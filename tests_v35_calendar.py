"""MLO v3.5: single event form, private local events and throttled automatic sync."""
import os, sys, types, tempfile
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet

class NoopScheduler:
    def shutdown(self,wait=False): pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda _:NoopScheduler()
sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as tmp:
    os.environ.update({'SESSION_SECRET':'v35-test-session-secret','APP_USERNAME':'admin',
      'APP_PASSWORD':'test-strong-password','STUDY_NOTIFIER_DB':str(Path(tmp)/'app.sqlite'),
      'TIMEZONE':'America/Edmonton','COOKIE_SECURE':'false','MLO_CREDENTIAL_KEY':Fernet.generate_key().decode(),
      'MLO_CALENDAR_AUTO_SYNC':'true','MLO_CALENDAR_SYNC_MINUTES':'10'})
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_conn
    from app.auth import create_pending_user
    from app import calendar_links as cal
    class Reply:
        def __init__(self,payload):self.payload=payload
        def json(self):return self.payload
    requests=[]
    def fake_request(method,url,**kw):
        requests.append((method,url))
        if '/calendarList' in url:
            return Reply({'items':[{'id':'my-cal','summary':'Calendar A','accessRole':'owner'}]})
        if method=='POST' and url.endswith('/my-cal/events'):
            return Reply({'id':'new-event-id','summary':kw['json']['summary'],
                          'start':kw['json']['start'],'htmlLink':'https://calendar.google.com/event'})
        raise AssertionError((method,url))
    with TestClient(app,follow_redirects=False) as admin:
        assert admin.post('/login',data={'username':'admin','password':'test-strong-password','next':'/life'}).status_code==303
        page=admin.get('/life/calendars/new')
        assert page.status_code==200 and 'MLO only' in page.text and 'mlo-event-destination' in page.text
        # MLO-only events remain in user-specific tables, not the legacy shared events table.
        data={'destination':'mlo','title':'Private appointment','start':'2026-10-20T09:00','end':'2026-10-20T09:45'}
        assert admin.post('/life/calendars/new',data=data).status_code==303
        with get_conn() as db:
            row=db.execute('SELECT * FROM life_local_events WHERE user_id=1').fetchone()
            assert row['title']=='Private appointment'
            assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0
        assert 'Private appointment' in admin.get('/life/calendar?month=2026-10').text
        url=f'/life/calendars/local/{row["id"]}/edit'
        assert admin.get(url).status_code==200
        assert admin.post(url,data={'title':'Revised appointment','start':'2026-10-20T10:00','end':'2026-10-20T10:45'}).status_code==303
        with get_conn() as db:assert db.execute('SELECT title FROM life_local_events WHERE id=?',(row['id'],)).fetchone()[0]=='Revised appointment'
        ok,msg=create_pending_user('person-b','Person B','second-strong-password');assert ok,msg
        with get_conn() as db:
            db.execute("UPDATE users SET approved=1 WHERE username='person-b'");db.commit()
        with TestClient(app,follow_redirects=False) as user:
            assert user.post('/login',data={'username':'person-b','password':'second-strong-password','next':'/life'}).status_code==303
            assert user.get(url).status_code==404
            assert 'Private appointment' not in user.get('/life/calendar?month=2026-10').text
            assert 'MLO only' in user.get('/life/calendars/new').text
            assert user.post('/life/calendars/new',data={**data,'title':'Person B calendar event'}).status_code==303
            assert admin.get('/life/calendars/local/99999/edit').status_code==404
        # Create a linked Google account, authorize writing and ensure one API write.
        with get_conn() as db:
            cur=db.execute('''INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at)
              VALUES(?,?,?,?,?,?)''',(1,'google','my@gmail.com','my@gmail.com',
                cal._encrypt(cal.json_dump({'access_token':'test-token','scope':'https://www.googleapis.com/auth/calendar.events',
                                           '_expires_at':9999999999})), '2026-10-14'))
            connection_id=cur.lastrowid;db.commit()
        assert f'external:{connection_id}' in admin.get('/life/calendars/new').text
        with patch.object(cal,'_request',side_effect=fake_request):
            assert admin.get(f'/life/calendars/{connection_id}/calendars.json').json()['calendars'][0]['name']=='Calendar A'
            r=admin.post('/life/calendars/new',data={**data,'destination':f'external:{connection_id}',
                'calendar_id':'my-cal','title':'Google write'});
            assert r.status_code==303
        assert len([c for c in requests if c[0]=='POST'])==1
        with get_conn() as db:
            assert db.execute('SELECT COUNT(*) FROM life_local_events WHERE user_id=1').fetchone()[0]==1
            assert db.execute('SELECT COUNT(*) FROM life_external_events WHERE connection_id=?',(connection_id,)).fetchone()[0]==1
        with TestClient(app,follow_redirects=False) as user:
            assert user.post('/login',data={'username':'person-b','password':'second-strong-password','next':'/life'}).status_code==303
            assert user.get(f'/life/calendars/{connection_id}/calendars.json').status_code==404
            assert user.post('/life/calendars/new',data={**data,'destination':f'external:{connection_id}',
                              'calendar_id':'my-cal'}).status_code==404
        # Background sync keeps successful caches; failed refreshes do not delete them.
        calls=[]
        def refreshed(provider,token,cid):
            calls.append(cid)
            return [('my-cal:remote-2','Remote event','2026-10-21','2026-10-21T08:00:00Z','', 'Calendar A')]
        with patch.object(cal,'_get_events',side_effect=refreshed):
            assert cal.sync_due_calendars()>=1
            assert cal.sync_due_calendars()==0
        assert calls==[connection_id]
        with get_conn() as db:
            assert db.execute('SELECT COUNT(*) FROM life_external_events WHERE connection_id=?',(connection_id,)).fetchone()[0]==1
            db.execute('UPDATE life_calendar_connections SET last_sync_attempt_at=NULL WHERE id=?',(connection_id,));db.commit()
        with patch.object(cal,'_get_events',side_effect=RuntimeError('provider temporarily unavailable')):
            assert cal.sync_due_calendars()>=1
        with get_conn() as db:
            assert db.execute('SELECT COUNT(*) FROM life_external_events WHERE connection_id=?',(connection_id,)).fetchone()[0]==1
            assert db.execute('SELECT last_error FROM life_calendar_connections WHERE id=?',(connection_id,)).fetchone()[0]
        assert admin.post(f'/life/calendars/local/{row["id"]}/delete',data={'confirm':'DELETE'}).status_code==303
        with get_conn() as db:assert db.execute('SELECT id FROM life_local_events WHERE id=?',(row['id'],)).fetchone() is None
print('PASS v3.5 unified event creation, private records, provider routing and automatic sync')
