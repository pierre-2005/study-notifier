"""Account-scoped ntfy device topics. Never send to another user's topic."""
from __future__ import annotations
import secrets
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
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent/'templates'))
templates.env.globals['APP_VERSION']=APP_VERSION


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
    return templates.TemplateResponse(request,'life_devices.html',{'request':request,'devices':devices,'base_url':settings.ntfy_base_url,'notice':notice})


@router.post('')
def add_device(request:Request,name:str=Form('My phone')):
    name=name.strip()[:80] or 'My phone'
    topic='mlo-'+secrets.token_urlsafe(24).replace('_','-')
    with get_conn() as conn:
        conn.execute('INSERT INTO life_devices(owner_id,name,topic,created_at) VALUES(?,?,?,?)',
                     (uid(request),name,topic,datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return RedirectResponse('/life/devices',status_code=303)



@router.get('/{device_id}/qr.png', include_in_schema=False)
def device_qr(request:Request, device_id:int):
    """Android ntfy subscribe QR; never show another user's topic."""
    with get_conn() as conn:
        row=conn.execute('SELECT topic FROM life_devices WHERE id=? AND owner_id=?',
                         (device_id,uid(request))).fetchone()
    if row is None: raise HTTPException(404,'Device not found')
    host=urlparse(settings.ntfy_base_url)
    if host.scheme != 'https' or not host.hostname:
        raise HTTPException(503,'Configure an HTTPS ntfy server to enable QR pairing')
    # Official ntfy Android deep link syntax subscribes the topic automatically.
    link=f'ntfy://{host.netloc}/{quote(row["topic"],safe="")}?display=My+Life+Organized'
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,
                     box_size=9,border=3)
    qr.add_data(link);qr.make(fit=True)
    output=io.BytesIO();qr.make_image(fill_color='black',back_color='white').save(output,format='PNG')
    return Response(output.getvalue(),media_type='image/png',headers={
        'Cache-Control':'private, no-store',
        'X-Content-Type-Options':'nosniff',
        'Referrer-Policy':'no-referrer',
    })

@router.get('/{device_id}/ios-qr.png', include_in_schema=False)
def iphone_pair_qr(request:Request, device_id:int):
    """iPhone QR opens an authenticated MLO copy/paste guide, not an Android-only deep link.

    The QR embeds only a URL with an opaque-in-practice device ID. It never embeds the
    ntfy topic; the signed-in device owner must open the page to see that secret.
    """
    with get_conn() as conn:
        row=conn.execute('SELECT id FROM life_devices WHERE id=? AND owner_id=?',
                         (device_id,uid(request))).fetchone()
    if row is None: raise HTTPException(404,'Device not found')
    public_url=os.getenv('MLO_PUBLIC_URL','').strip().rstrip('/')
    parsed=urlparse(public_url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise HTTPException(503,'Configure MLO_PUBLIC_URL with your HTTPS website address')
    link=f'{public_url}/life/devices/{device_id}/pair-iphone'
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,
                     box_size=9,border=3)
    qr.add_data(link);qr.make(fit=True)
    output=io.BytesIO();qr.make_image(fill_color='black',back_color='white').save(output,format='PNG')
    return Response(output.getvalue(),media_type='image/png',headers={
        'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff',
        'Referrer-Policy':'no-referrer',
    })


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
