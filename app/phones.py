"""Account-scoped ntfy device topics. Never send to another user's topic."""
from __future__ import annotations
import secrets
from datetime import datetime,timezone
from pathlib import Path
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


@router.post('/{device_id}/toggle')
def toggle_device(request:Request,device_id:int):
    with get_conn() as conn:
        conn.execute('UPDATE life_devices SET enabled=CASE WHEN enabled=1 THEN 0 ELSE 1 END WHERE id=? AND owner_id=?',(device_id,uid(request)))
        conn.commit()
    return RedirectResponse('/life/devices',status_code=303)


@router.post('/{device_id}/delete')
def remove_device(request:Request,device_id:int):
    with get_conn() as conn:
        conn.execute('DELETE FROM life_devices WHERE id=? AND owner_id=?',(device_id,uid(request)))
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
