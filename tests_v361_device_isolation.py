"""Security regression: another MLO account, including admin, cannot manage personal devices."""
from __future__ import annotations
import importlib.util
import os
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path

class NoopScheduler:
    def shutdown(self,wait=False): pass

# Startup must not run timers or contact an external ntfy service.
_stub=types.ModuleType('app.scheduler')
_stub.start_scheduler=lambda _: NoopScheduler()
sys.modules['app.scheduler']=_stub
_tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(_tmp.name)/'devices.db'),
    SESSION_SECRET='local-device-test-secret', COOKIE_SECURE='false',
    APP_USERNAME='admin', APP_PASSWORD='admin-password-for-testing',
    MLO_PUBLIC_URL='https://organizer.overvault.ca',
    NTFY_TOPIC='legacy-shared-topic', MLO_ENABLE_LEGACY_GLOBAL_NTFY='true')

from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user
from app.notifier.ntfy import NtfyNotifier

sent=[]
old_send=NtfyNotifier.send
NtfyNotifier.send=lambda self,title,message: sent.append((self.url,title,message)) or True

with TestClient(app,follow_redirects=False) as admin, TestClient(app,follow_redirects=False) as a, TestClient(app,follow_redirects=False) as b:
    for name in ('alice','bob'):
        ok, info=create_pending_user(name,name.title(),'SafePassword456789!')
        assert ok,info
    with get_conn() as c:
        c.execute("UPDATE users SET approved=1 WHERE username IN ('alice','bob')")
        c.commit()
    assert admin.post('/login',data={'username':'admin','password':'admin-password-for-testing'}).status_code==303
    assert a.post('/login',data={'username':'alice','password':'SafePassword456789!'}).status_code==303
    assert b.post('/login',data={'username':'bob','password':'SafePassword456789!'}).status_code==303
    assert a.post('/life/devices',data={'name':'Alice phone'}).status_code==303
    assert b.post('/life/devices',data={'name':'Bob phone'}).status_code==303
    with get_conn() as c:
        alice=c.execute("SELECT d.* FROM life_devices d JOIN users u ON u.id=d.owner_id WHERE u.username='alice'").fetchone()
        bob=c.execute("SELECT d.* FROM life_devices d JOIN users u ON u.id=d.owner_id WHERE u.username='bob'").fetchone()
        assert alice['topic']!=bob['topic']
        assert alice['owner_id']!=bob['owner_id']
    for client,own,other in ((a,alice,bob),(b,bob,alice),(admin,None,alice),(admin,None,bob)):
        page=client.get('/life/devices')
        assert page.status_code==200
        assert other['topic'] not in page.text
        if own:
            assert own['topic'] in page.text
        for method in ('toggle','delete','test'):
            assert client.post(f"/life/devices/{other['id']}/{method}").status_code==404,method
        assert not sent
        with get_conn() as c:
            persisted=c.execute('SELECT enabled FROM life_devices WHERE id=?',(other['id'],)).fetchone()
            assert persisted and persisted['enabled']==1
    assert a.post(f"/life/devices/{alice['id']}/test").status_code==303
    assert len(sent)==1 and alice['topic'] in sent[0][0]
    sent.clear()
    assert a.post(f"/life/devices/{alice['id']}/toggle").status_code==303
    assert a.post(f"/life/devices/{alice['id']}/test").status_code==303
    assert not sent
    assert a.post(f"/life/devices/{alice['id']}/toggle").status_code==303
    # Load the production scheduler implementation separately from the startup stub.
    # The app integration tests don't require a running APScheduler package.
    if 'apscheduler.schedulers.background' not in sys.modules:
        for n in ('apscheduler','apscheduler.schedulers','apscheduler.schedulers.background','apscheduler.triggers','apscheduler.triggers.interval'):
            module=types.ModuleType(n)
            if n in ('apscheduler','apscheduler.schedulers','apscheduler.triggers'):
                module.__path__=[]
            sys.modules[n]=module
        sys.modules['apscheduler.schedulers.background'].BackgroundScheduler=object
        sys.modules['apscheduler.triggers.interval'].IntervalTrigger=object
    path=Path(__file__).resolve().parent/'app'/'scheduler.py'
    spec=importlib.util.spec_from_file_location('_actual_mlo_scheduler',path)
    actual=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual)
    _stub.legacy_global_notifications_allowed=actual.legacy_global_notifications_allowed
    assert not actual.legacy_global_notifications_allowed(), 'Global topic must fail closed with multiple accounts'
    # Even an old global topic with due reminders must not receive multi-user data.
    with get_conn() as c:
        c.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc) VALUES(?,?,?,?,?)",
                  ('todo',1,'2020-01-01T00:00:00+00:00','Private legacy reminder','2020-01-01T00:00:00+00:00'))
        c.commit()
    actual.process_due_reminders()
    actual.process_todo_digest()
    assert sent==[], 'Multi-user reminders must never use the shared legacy channel'
    assert admin.post('/settings/test').headers['location'].startswith('/life/devices?notice=no_global')
    assert not sent
    # A due task goes only to devices owned by the task's owner.
    due=datetime(2026,10,15,18,tzinfo=timezone.utc)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls,tz=None):
            return due.astimezone(tz) if tz else due.replace(tzinfo=None)
    actual.datetime=FrozenDatetime
    with get_conn() as c:
        for user,title in (('alice','Alice private task'),('bob','Bob private task')):
            uid=c.execute('SELECT id FROM users WHERE username=?',(user,)).fetchone()['id']
            c.execute('''INSERT INTO life_tasks(owner_id,title,created_at,updated_at,due_on)
                         VALUES(?,?,?,?,?)''',(uid,title,due.isoformat(),due.isoformat(),'2026-10-15'))
        c.commit()
    actual.process_life_reminders()
    assert len(sent)==2,sent
    assert any(alice['topic'] in url and msg=='Alice private task' for url,_,msg in sent)
    assert any(bob['topic'] in url and msg=='Bob private task' for url,_,msg in sent)
    assert not any(bob['topic'] in url and msg=='Alice private task' for url,_,msg in sent)
    assert not any(alice['topic'] in url and msg=='Bob private task' for url,_,msg in sent)
    assert a.post(f"/life/devices/{alice['id']}/delete").status_code==303
    assert a.get('/life/devices').text.find(alice['topic'])==-1
    assert b.get('/life/devices').text.find(bob['topic'])!=-1

NtfyNotifier.send=old_send
_tmp.cleanup()
print('PASS: device list/create/toggle/delete/test isolated; admin limited to own devices; due reminders owner-matched; legacy global fail-closed')
