"""Regression: event destinations are explicit, Google and Outlook writes remain separate."""
import os, tempfile, types, sys
from pathlib import Path
from cryptography.fernet import Fernet

class NoopScheduler:
    def shutdown(self, wait=False): pass
sched=types.ModuleType('app.scheduler')
sched.start_scheduler=lambda _: NoopScheduler()
sys.modules['app.scheduler']=sched

with tempfile.TemporaryDirectory() as temp:
    os.environ.update({'SESSION_SECRET':'temporary-test-session-secret','APP_USERNAME':'admin',
        'APP_PASSWORD':'strong-test-password','STUDY_NOTIFIER_DB':str(Path(temp)/'db.sqlite'),
        'COOKIE_SECURE':'false','TIMEZONE':'America/Edmonton','MLO_CREDENTIAL_KEY':Fernet.generate_key().decode()})
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_conn
    from app import calendar_links as links
    from app.auth import create_pending_user
    with TestClient(app, follow_redirects=True) as client:
        client.post('/login', data={'username':'admin','password':'strong-test-password','next':'/life'})
        page=client.get('/life/calendar')
        assert page.status_code==200
        assert 'href="/life/calendars/new"' in page.text
        assert 'href="/events/new"' not in page.text
        chooser=client.get('/life/calendars/new')
        assert chooser.status_code==200
        assert 'No Google or Outlook accounts' in chooser.text
        assert 'Create MLO-only event' in chooser.text
        assert 'Create in Google' not in chooser.text
        local=client.get('/events/new')
        assert local.status_code==200
        assert 'does not create a Google or Outlook event' in local.text
        # Add a real-owner connection with a write scope; read-only accounts cannot falsely claim editing.
        with get_conn() as db:
            db.execute("INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at) VALUES(?,?,?,?,?,?)",
                (1,'google','primary@example.com','primary@example.com',links._encrypt(links.json_dump({'access_token':'mock','scope':'https://www.googleapis.com/auth/calendar.events'})),'2026-10-13'))
            db.execute("INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at) VALUES(?,?,?,?,?,?)",
                (1,'microsoft','work@example.com','work@example.com',links._encrypt(links.json_dump({'access_token':'mock','scope':'Calendars.Read'})),'2026-10-13'))
            db.commit()
        chooser=client.get('/life/calendars/new')
        assert 'primary@example.com' in chooser.text
        assert 'Create in Google' in chooser.text
        assert 'work@example.com' in chooser.text
        assert 'Reconnect to enable editing' in chooser.text
        ok,msg=create_pending_user('member','Member','some-test-password'); assert ok,msg
        with get_conn() as db:
            db.execute("UPDATE users SET approved=1 WHERE username='member'");db.commit()
        with TestClient(app,follow_redirects=True) as member:
            member.post('/login',data={'username':'member','password':'some-test-password','next':'/life'})
            m=member.get('/life/calendars/new')
            assert m.status_code==200
            assert 'primary@example.com' not in m.text
            assert 'Create MLO-only event' not in m.text
print('PASS: main calendar routes through chooser; permissions and local-only labels; account isolation')
