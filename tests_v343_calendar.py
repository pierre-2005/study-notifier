"""v3.4.3: calendar writes (mocked providers), permissions, setup diagnostics."""
import os,sys,types,tempfile
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet
class NoopScheduler:
    def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda _:NoopScheduler();sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as temp:
    os.environ.update({'SESSION_SECRET':'development-session-secret-123','APP_USERNAME':'admin',
        'APP_PASSWORD':'strong-test-password','STUDY_NOTIFIER_DB':str(Path(temp)/'app.db'),
        'COOKIE_SECURE':'false','TIMEZONE':'America/Edmonton','MLO_CREDENTIAL_KEY':Fernet.generate_key().decode()})
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_conn
    from app.auth import create_pending_user
    from app import calendar_links as links
    class Reply:
        def __init__(self,payload=None):self.payload=payload or {}
        def json(self):return self.payload
    calls=[]
    def mock_request(method,url,**kw):
        calls.append((method,url,kw))
        if url.endswith('/calendarList'):
            return Reply({'items':[{'id':'cal@google.com','summary':'Primary','accessRole':'owner'},
                                   {'id':'readonly@google.com','summary':'Readonly','accessRole':'reader'}]})
        if url.endswith('/events') and method=='POST':
            return Reply({'id':'event1','summary':kw['json']['summary'],'start':kw['json']['start'],'htmlLink':'https://calendar.google.com/calendar/event?eid=example'})
        if url.endswith('/event1') and method=='GET':
            return Reply({'id':'event1','summary':'Sample meeting','start':{'dateTime':'2026-11-01T09:00:00-07:00'},'end':{'dateTime':'2026-11-01T10:00:00-07:00'}})
        if url.endswith('/event1') and method=='PATCH':
            return Reply({'id':'event1','summary':kw['json']['summary'],'start':kw['json']['start']})
        if url.endswith('/event1') and method=='DELETE':return Reply({})
        raise AssertionError((method,url,kw))
    with TestClient(app,follow_redirects=True) as alice:
        alice.post('/login',data={'username':'admin','password':'strong-test-password','next':'/life'})
        page=alice.get('/life/calendars')
        assert page.status_code==200 and 'Connection not configured' in page.text
        assert 'MLO_GOOGLE_CLIENT_ID' in page.text
        assert 'Admin setup needed' not in page.text
        with get_conn() as db:
            cur=db.execute('''INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at)
                 VALUES(?,?,?,?,?,?)''',(1,'google','my-work@gmail.com','my-work@gmail.com',
                  links._encrypt(links.json_dump({'access_token':'mock-token','scope':'https://www.googleapis.com/auth/calendar.events',
                                  '_expires_at':9999999999})), '2026-10-13'))
            connection_id=cur.lastrowid
            db.commit()
        with patch.object(links,'_request',mock_request):
            # Only editable calendars are offered
            r=alice.get(f'/life/calendars/{connection_id}/events/new');assert r.status_code==200,r.text[-800:]
            assert 'Primary' in r.text and 'Readonly' not in r.text
            denied=alice.post(f'/life/calendars/{connection_id}/events/new',data={
                'calendar_id':'readonly@google.com','title':'Should not create','start':'2026-11-01T09:00',
                'end':'2026-11-01T10:00'})
            assert denied.status_code==422,denied.status_code
            assert alice.post(f'/life/calendars/{connection_id}/events/new',data={
                'calendar_id':'cal@google.com','title':'Sample meeting','start':'2026-11-01T09:00',
                'end':'2026-11-01T10:00'}).status_code==200
            assert any(method=='POST' and '/events' in url for method,url,_ in calls)
            with get_conn() as db:
                row=db.execute('SELECT uid FROM life_external_events WHERE connection_id=?',(connection_id,)).fetchone()
                assert row is not None
                event_uid=row['uid']
            from urllib.parse import quote
            uri=quote(event_uid,safe='')
            edit=alice.get(f'/life/calendars/{connection_id}/events/{uri}/edit')
            assert edit.status_code==200
            assert 'Sample meeting' in edit.text
            assert alice.post(f'/life/calendars/{connection_id}/events/{uri}/edit',data={
                'title':'Updated meeting','start':'2026-11-01T09:00','end':'2026-11-01T10:30'}).status_code==200
            assert any(method=='PATCH' for method,_,_ in calls)
            assert alice.post(f'/life/calendars/{connection_id}/events/{uri}/delete',data={'confirm':'NO'}).status_code==422
            ok,msg=create_pending_user('another-person','Another person','strong-another-password');assert ok,msg
            with get_conn() as db:db.execute("UPDATE users SET approved=1 WHERE username='another-person'");db.commit()
            with TestClient(app,follow_redirects=True) as bob:
                bob.post('/login',data={'username':'another-person','password':'strong-another-password','next':'/life'})
                assert bob.get(f'/life/calendars/{connection_id}/events/new').status_code==404
                assert bob.post(f'/life/calendars/{connection_id}/events/{uri}/delete',data={'confirm':'DELETE'}).status_code==404
            assert alice.post(f'/life/calendars/{connection_id}/events/{uri}/delete',data={'confirm':'DELETE'}).status_code==200
            assert any(method=='DELETE' for method,_,_ in calls)
            with get_conn() as db:
                assert db.execute('SELECT COUNT(*) FROM life_external_events WHERE connection_id=?',(connection_id,)).fetchone()[0]==0
        with get_conn() as db:
            db.execute('UPDATE life_calendar_connections SET secret_blob=? WHERE id=?',(
               links._encrypt(links.json_dump({'access_token':'readonly-token','scope':'https://www.googleapis.com/auth/calendar.readonly'})),connection_id))
            db.commit()
        assert alice.get(f'/life/calendars/{connection_id}/events/new').status_code==409
        # Microsoft Graph: independently verify delegated access and outbound payloads.
        with get_conn() as db:
            cur=db.execute('INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at) VALUES(?,?,?,?,?,?)',
               (1,'microsoft','me@outlook.com','me@outlook.com',
                links._encrypt(links.json_dump({'access_token':'ms-token','scope':'Calendars.ReadWrite','_expires_at':9999999999})), '2026-10-13'))
            ms_id=cur.lastrowid
            db.commit()
        def ms_request(method,url,**kw):
            if url.endswith('/me/calendars'):
                return Reply({'value':[{'id':'outlookcal','name':'Primary Outlook','canEdit':True}]})
            if method=='POST' and url.endswith('/outlookcal/events'):
                data=kw['json'];assert data['start']['timeZone']=='UTC'
                assert data['subject']=='Outlook meeting'
                return Reply({'id':'ms-event-1','subject':data['subject'],'start':data['start']})
            raise AssertionError((method,url))
        with patch.object(links,'_request',ms_request):
            assert 'Primary Outlook' in alice.get(f'/life/calendars/{ms_id}/events/new').text
            assert alice.post(f'/life/calendars/{ms_id}/events/new',data={
               'calendar_id':'outlookcal','title':'Outlook meeting',
               'start':'2026-11-01T09:00','end':'2026-11-01T09:30'}).status_code==200
        with get_conn() as db:
            assert db.execute('SELECT COUNT(*) FROM life_external_events WHERE connection_id=?',(ms_id,)).fetchone()[0]==1
print('PASS v3.4.3: setup diagnostics; provider create/edit/delete; unauthorized access; read-only reconnect guard')
