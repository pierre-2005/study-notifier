"""Account-owned appearance settings, persistence and authorization boundaries."""
import os, sys, types, tempfile
from pathlib import Path
from cryptography.fernet import Fernet
class NoopScheduler:
    def shutdown(self,wait=False): pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda _:NoopScheduler()
sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as tmp:
    os.environ.update({'SESSION_SECRET':'test-secret-appearance-test','APP_USERNAME':'admin',
      'APP_PASSWORD':'sufficiently-strong-test-password','STUDY_NOTIFIER_DB':str(Path(tmp)/'app.db'),
      'COOKIE_SECURE':'false','MLO_CREDENTIAL_KEY':Fernet.generate_key().decode()})
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import create_pending_user
    with TestClient(app) as alice:
        assert alice.post('/login',data={'username':'admin','password':'sufficiently-strong-test-password','next':'/life'}).status_code in (200,303)
        url='/life/layout/appearance'
        expected={'theme':'dark','palette':'ocean','palette_style':'full'}
        assert alice.post(url,json=expected).status_code==200
        assert alice.get(url).json()==expected
        html=alice.get('/life').text
        assert '"palette": "ocean"' in html and '"theme": "dark"' in html
        assert alice.post(url,json={'theme':'bad','palette':'ocean','palette_style':'full'}).status_code==422
        assert alice.post(url,json=expected,headers={'Origin':'https://evil.example'}).status_code==403
        assert alice.post(url,json=expected,headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
        ok,msg=create_pending_user('bob','Bob','other-strong-password');assert ok,msg
        from app.db import get_conn
        with get_conn() as conn:
            conn.execute("UPDATE users SET approved=1 WHERE username='bob'");conn.commit()
        with TestClient(app) as bob:
            assert bob.post('/login',data={'username':'bob','password':'other-strong-password','next':'/life'}).status_code in (200,303)
            assert bob.get(url).json()=={'theme':'system','palette':'neutral','palette_style':'independent'}
            other={'theme':'light','palette':'rose','palette_style':'independent'}
            assert bob.post(url,json=other).status_code==200
            assert bob.get(url).json()==other
        assert alice.get(url).json()==expected
        # Verify saved appearance survives a new browser session.
        with TestClient(app) as fresh:
            assert fresh.post('/login',data={'username':'admin','password':'sufficiently-strong-test-password','next':'/life'}).status_code in (200,303)
            assert fresh.get(url).json()==expected
        print('PASS: per-account server appearance, browser independence, input validation, CSRF guard')
