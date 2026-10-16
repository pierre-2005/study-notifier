"""MLO v3.6.4: authenticated iPhone pairing QR and PWA manifest fields."""
import os, tempfile, types, sys
from pathlib import Path

class FakeScheduler:
    def shutdown(self, wait=False): pass
stub = types.ModuleType('app.scheduler')
stub.start_scheduler = lambda timezone: FakeScheduler()
sys.modules['app.scheduler'] = stub

with tempfile.TemporaryDirectory() as work:
    os.environ.update(STUDY_NOTIFIER_DB=str(Path(work)/'store.db'),
        SESSION_SECRET='ios-test-not-for-production',APP_USERNAME='rootuser',
        APP_PASSWORD='password12345',COOKIE_SECURE='false',
        MLO_PUBLIC_URL='https://organizer.overvault.ca')
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_conn
    from app.auth import create_pending_user

    with TestClient(app,follow_redirects=False) as owner:
        manifest=owner.get('/manifest.webmanifest')
        assert manifest.status_code==200
        m=manifest.json()
        assert m['orientation']=='any' and m['lang']=='en-CA'
        assert 'productivity' in m['categories']
        assert len(m.get('screenshots', [])) >= 2
        for screen in m['screenshots']:
            assert owner.get(screen['src']).status_code==200,screen['src']
        assert owner.post('/login',data={'username':'rootuser','password':'password12345'}).status_code==303
        assert owner.post('/life/devices',data={'name':'My iPhone'}).status_code==303
        with get_conn() as c:
            d=c.execute('SELECT * FROM life_devices ORDER BY id DESC LIMIT 1').fetchone()
        qr=owner.get(f'/life/devices/{d["id"]}/ios-qr.png')
        assert qr.status_code==200 and qr.content.startswith(b'\x89PNG\r\n\x1a\n')
        assert qr.headers.get('cache-control')=='private, no-store'
        pair=owner.get(f'/life/devices/{d["id"]}/pair-iphone')
        assert pair.status_code==200 and 'Copy topic' in pair.text and d['topic'] in pair.text
        assert pair.headers.get('cache-control')=='private, no-store'
        assert '/ios-qr.png' in owner.get('/life/devices').text
        good,msg=create_pending_user('another','Another','another-password-123')
        assert good,msg
        with get_conn() as c:
            c.execute('UPDATE users SET approved=1 WHERE username=?',('another',));c.commit()
        with TestClient(app,follow_redirects=False) as outsider:
            assert outsider.post('/login',data={'username':'another','password':'another-password-123'}).status_code==303
            assert outsider.get(f'/life/devices/{d["id"]}/ios-qr.png').status_code==404
            assert outsider.get(f'/life/devices/{d["id"]}/pair-iphone').status_code==404
            assert d['topic'] not in outsider.get('/life/devices').text
print('PASS: iPhone owner-private pairing, manifest enhancements, cross-account restrictions')
