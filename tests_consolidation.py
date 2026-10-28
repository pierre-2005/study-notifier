"""Consolidation regression suite. Runs against a disposable SQLite DB."""
import os, sys, tempfile, types
from pathlib import Path
from datetime import datetime, timezone

class NoopScheduler:
    def shutdown(self,wait=False): pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda _: NoopScheduler()
sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as root:
    os.environ.update({
        'STUDY_NOTIFIER_DB':str(Path(root)/'test.db'),
        'SESSION_SECRET':'local-testing-only',
        'COOKIE_SECURE':'false',
        'APP_USERNAME':'admin','APP_PASSWORD':'consolidation-test-password',
    })
    from app.db import init_db, get_conn
    from app.auth import init_auth_schema, ensure_bootstrap_admin, create_pending_user
    from app.main import app
    from app.lifeos import init_life_schema
    from app.consolidation import consolidate_todos
    from fastapi.testclient import TestClient

    # Simulate data from an old installation, before any LifeOS records.
    init_db();init_auth_schema();ensure_bootstrap_admin('admin','consolidation-test-password')
    with get_conn() as c:
        time=datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO todos(title,notes,due_at_utc,status,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
                  ('Legacy private checklist','Migrate once',time,'todo',time,time))
        c.execute('INSERT INTO courses(name,term,color,created_at_utc) VALUES(?,?,?,?)',('ENEL Test','Fall','#6285ab',time))
        c.execute("INSERT INTO items(course_id,type,title,notes,due_at_utc,status,priority,created_at_utc,updated_at_utc) VALUES(1,'exam','Private midterm','',?,'todo',2,?,?)",(time,time,time))
        c.execute('INSERT INTO expenses(title,category,amount,due_at_utc,status,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?,?)',('Secret bill','Home',75,time,'unpaid',time,time))
        c.execute("INSERT INTO jobs(company,role,status,created_at_utc,updated_at_utc) VALUES('Private Company','Engineer','applied',?,?)",(time,time))
        c.commit()
    with TestClient(app,follow_redirects=True) as a:
        a.post('/login',data={'username':'admin','password':'consolidation-test-password','next':'/life'})
        with get_conn() as c:
            t=c.execute("SELECT id,owner_id FROM life_tasks WHERE title='Legacy private checklist'").fetchone()
            assert t is not None
            assert c.execute('SELECT COUNT(*) FROM life_legacy_todo_map').fetchone()[0]==1
            assert Path(root,'test.pre-mlo-v3.1.sqlite.backup').is_file()
        assert consolidate_todos()==0, 'Migration should be idempotent'
        for path,needle in [('/life','Private midterm'),('/life/study','ENEL Test'),('/life/work','Private Company'),('/expenses','Secret bill'),('/life/spaces','Spaces'),('/life/calendar','Private midterm'),('/life/focus','Timers'),('/courses','ENEL Test'),('/items','Private midterm'),('/jobs','Private Company'),('/expenses','Secret bill')]:
            res=a.get(path)
            assert res.status_code==200,(path,res.status_code,res.text[:1500])
            assert needle in res.text,(path,needle,res.text[:1500])
        assert a.get('/life/money',follow_redirects=False).headers['location']=='/finance'
        html=a.get('/life').text
        assert 'CLASSIC TOOLS' not in html
        assert 'My tasks' in html and 'Work & career' in html
        assert a.get('/classic/dashboard').url.path=='/life'
        assert a.get('/todos').url.path=='/life/tasks'
        assert a.get('/schedule').url.path=='/life/calendar'
        assert a.get('/timers').url.path=='/life/focus'
        a.post('/life/tasks/'+str(t['id'])+'/status',data={'status':'done'})
        with get_conn() as c:
            assert c.execute('SELECT status FROM todos WHERE title=?',('Legacy private checklist',)).fetchone()['status']=='done'
        # Old row is preserved; deleting a migrated task must not recreate it on restart.
        a.post('/life/tasks/'+str(t['id'])+'/delete')
        assert consolidate_todos()==0
        with get_conn() as c:
            assert c.execute('SELECT task_id FROM life_legacy_todo_map').fetchone()['task_id'] is None
        ok,msg=create_pending_user('collaborator','Collab','safe-password-123')
        assert ok,msg
        with get_conn() as c:
            c.execute("UPDATE users SET approved=1 WHERE username='collaborator'");c.commit()
        with TestClient(app,follow_redirects=True) as b:
            b.post('/login',data={'username':'collaborator','password':'safe-password-123','next':'/life'})
            for path in ('/life','/life/study','/life/work','/life/money','/life/calendar'):
                page=b.get(path)
                assert page.status_code==200,(path,page.status_code,page.text[:400])
                for secret in ('Private midterm','Secret bill','Private Company','ENEL Test'):
                    assert secret not in page.text,(path,secret)
    print('PASS: legacy import idempotency, tombstone, Today/Study/Work/Money/Calendar wiring, redirects, private data isolation, existing data preserved, new backup')
