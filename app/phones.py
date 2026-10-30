"""Account-scoped ntfy device topics. Never send to another user's topic."""
from __future__ import annotations
import secrets
import hashlib
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import io
import os
from urllib.parse import urlparse, quote

import qrcode
from datetime import datetime,timezone
from pathlib import Path
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.config import settings
from app.notifier.ntfy import NtfyNotifier
from app.meta import APP_VERSION

router=APIRouter(prefix='/life/devices',tags=['devices'])
public_router=APIRouter(prefix='/pair/phone',tags=['phone pairing'])
PAIR_MAX_AGE=15*60
from app.ui import templates


def init_phone_schema():
    with get_conn() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS life_devices (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          topic TEXT NOT NULL UNIQUE,
          enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_devices_owner ON life_devices(owner_id);
        CREATE TABLE IF NOT EXISTS life_task_notification_log (
          task_id INTEGER NOT NULL REFERENCES life_tasks(id) ON DELETE CASCADE,
          device_id INTEGER NOT NULL REFERENCES life_devices(id) ON DELETE CASCADE,
          due_day TEXT NOT NULL, sent_at TEXT NOT NULL,
          PRIMARY KEY(task_id,device_id,due_day)
        );
        ''')
        conn.commit()


def uid(request):
    user=getattr(request.state,'current_user',None)
    if user is None: raise HTTPException(401,'Sign in required')
    return int(user['id'])


@router.get('',response_class=HTMLResponse)
def devices_page(request:Request,notice:str=''):
    with get_conn() as conn:
        devices=conn.execute('SELECT * FROM life_devices WHERE owner_id=? ORDER BY id DESC',(uid(request),)).fetchall()
    pair_links={}
    for device in devices:
        try:pair_links[device['id']]={platform:_pair_link(device,platform) for platform in ('iphone','android')}
        except HTTPException:pass
    return templates.TemplateResponse(request,'life_devices.html',{'request':request,'devices':devices,'base_url':settings.ntfy_base_url,'notice':notice,'pair_links':pair_links})


@router.post('')
def add_device(request:Request,name:str=Form('My phone')):
    name=name.strip()[:80] or 'My phone'
    topic='mlo-'+secrets.token_urlsafe(24).replace('_','-')
    with get_conn() as conn:
        conn.execute('INSERT INTO life_devices(owner_id,name,topic,created_at) VALUES(?,?,?,?)',
                     (uid(request),name,topic,datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return RedirectResponse('/life/devices',status_code=303)



def _pair_serializer():
    return URLSafeTimedSerializer(os.environ['SESSION_SECRET'],salt='mlo-phone-pair-v1')


def _pair_link(device,platform):
    public_url=os.getenv('MLO_PUBLIC_URL','').strip().rstrip('/')
    parsed=urlparse(public_url)
    if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(503,'Configure MLO_PUBLIC_URL with your HTTPS website address')
    token=_pair_serializer().dumps({'device':device['id'],'topic':hashlib.sha256(device['topic'].encode()).hexdigest()})
    return f'{public_url}/pair/phone/{token}?platform={platform}'


def _qr(request,device_id,platform):
    with get_conn() as conn:
        device=conn.execute('SELECT * FROM life_devices WHERE id=? AND owner_id=?',(device_id,uid(request))).fetchone()
    if device is None:raise HTTPException(404,'Device not found')
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=4)
    qr.add_data(_pair_link(device,platform));qr.make(fit=True)
    output=io.BytesIO();qr.make_image(fill_color='black',back_color='white').save(output,format='PNG')
    return Response(output.getvalue(),media_type='image/png',headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})


@router.get('/{device_id}/qr.png',include_in_schema=False)
def device_qr(request:Request,device_id:int):
    return _qr(request,device_id,'android')


@router.get('/{device_id}/ios-qr.png',include_in_schema=False)
def iphone_pair_qr(request:Request,device_id:int):
    return _qr(request,device_id,'iphone')


@public_router.get('/{token}',response_class=HTMLResponse,include_in_schema=False)
def scan_phone(request:Request,token:str,platform:str='iphone'):
    if len(token)>600:raise HTTPException(404,'Pairing code not found')
    try:data=_pair_serializer().loads(token,max_age=PAIR_MAX_AGE)
    except SignatureExpired:raise HTTPException(410,'This pairing code expired. Open Phones & reminders on your signed-in device and refresh the QR code.')
    except BadSignature:raise HTTPException(404,'Pairing code not found')
    if not isinstance(data,dict) or type(data.get('device')) is not int:raise HTTPException(404,'Pairing code not found')
    with get_conn() as conn:
        device=conn.execute("""SELECT d.* FROM life_devices d JOIN users u ON u.id=d.owner_id WHERE d.id=? AND u.active=1 AND u.approved=1 AND (u.requires_email_verification=0 OR u.email_verified=1)""",(data['device'],)).fetchone()
    if device is None or not secrets.compare_digest(str(data.get('topic','')),hashlib.sha256(device['topic'].encode()).hexdigest()):raise HTTPException(404,'Pairing code not found')
    host=urlparse(settings.ntfy_base_url)
    if host.scheme!='https' or not host.hostname or host.username or host.password:raise HTTPException(503,'An HTTPS notification server is required')
    deep_link=f'ntfy://{host.netloc}/{quote(device["topic"],safe="")}?display=My+Life+Organized'
    return templates.TemplateResponse(request,'phone_pair.html',{'device':device,'base_url':settings.ntfy_base_url,'platform':'android' if platform=='android' else 'iphone','deep_link':deep_link},headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer','X-Robots-Tag':'noindex, nofollow'})


@router.get('/{device_id}/open-pair',include_in_schema=False)
def open_pair(request:Request,device_id:int,platform:str='iphone'):
    with get_conn() as conn:device=conn.execute('SELECT * FROM life_devices WHERE id=? AND owner_id=?',(device_id,uid(request))).fetchone()
    if device is None:raise HTTPException(404,'Device not found')
    return RedirectResponse(_pair_link(device,'android' if platform=='android' else 'iphone'),status_code=303,headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer'})


@router.get('/{device_id}/pair-iphone',response_class=HTMLResponse,include_in_schema=False)
def iphone_pair_page(request:Request, device_id:int):
    """Phone-friendly topic-copy page with strict per-account ownership checks."""
    with get_conn() as conn:
        row=conn.execute('SELECT * FROM life_devices WHERE id=? AND owner_id=?',
                         (device_id,uid(request))).fetchone()
    if row is None: raise HTTPException(404,'Device not found')
    return templates.TemplateResponse(request,'life_device_ios_pair.html',{
        'request':request, 'device':row, 'base_url':settings.ntfy_base_url,
    },headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer'})


@router.post('/{device_id}/toggle')
def toggle_device(request:Request,device_id:int):
    with get_conn() as conn:
        result=conn.execute('UPDATE life_devices SET enabled=CASE WHEN enabled=1 THEN 0 ELSE 1 END WHERE id=? AND owner_id=?',(device_id,uid(request)))
        if result.rowcount != 1:
            raise HTTPException(404,'Device not found')
        conn.commit()
    return RedirectResponse('/life/devices',status_code=303)


@router.post('/{device_id}/delete')
def remove_device(request:Request,device_id:int):
    with get_conn() as conn:
        result=conn.execute('DELETE FROM life_devices WHERE id=? AND owner_id=?',(device_id,uid(request)))
        if result.rowcount != 1:
            raise HTTPException(404,'Device not found')
        conn.commit()
    return RedirectResponse('/life/devices',status_code=303)


@router.post('/{device_id}/test')
def test_device(request:Request,device_id:int):
    with get_conn() as conn:
        row=conn.execute('SELECT * FROM life_devices WHERE id=? AND owner_id=?',(device_id,uid(request))).fetchone()
    if not row: raise HTTPException(404,'Device not found')
    if not row['enabled']: return RedirectResponse('/life/devices?notice=disabled',status_code=303)
    result=NtfyNotifier(settings.ntfy_base_url,row['topic']).send('MLO connection test','Your phone is connected to your MLO workspace.')
    return RedirectResponse('/life/devices?notice='+('sent' if result else 'failed'),status_code=303)
