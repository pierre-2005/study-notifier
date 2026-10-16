"""MLO 3.6.3: finance compatibility, PWA public visibility, device QR isolation."""
from __future__ import annotations
import os,sys,tempfile,types,io,sqlite3
from pathlib import Path
class Scheduler:
    def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda timezone:Scheduler();sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as temp:
    os.environ.update(STUDY_NOTIFIER_DB=str(Path(temp)/'data.db'),SESSION_SECRET='local-test-not-production',
       APP_USERNAME='admin',APP_PASSWORD='password12345',COOKIE_SECURE='false',MLO_PUBLIC_URL='https://organizer.overvault.ca')
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_conn
    from app.auth import create_pending_user
    with TestClient(app,follow_redirects=False) as admin:
        assert admin.get('/manifest.webmanifest').status_code == 200
        assert admin.get('/manifest.webmanifest').json()['name']=='My Life Organized'
        assert admin.get('/service-worker.js').status_code==200
        assert admin.post('/login',data={'username':'admin','password':'password12345'}).status_code==303
        for path in ('/finance','/finance/budget','/finance/transactions','/finance/monthly','/finance/rules','/finance/import'):
            r=admin.get(path)
            assert r.status_code==200,(path,r.status_code,r.text[:400])
            assert 'finance-unified-tabs' in r.text, path
            assert '>Budget<' in r.text, path
        menu=admin.get('/finance').text
        assert 'data-nav-key="life-money"' in menu
        assert '<a href="/finance"' in menu
        # Migrate to an older budget table missing the expected unique index.
        with get_conn() as c:
            c.execute('ALTER TABLE finance_budget_rows RENAME TO old_budget_rows')
            c.execute('''CREATE TABLE finance_budget_rows (
               section TEXT NOT NULL, name TEXT NOT NULL, amount REAL NOT NULL DEFAULT 0,
               frequency TEXT NOT NULL DEFAULT 'Monthly', created_at_utc TEXT NOT NULL,
               updated_at_utc TEXT NOT NULL)''')
            c.execute('INSERT INTO finance_budget_rows SELECT * FROM old_budget_rows')
            c.execute('DROP TABLE old_budget_rows')
            c.commit()
        resp=admin.post('/finance/budget/save',data={'name':'My finance plan','row_key':['income_0','income_1'],
          'section__income_0':'income','name__income_0':'Employment (primary)','amount__income_0':'4200',
          'frequency__income_0':'Monthly',
          'section__income_1':'income','name__income_1':'Employment (secondary)','amount__income_1':'0',
          'frequency__income_1':'Monthly'})
        assert resp.status_code==303,(resp.status_code,resp.text[:1000])
        assert resp.headers['location']=='/finance/budget?saved=1'
        assert 'Budget saved successfully' in admin.get(resp.headers['location']).text
        assert admin.post('/finance/budget/save',data={'name':'AJAX safe'},headers={'accept':'application/json'}).json()['ok'] is True
        with get_conn() as c:
            saved=c.execute("SELECT amount FROM finance_budget_rows WHERE section='income' AND name='Employment (primary)'").fetchone()
            assert saved and saved['amount']==4200
        # Verify a simulated SQLite write failure produces a readable branded view.
        from app.finance import service
        original=service.save_budget_rows
        def fail(*args,**kwargs):raise sqlite3.OperationalError('mock write failure')
        service.save_budget_rows=fail
        try:
            r=admin.post('/finance/budget/save',data={'name':'fail'})
            assert r.status_code==503,(r.status_code,r.text[:500])
            assert 'Budget could not be saved' in r.text
            ajax=admin.post('/finance/budget/save',data={'name':'fail'},headers={'accept':'application/json'})
            assert ajax.status_code==503 and 'could not be saved' in ajax.json()['detail']
            assert 'finance-unified-tabs' in r.text
        finally: service.save_budget_rows=original
        assert admin.post('/life/devices',data={'name':'My iPhone'}).status_code==303
        with get_conn() as c:
            device=c.execute('SELECT id,topic FROM life_devices ORDER BY id DESC LIMIT 1').fetchone()
            id,topic=device['id'],device['topic']
        qr=admin.get(f'/life/devices/{id}/qr.png')
        assert qr.status_code==200 and qr.headers['content-type']=='image/png'
        assert qr.content.startswith(b'\x89PNG\r\n\x1a\n')
        assert qr.headers.get('cache-control')=='private, no-store'
        assert 'Pair phone with QR code' in admin.get('/life/devices').text
        ok,msg=create_pending_user('beta','Beta user','beta-password-123')
        assert ok,msg
        with get_conn() as c:
            c.execute("UPDATE users SET approved=1 WHERE username='beta'");c.commit()
        with TestClient(app,follow_redirects=False) as beta:
            assert beta.post('/login',data={'username':'beta','password':'beta-password-123'}).status_code==303
            assert beta.get(f'/life/devices/{id}/qr.png').status_code==404
            assert topic not in beta.get('/life/devices').text
print('PASS: finance tabs on all main views, legacy schema budget save, styled failure, public PWA, owner-private QR')
