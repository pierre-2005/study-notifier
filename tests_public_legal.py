"""Regression tests for Google OAuth public pages. No network calls or production database."""
import os, tempfile, types, sys
from pathlib import Path
from contextlib import ExitStack

class DummyScheduler:
    def shutdown(self, wait=False): pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda timezone: DummyScheduler()
sys.modules['app.scheduler']=stub

with tempfile.TemporaryDirectory() as tmp:
    os.environ.update({
        'STUDY_NOTIFIER_DB':str(Path(tmp)/'legal-test.db'),
        'MLO_ATTACHMENT_DIR':str(Path(tmp)/'files'),
        'SESSION_SECRET':'test-session-secret-not-production',
        'APP_USERNAME':'legal_admin',
        'APP_PASSWORD':'only-test-password',
        'MLO_LEGAL_CONTACT_EMAIL':'hello@example.org',
        'COOKIE_SECURE':'false',
    })
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, follow_redirects=False) as visitor:
        for route,token in [('/','Make room for'),('/privacy','Privacy Policy'),('/termsofservice','Terms of Service')]:
            r=visitor.get(route)
            assert r.status_code == 200,(route,r.status_code,r.text[:200])
            assert 'text/html' in r.headers.get('content-type',''),route
            assert token in r.text,(route,token)
            assert 'href="/privacy"' in r.text
            assert 'href="/termsofservice"' in r.text
            assert 'href="/static/public-legal.css?' in r.text
        assert 'Google API Services User Data Policy' in visitor.get('/privacy').text
        assert 'hello@example.org' in visitor.get('/privacy').text
        assert 'hello@example.org' in visitor.get('/termsofservice').text
        assert visitor.get('/static/public-legal.css').status_code == 200
        assert visitor.get('/life').status_code in (302,303,307)
        assert '/login' in visitor.get('/life').headers['location']
        assert visitor.get('/login').status_code == 200
        assert 'href="/privacy"' in visitor.get('/login').text
        assert 'href="/termsofservice"' in visitor.get('/signup').text
        signed=visitor.post('/login',data={'username':'legal_admin','password':'only-test-password','next':'/life'})
        assert signed.status_code in (302,303)
        assert visitor.get('/').status_code == 303
        assert visitor.get('/').headers['location'] == '/life'
        assert visitor.get('/privacy').status_code == 200
        assert visitor.get('/termsofservice').status_code == 200
        assert 'href="/privacy"' in visitor.get('/life').text
print('PASS: public homepage, privacy, terms, static styling, public access, and authenticated redirection')
