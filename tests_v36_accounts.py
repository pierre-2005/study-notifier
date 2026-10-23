"""Account compatibility: owner-delivered recovery, permissions, and session revocation."""
import os,sys,tempfile,types,re
from pathlib import Path
class Scheduler:
    def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda _:Scheduler();sys.modules['app.scheduler']=stub
tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(tmp.name)/'test.db'),SESSION_SECRET='test-secret-not-production',
    COOKIE_SECURE='false',APP_USERNAME='admin',APP_PASSWORD='AdminBootstrapPassword123!',MLO_PUBLIC_URL='https://organizer.overvault.ca',
    MLO_SMTP_HOST='mock',MLO_SMTP_FROM='recovery@example.com')
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user,get_user_by_username,ensure_bootstrap_admin,verify_password,update_user_password
from app import account_security as sec
sent=[];sec._send_email=lambda to,subject,body:sent.append((to,subject,body)) or True
with TestClient(app,follow_redirects=False) as admin,TestClient(app,follow_redirects=False) as member:
    assert admin.get('/forgot-password').status_code==200
    assert member.get('/account/security').status_code==303
    assert admin.post('/login',data={'username':'admin','password':'AdminBootstrapPassword123!'}).status_code==303
    ok,message=create_pending_user('alex','Alex','MyStrongPassword123!','alex@example.com');assert ok,message
    uid=get_user_by_username('alex')['id']
    with get_conn() as db:db.execute('UPDATE users SET approved=1 WHERE id=?',(uid,));db.commit()
    assert admin.post(f'/admin/users/{uid}/reset-password',data={'admin_password':'WRONG'}).status_code==403
    # An unverified address cannot be used for recovery. Admins cannot set known member passwords.
    assert admin.post(f'/admin/users/{uid}/reset-password',data={'admin_password':'AdminBootstrapPassword123!','new_password':'ShouldNotBeSet!123'}).status_code==409
    assert verify_password('MyStrongPassword123!',get_user_by_username('alex')['password_hash'])
    assert member.post('/login',data={'username':'alex','password':'MyStrongPassword123!'}).status_code==303
    assert member.get('/life').status_code==200
    form={k:'on' for k in sec.PERMISSION_LABELS if k!='projects_create'}
    assert admin.post(f'/admin/users/{uid}/permissions',data=form).status_code==303
    assert member.post('/life/projects',data={'name':'Must fail','area':'Personal','template':'blank'}).status_code==403
    assert member.post('/account/email/verify').status_code==303
    token=re.search(r'/verify-email/([A-Za-z0-9_-]+)',sent[-1][2])[1]
    assert member.post('/verify-email/'+token).status_code==200
    assert get_user_by_username('alex')['email_verified']==1
    assert member.post('/verify-email/'+token).status_code==200
    unknown=member.post('/forgot-password',data={'identity':'missing@example.com'})
    known=member.post('/forgot-password',data={'identity':'alex@example.com'})
    assert unknown.status_code==known.status_code==200
    assert 'If a verified email matches' in unknown.text and 'If a verified email matches' in known.text
    code=re.search(r'\b\d{6}\b',sent[-1][2])[0]
    reset={'email':'alex@example.com','code':code,'password':'RecoveryPassword123!','confirm':'RecoveryPassword123!'}
    assert member.post('/reset-code',data=reset).status_code==303
    assert member.post('/reset-code',data=reset).status_code==200
    assert member.get('/life').status_code==303
    assert member.post('/login',data={'username':'alex','password':'RecoveryPassword123!'}).status_code==303
    assert member.get('/life').status_code==200
    # Old issued links remain compatible, and their token/password update commits atomically.
    legacy=sec._issue_token(uid,'password_reset')
    assert member.post('/password-reset/'+legacy,data={'password':'LinkRecoveryPassword123!','confirm':'LinkRecoveryPassword123!'}).status_code==303
    assert member.post('/password-reset/'+legacy,data={'password':'NoReplayPassword123!','confirm':'NoReplayPassword123!'}).status_code==200
    assert member.post('/login',data={'username':'alex','password':'LinkRecoveryPassword123!'}).status_code==303
    assert admin.post(f'/admin/users/{uid}/email',data={'email':'attacker@example.com','admin_password':'AdminBootstrapPassword123!'}).status_code==403
    assert member.post('/account/email',data={'email':'updated@example.com','current_password':'LinkRecoveryPassword123!'}).status_code==303
    assert not get_user_by_username('alex')['email_verified']
    admin_id=get_user_by_username('admin')['id'];update_user_password(admin_id,'NewAdminPasswordSecure123!',actor_id=admin_id)
    ensure_bootstrap_admin('admin','AdminBootstrapPassword123!')
    assert verify_password('NewAdminPasswordSecure123!',get_user_by_username('admin')['password_hash'])
    assert not verify_password('AdminBootstrapPassword123!',get_user_by_username('admin')['password_hash'])
    assert admin.get('/admin/users').status_code==303
print('PASS: owner-delivered codes; old reset links; permissions; email verification; session revocation; no admin impersonation; bootstrap preservation')
tmp.cleanup()
