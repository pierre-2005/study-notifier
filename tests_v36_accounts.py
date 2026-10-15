"""Account migration, forced-password-reset, verified email and permission tests."""
import os,sys,tempfile,types,re
from pathlib import Path

class Scheduler:
    def shutdown(self,wait=False): pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda timezone: Scheduler()
sys.modules['app.scheduler']=stub

tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(tmp.name)/'test.db'),SESSION_SECRET='test-secret-not-production',
              COOKIE_SECURE='false',APP_USERNAME='admin',APP_PASSWORD='AdminBootstrapPassword123!',
              MLO_PUBLIC_URL='https://organizer.overvault.ca',MLO_SMTP_HOST='mock',
              MLO_SMTP_FROM='recovery@example.com')
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user,get_user_by_username,ensure_bootstrap_admin,verify_password
from app import account_security as sec

sent=[]
sec._send_email=lambda to,subject,body: sent.append((to,subject,body)) or True
with TestClient(app,follow_redirects=False) as admin, TestClient(app,follow_redirects=False) as member:
    assert admin.get('/forgot-password').status_code==200
    assert member.get('/account/security').status_code==303
    assert admin.post('/login',data={'username':'admin','password':'AdminBootstrapPassword123!'}).status_code==303
    assert admin.get('/admin/users').status_code==200
    assert admin.get('/account/security').status_code==200
    ok,msg=create_pending_user('alex','Alex','MyStrongPassword123!','alex@example.com')
    assert ok,msg
    with get_conn() as c:
        uid=c.execute("SELECT id FROM users WHERE username='alex'").fetchone()['id']
        c.execute('UPDATE users SET approved=1 WHERE id=?',(uid,))
        c.commit()
    assert admin.get('/admin/users').status_code==200
    assert admin.post(f'/admin/users/{uid}/reset-password',data={'new_password':'TemporaryPass123!','confirm_password':'TemporaryPass123!','admin_password':'WRONG'}).status_code==403
    assert admin.post(f'/admin/users/{uid}/reset-password',data={'new_password':'TemporaryPass123!','confirm_password':'TemporaryPass123!','admin_password':'AdminBootstrapPassword123!'}).status_code==303
    assert member.post('/login',data={'username':'alex','password':'TemporaryPass123!'}).status_code==303
    r=member.get('/life')
    assert r.status_code==303 and r.headers['location'].startswith('/account/password'), r.headers
    assert member.get('/account/password').status_code==200
    assert member.post('/account/password',data={'current_password':'TemporaryPass123!','password':'AlexUpdatedPassword123!','confirm':'AlexUpdatedPassword123!'}).status_code==303
    assert member.get('/life').status_code==303
    assert member.post('/login',data={'username':'alex','password':'AlexUpdatedPassword123!'}).status_code==303
    assert member.get('/life').status_code==200
    # Protected permission changes must be made by an admin.
    assert member.post(f'/admin/users/{uid}/permissions',data={}).status_code in (303,403)
    form={k:'on' for k in sec.PERMISSION_LABELS if k!='projects_create'}
    assert admin.post(f'/admin/users/{uid}/permissions',data=form).status_code==303
    assert member.post('/life/projects',data={'name':'Must fail','area':'Personal','template':'blank'}).status_code==403
    with get_conn() as c:
        assert c.execute("SELECT COUNT(*) FROM life_projects WHERE name='Must fail'").fetchone()[0]==0
    # Verify email before allowing user-led recovery.
    assert member.post('/account/email/verify').status_code==303
    assert len(sent)==1,sent
    token=re.search(r'/verify-email/([A-Za-z0-9_-]+)',sent[-1][2]).group(1)
    assert member.get('/verify-email/'+token).status_code==200
    assert member.post('/verify-email/'+token).status_code==200
    assert get_user_by_username('alex')['email_verified']==1
    assert member.post('/verify-email/'+token).status_code==200  # Replay cannot modify data
    # Forgot-password endpoint does not reveal unknown accounts.
    unknown=member.post('/forgot-password',data={'identity':'missing@example.com'})
    known=member.post('/forgot-password',data={'identity':'alex@example.com'})
    assert unknown.status_code==known.status_code==200
    assert 'If a verified email matches' in unknown.text and 'If a verified email matches' in known.text
    reset_token=re.search(r'/password-reset/([A-Za-z0-9_-]+)',sent[-1][2]).group(1)
    assert member.post('/password-reset/'+reset_token,data={'password':'RecoveryPassword123!','confirm':'RecoveryPassword123!'}).status_code==303
    assert member.post('/password-reset/'+reset_token,data={'password':'OtherPassword123!','confirm':'OtherPassword123!'}).status_code==200
    assert member.get('/life').status_code==303  # previous session is revoked
    assert member.post('/login',data={'username':'alex','password':'RecoveryPassword123!'}).status_code==303
    assert member.get('/life').status_code==200
    # Bootstrap env must never overwrite admin password on restart.
    admin_id=get_user_by_username('admin')['id']
    from app.auth import update_user_password
    update_user_password(admin_id,'NewAdminPasswordSecure123!',actor_id=admin_id)
    ensure_bootstrap_admin('admin','AdminBootstrapPassword123!')
    assert verify_password('NewAdminPasswordSecure123!',get_user_by_username('admin')['password_hash'])
    assert not verify_password('AdminBootstrapPassword123!',get_user_by_username('admin')['password_hash'])
    assert admin.get('/admin/users').status_code==303  # revoked session
    # User cannot fake verified email by setting a new email
    assert member.post('/account/email',data={'email':'updated@example.com','current_password':'RecoveryPassword123!'}).status_code==303
    assert not get_user_by_username('alex')['email_verified']
print('PASS: permissions enforced; admin reset; forced change; session revocation; email verification; single-use recovery; bootstrap-only admin')
tmp.cleanup()
