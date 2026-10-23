"""Upgrade a backed-up database fixture produced by pre-v3.7 main, preserving every original column."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
ATTACHMENT=b'Fixture attachment must survive the upgrade.\n'
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);source=root/'original.sqlite';stage=root/'rehearsal';uploads=root/'uploads';uploads.mkdir()
    original_upload=root/'original-uploads';original_upload.mkdir()
    for folder in (uploads,original_upload):(folder/'preserved-fixture.txt').write_bytes(ATTACHMENT)
    with sqlite3.connect(source) as original:
        original.execute('PRAGMA journal_mode=WAL');original.execute('PRAGMA wal_autocheckpoint=0')
        original.executescript((ROOT/'tests/fixtures/pre_v37_main.sql').read_text())
        original.execute("INSERT INTO finance_settings(key,value) VALUES('wal-sentinel','Uncheckpointed fixture data')");original.commit()
        assert Path(str(source)+'-wal').exists()
        baseline=list(original.iterdump())
        env={**os.environ,'APP_USERNAME':'fixture_admin','APP_PASSWORD':'','MLO_ATTACHMENT_DIR':str(uploads),
            'MLO_CREDENTIAL_KEY':'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
            'SESSION_SECRET':'upgrade-fixture-only','MLO_SCHEDULER_ENABLED':'false','MLO_CALENDAR_AUTO_SYNC':'false','MLO_SMTP_HOST':'','COOKIE_SECURE':'false'}
        result=subprocess.run([sys.executable,'-m','scripts.rehearse_v37','--source',str(source),'--work-dir',str(stage),
            '--legacy-owner-username','fixture_admin'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
        assert result.returncode==0,result.stdout+result.stderr
        report=json.loads(result.stdout);assert report['original_tables_preserved']==49,report
        assert report['migration_idempotent'] and report['restoration_matches_baseline']
        assert list(original.iterdump())==baseline,'Read-only source changed'
    for folder in (uploads,original_upload):assert (folder/'preserved-fixture.txt').read_bytes()==ATTACHMENT
    check=r'''
import json
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.calendar_links import _decrypt
with TestClient(app,follow_redirects=False) as alice,TestClient(app,follow_redirects=False) as admin,TestClient(app,follow_redirects=False) as viewer:
    assert alice.post('/login',data={'username':'alice','password':'UpgradeMemberPassword!123'}).status_code==303
    assert admin.post('/login',data={'username':'fixture_admin','password':'UpgradeFixturePassword!123'}).status_code==303
    assert viewer.post('/login',data={'username':'viewer','password':'UpgradeMemberPassword!123'}).status_code==303
    assert alice.get('/life').status_code==200
    assert alice.get('/life/tasks/1').status_code==200
    assert admin.get('/life/tasks/1').status_code==404
    assert viewer.post('/life/projects',data={'name':'Forbidden project'}).status_code==403
    assert alice.get('/life/files/1').content==b'Fixture attachment must survive the upgrade.\n'
    assert admin.get('/life/files/1').status_code==404
    assert alice.get('/life/layout').json()['nav_labels']['life-tasks']=='My action list'
    with get_conn() as db:assert db.execute("SELECT theme,palette,palette_style FROM life_appearance WHERE user_id=(SELECT id FROM users WHERE username='alice')").fetchone()[:]==('dark','sage','full')
    assert admin.get('/finance').status_code==200
    response=alice.get('/finance');assert response.status_code in (303,403),response.text[:300]
    with get_conn() as db:
        row=db.execute("SELECT * FROM users WHERE username='alice'").fetchone()
        assert row['requires_email_verification']==0 and row['approved']==1
        assert db.execute("SELECT approved FROM users WHERE username='pending'").fetchone()[0]==0
        assert db.execute("SELECT amount FROM finance_budget_rows WHERE section='expenses' AND name='Groceries'").fetchone()[0]==123
        assert db.execute("SELECT description FROM finance_transactions").fetchone()[0]=='Fixture groceries'
        assert json.loads(_decrypt(db.execute('SELECT secret_blob FROM life_calendar_connections').fetchone()[0]))['refresh_token']=='FAKE_FIXTURE_ONLY'
        assert db.execute('SELECT COUNT(*) FROM life_project_members').fetchone()[0]==2
        assert db.execute('SELECT parent_id FROM life_tasks WHERE id=2').fetchone()[0]==1
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
'''
    result=subprocess.run([sys.executable,'-c',check],cwd=ROOT,env={**env,'STUDY_NOTIFIER_DB':str(stage/'staging.sqlite')},capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert (original_upload/'preserved-fixture.txt').read_bytes()==ATTACHMENT
    print(json.dumps({**report,'fixture_origin':'main ba3aba3f932753de1dc9014c52558768b84f0b38','attachment_sha256':hashlib.sha256(ATTACHMENT).hexdigest(),
        'verified':'original values, permission denial, roles, grandfathered login, nested records, encrypted OAuth round-trip, finance, uploads and rollback'},indent=2))
print('PASS: full pre-v3.7 database fixture backed up, migrated twice, restored and exercised through authenticated routes')
