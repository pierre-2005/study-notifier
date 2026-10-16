"""Public PWA regression: verifies Microsoft PWABuilder-facing entrypoint."""
from __future__ import annotations
import json, os, struct, sys, tempfile, types
from pathlib import Path

class DummyScheduler:
    def shutdown(self, wait=False): pass

stub = types.ModuleType('app.scheduler')
stub.start_scheduler = lambda timezone: DummyScheduler()
sys.modules['app.scheduler'] = stub

with tempfile.TemporaryDirectory() as tmp:
    os.environ.update({
        'STUDY_NOTIFIER_DB': str(Path(tmp) / 'pwa-test.db'),
        'MLO_ATTACHMENT_DIR': str(Path(tmp) / 'files'),
        'SESSION_SECRET': 'test-only-not-production',
        'APP_USERNAME': 'pwa_admin',
        'APP_PASSWORD': 'local-test-password',
        'COOKIE_SECURE': 'false',
    })
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app, follow_redirects=False) as client:
        page = client.get('/')
        assert page.status_code == 200, ('public homepage', page.status_code)
        assert 'rel="manifest" href="/manifest.webmanifest"' in page.text
        assert "navigator.serviceWorker.register('/service-worker.js'" in page.text

        manifest_resp = client.get('/manifest.webmanifest')
        assert manifest_resp.headers.get('cache-control','').startswith('public')
        assert client.get('/static/manifest.webmanifest').status_code == 200
        assert manifest_resp.status_code == 200
        assert 'json' in manifest_resp.headers.get('content-type', '')
        manifest = manifest_resp.json()
        assert manifest.get('name') == 'My Life Organized'
        assert manifest.get('short_name') == 'MLO'
        assert manifest.get('description')
        assert manifest.get('start_url', '').startswith('/')
        assert manifest.get('display') == 'standalone'
        assert manifest.get('id') == '/life', 'Keep stable installed-app identity'
        icons = manifest.get('icons') or []
        for size in (192, 512):
            icon = next((i for i in icons if i.get('sizes') == f'{size}x{size}'), None)
            assert icon is not None, size
            resp = client.get(icon['src'])
            assert resp.status_code == 200, (icon['src'], resp.status_code)
            assert resp.content.startswith(b'\x89PNG\r\n\x1a\n')
            w, h = struct.unpack('>II', resp.content[16:24])
            assert (w, h) == (size, size), (icon['src'], w, h)

        # If this redirects to /login, PWABuilder cannot register a worker.
        worker = client.get('/service-worker.js')
        assert worker.status_code == 200, ('public worker', worker.status_code, worker.headers.get('location'))
        assert 'javascript' in worker.headers.get('content-type', '')
        assert worker.headers.get('Service-Worker-Allowed') == '/'
        assert "url.pathname.startsWith('/static/')" in worker.text
        assert "url.pathname.endsWith('.webmanifest')" in worker.text
        assert 'event.request.mode' not in worker.text  # no navigation interception
        for route in ('/privacy', '/termsofservice'):
            r = client.get(route)
            assert r.status_code == 200
            assert 'rel="manifest"' in r.text
        assert client.get('/life').status_code in (302, 303, 307)
print('PASS: anonymous PWA homepage; linked manifest and icons; public worker; private pages stay protected')
