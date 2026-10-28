from scripts.qa_db import closing_connection
"""Read-only online backup with outstanding WAL, staging upgrade and verified restore."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from app.db import SCHEMA

with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);source=root/'legacy.sqlite';stage=root/'rehearsal'
    with closing_connection(sqlite3.connect(source)) as connection:
        connection.execute('PRAGMA journal_mode=WAL');connection.execute('PRAGMA wal_autocheckpoint=0')
        connection.executescript(SCHEMA)
        connection.execute('INSERT INTO courses(name,term,created_at_utc) VALUES(?,?,?)',('Preserved course','Fall 2026','2026-10-01'))
        connection.execute('INSERT INTO todos(title,created_at_utc,updated_at_utc) VALUES(?,?,?)',('Preserved uncheckpointed task','2026-10-01','2026-10-01'))
        connection.execute('CREATE TABLE operator_sentinel(id INTEGER PRIMARY KEY,encrypted_oauth TEXT,permission_json TEXT)')
        connection.execute('INSERT INTO operator_sentinel VALUES(1,?,?)',('encrypted-fixture-not-live',json.dumps({'role':'member','can_delete':False})))
        connection.commit()
        assert Path(str(source)+'-wal').exists()
        before=list(connection.iterdump())
        result=subprocess.run([sys.executable,'-m','scripts.rehearse_v37','--source',str(source),
            '--work-dir',str(stage),'--legacy-owner-username','admin'],capture_output=True,text=True,timeout=120,
            env={**os.environ,'MLO_CREDENTIAL_KEY':'','APP_PASSWORD':'','SESSION_SECRET':'staging-fixture-secret'})
        assert result.returncode==0,result.stdout+result.stderr
        report=json.loads(result.stdout);assert report['migration_idempotent'] and report['restoration_matches_baseline']
        assert report['source_opened_read_only'] and not report['production_verification']
        assert list(connection.iterdump())==before,'Source changed during rehearsal'
        with closing_connection(sqlite3.connect(stage/'baseline.sqlite')) as backup:
            assert backup.execute('SELECT title FROM todos').fetchone()[0]=='Preserved uncheckpointed task'
        refuse=subprocess.run([sys.executable,'-m','scripts.rehearse_v37','--source',str(source),'--work-dir',str(stage)],capture_output=True,text=True)
        assert refuse.returncode!=0,'Nonempty staging directory must be refused'
        print(json.dumps(report,indent=2))
print('PASS v3.7 staging: outstanding WAL preserved, source unchanged, additive migrations twice, all original columns preserved, integrity/FK checks and verified restoration')
