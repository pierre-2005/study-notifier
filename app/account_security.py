"""Password recovery and per-user security controls.

Recovery links are random, single-use, short-lived and stored only as hashes.
No self-service reset is possible before the email address is verified.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import (get_user_by_id, verify_password, update_user_password,
                      PERMISSION_LABELS, set_user_capabilities)
from app.db import get_conn

router=APIRouter(tags=['account-security'])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent/'templates'))

def init_account_security_schema():
    # Tables/columns are created in init_auth_schema, which is always called first.
    return None

def now():
    return datetime.now(timezone.utc).isoformat()

def _current(request):
    user=getattr(request.state,'current_user',None)
    if user is None: raise HTTPException(401,'Sign in required')
    return user

def _admin(request):
    user=_current(request)
    if user['role']!='admin': raise HTTPException(403,'Administrator access required')
    return user

def _email_configured():
    return bool(os.getenv('MLO_SMTP_HOST') and os.getenv('MLO_SMTP_FROM')
                and os.getenv('MLO_PUBLIC_URL','').startswith('https://'))

def _send_email(to, subject, body):
    host=os.getenv('MLO_SMTP_HOST','').strip()
    sender=os.getenv('MLO_SMTP_FROM','').strip()
    if not host or not sender: return False
    msg=EmailMessage()
    msg['From']=sender
    msg['To']=to
    msg['Subject']=subject
    msg.set_content(body)
    port=int(os.getenv('MLO_SMTP_PORT','587'))
    username=os.getenv('MLO_SMTP_USER','')
    password=os.getenv('MLO_SMTP_PASSWORD','')
    # Never transmit SMTP credentials without transport encryption.
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=8,context=ssl.create_default_context()) as smtp:
            if username: smtp.login(username,password)
            smtp.send_message(msg)
    else:
        if os.getenv('MLO_SMTP_STARTTLS','true').lower() in ('0','false','no'):
            raise RuntimeError('STARTTLS must be enabled for SMTP submission.')
        with smtplib.SMTP(host,port,timeout=8) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            if username: smtp.login(username,password)
            smtp.send_message(msg)
    return True

def _issue_token(user_id,purpose,candidate_email=None,minutes=30):
    token=secrets.token_urlsafe(36)
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    with get_conn() as conn:
        # One token per user/purpose every 5 minutes to reduce inbox abuse.
        since=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
        recent=conn.execute('''SELECT id FROM auth_email_tokens WHERE user_id=? AND purpose=?
                                  AND created_at>=?''',(user_id,purpose,since)).fetchone()
        if recent: return None
        conn.execute('''INSERT INTO auth_email_tokens(user_id,purpose,token_hash,candidate_email,created_at,expires_at)
                          VALUES(?,?,?,?,?,?)''',(user_id,purpose,token_hash,candidate_email,now(),
                          (datetime.now(timezone.utc)+timedelta(minutes=minutes)).isoformat()))
        conn.commit()
    return token

def _get_token(token,purpose):
    if not token or len(token)>180: return None
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    with get_conn() as conn:
        return conn.execute('''SELECT t.*,u.username,u.email,u.email_verified,u.active FROM auth_email_tokens t
            JOIN users u ON u.id=t.user_id WHERE token_hash=? AND purpose=? AND used_at IS NULL
            AND expires_at>?''',(token_hash,purpose,now())).fetchone()

def _mark_token(token_id):
    with get_conn() as conn:
        conn.execute('UPDATE auth_email_tokens SET used_at=? WHERE id=? AND used_at IS NULL',(now(),token_id))
        conn.commit()

def _view(request,template,**kwargs):
    return templates.TemplateResponse(request,template,{'request':request,**kwargs})

@router.get('/forgot-password',response_class=HTMLResponse)
def forgot_page(request:Request):
    return _view(request,'forgot_password.html',message='',error='',smtp_enabled=_email_configured())

@router.post('/forgot-password',response_class=HTMLResponse)
def forgot_submit(request:Request,identity:str=Form(...)):
    # Do not disclose account existence or verified-email status.
    generic='If a verified email matches an account, a recovery link will be sent.'
    identity=identity.strip().lower()[:254]
    with get_conn() as conn:
        user=conn.execute('''SELECT id,email FROM users WHERE active=1 AND approved=1 AND email_verified=1
            AND (lower(email)=? OR lower(username)=?)''',(identity,identity)).fetchone()
    if user and user['email'] and _email_configured():
        token=_issue_token(user['id'],'password_reset')
        if token:
            url=os.getenv('MLO_PUBLIC_URL','').rstrip('/')+'/password-reset/'+token
            try:
                _send_email(user['email'],'MLO password reset',
                    'A password reset was requested for your MLO account.\n\n'+url+
                    '\n\nThis link expires in 30 minutes. If you did not request it, ignore this message.')
            except Exception:
                logging.getLogger(__name__).exception('Password-reset email delivery failed')
    return _view(request,'forgot_password.html',message=generic,error='',smtp_enabled=_email_configured())

@router.get('/password-reset/{token}',response_class=HTMLResponse)
def reset_page(request:Request,token:str):
    return _view(request,'reset_password.html',token=token,valid=bool(_get_token(token,'password_reset')),error='',success='')

@router.post('/password-reset/{token}',response_class=HTMLResponse)
def reset_submit(request:Request,token:str,password:str=Form(...),confirm:str=Form(...)):
    entry=_get_token(token,'password_reset')
    if not entry: return _view(request,'reset_password.html',token=token,valid=False,error='This link is invalid or expired.',success='')
    if password!=confirm or not 12<=len(password)<=256:
        return _view(request,'reset_password.html',token=token,valid=True,error='Passwords must match and contain 12–256 characters.',success='')
    # Consume the token atomically before updating the password. Reject replays.
    with get_conn() as conn:
        result=conn.execute('UPDATE auth_email_tokens SET used_at=? WHERE id=? AND used_at IS NULL',
                            (now(),entry['id']))
        conn.commit()
        if result.rowcount!=1: raise HTTPException(400,'Link already used.')
    update_user_password(int(entry['user_id']),password,temporary=False)
    return RedirectResponse('/login?message=Password+updated.+Please+sign+in.',status_code=303)

@router.get('/verify-email/{token}',response_class=HTMLResponse)
def verify_page(request:Request,token:str):
    return _view(request,'verify_email.html',token=token,valid=bool(_get_token(token,'verify_email')),success=False)

@router.post('/verify-email/{token}',response_class=HTMLResponse)
def verify_submit(request:Request,token:str):
    entry=_get_token(token,'verify_email')
    if not entry: return _view(request,'verify_email.html',token=token,valid=False,success=False)
    with get_conn() as conn:
        result=conn.execute('UPDATE auth_email_tokens SET used_at=? WHERE id=? AND used_at IS NULL',(now(),entry['id']))
        if result.rowcount!=1: raise HTTPException(400,'Link already used.')
        conn.execute('''UPDATE users SET email_verified=1 WHERE id=? AND lower(email)=?''',
                     (entry['user_id'],(entry['candidate_email'] or '').lower()))
        conn.commit()
    return _view(request,'verify_email.html',token='',valid=False,success=True)

@router.get('/account/security',response_class=HTMLResponse)
def account_page(request:Request,message:str=''):
    user=_current(request)
    return _view(request,'account_security.html',user=user,notice=message,
                 smtp_enabled=_email_configured(),error='')

@router.post('/account/email')
def account_email(request:Request,email:str=Form(...),current_password:str=Form(...)):
    user=_current(request)
    email=email.strip().lower()
    if len(email)>254 or '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(422,'Enter a valid email address.')
    if not verify_password(current_password,user['password_hash']):
        raise HTTPException(403,'Your current password is incorrect.')
    with get_conn() as conn:
        existing=conn.execute('SELECT id FROM users WHERE lower(email)=? AND id!=?',(email,user['id'])).fetchone()
        if existing: raise HTTPException(409,'Email already registered.')
        conn.execute('UPDATE users SET email=?,email_verified=0 WHERE id=?',(email,user['id']))
        conn.execute('UPDATE auth_email_tokens SET used_at=? WHERE user_id=? AND purpose=? AND used_at IS NULL',
                     (now(),user['id'],'verify_email'))
        conn.commit()
    return RedirectResponse('/account/security?message=Email+saved.+Verify+it+to+enable+recovery.',status_code=303)

@router.post('/account/email/verify')
def request_email_verify(request:Request):
    user=_current(request)
    if not _email_configured() or not user['email'] or user['email_verified']:
        return RedirectResponse('/account/security',status_code=303)
    token=_issue_token(user['id'],'verify_email',candidate_email=user['email'],minutes=60)
    if token:
        url=os.getenv('MLO_PUBLIC_URL','').rstrip('/')+'/verify-email/'+token
        try:
            _send_email(user['email'],'Verify your MLO email address',
                'Confirm your email address using this link:\n\n'+url+'\n\nThis link expires in one hour.')
        except Exception:
            logging.getLogger(__name__).exception('Verification email delivery failed')
    return RedirectResponse('/account/security?message=If+mail+delivery+is+configured,+check+your+inbox.',status_code=303)

@router.get('/account/password',response_class=HTMLResponse)
def change_page(request:Request,required:str=''):
    _current(request)
    return _view(request,'change_password.html',required=bool(required),error='')

@router.post('/account/password',response_class=HTMLResponse)
def change_submit(request:Request,current_password:str=Form(...),password:str=Form(...),confirm:str=Form(...)):
    user=_current(request)
    if not verify_password(current_password,user['password_hash']):
        return _view(request,'change_password.html',required=bool(user['must_change_password']),error='Current password is incorrect.')
    if password!=confirm or not 12<=len(password)<=256:
        return _view(request,'change_password.html',required=bool(user['must_change_password']),error='New passwords must match and contain 12–256 characters.')
    update_user_password(int(user['id']),password,actor_id=int(user['id']))
    request.session.clear()
    return RedirectResponse('/login?message=Password+updated.+Sign+in+again.',status_code=303)

@router.post('/admin/users/{target_id}/reset-password')
def admin_reset(request:Request,target_id:int,new_password:str=Form(...),confirm_password:str=Form(...),admin_password:str=Form(...)):
    admin=_admin(request)
    if not verify_password(admin_password,admin['password_hash']):
        raise HTTPException(403,'Your administrator password is incorrect.')
    if new_password!=confirm_password: raise HTTPException(422,'Passwords do not match.')
    if int(admin['id'])==target_id: raise HTTPException(400,'Use Account security to change your own password.')
    target=get_user_by_id(target_id)
    if not target or target['role']=='admin': raise HTTPException(403,'Administrator passwords must be changed by their owners.')
    try: update_user_password(target_id,new_password,actor_id=int(admin['id']),temporary=True)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    return RedirectResponse('/admin/users?notice=Password+reset.+Existing+sessions+revoked.',status_code=303)

@router.post('/admin/users/{target_id}/permissions')
async def admin_permissions(request:Request,target_id:int):
    admin=_admin(request)
    form=await request.form()
    prefs={k:(form.get(k)=='on') for k in PERMISSION_LABELS}
    if not set_user_capabilities(target_id,prefs,int(admin['id'])): raise HTTPException(404,'Member not found.')
    return RedirectResponse('/admin/users?notice=Permissions+saved.',status_code=303)

@router.post('/admin/users/{target_id}/email')
def admin_email(request:Request,target_id:int,email:str=Form(''),admin_password:str=Form(...)):
    admin=_admin(request)
    if not verify_password(admin_password,admin['password_hash']): raise HTTPException(403,'Admin password incorrect.')
    email=email.strip().lower()
    if email and ('@' not in email or len(email)>254 or '.' not in email.split('@')[-1]):
        raise HTTPException(422,'Invalid email.')
    with get_conn() as conn:
        if not conn.execute('SELECT id FROM users WHERE id=? AND role!=?',(target_id,'admin')).fetchone():
            raise HTTPException(404,'Member not found.')
        if email and conn.execute('SELECT id FROM users WHERE lower(email)=? AND id!=?',(email,target_id)).fetchone():
            raise HTTPException(409,'Email already in use.')
        conn.execute('UPDATE users SET email=?,email_verified=0 WHERE id=?',(email or None,target_id))
        conn.execute('UPDATE auth_email_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',(now(),target_id))
        conn.execute('INSERT INTO auth_audit_log(actor_id,target_id,action,created_at) VALUES(?,?,?,?)',
                     (admin['id'],target_id,'email_updated',now()))
        conn.commit()
    return RedirectResponse('/admin/users?notice=Email+saved.+Verification+required.',status_code=303)
