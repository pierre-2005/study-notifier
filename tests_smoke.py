"""Offline smoke and account-isolation suite. Run with python tests_smoke.py.
Tests replace ONLY the background reminder scheduler when APScheduler isn't installed.
"""
import os,sys,tempfile,types
from pathlib import Path

class NoopScheduler:
    def shutdown(self, wait=False): pass
stub = types.ModuleType('app.scheduler')
stub.start_scheduler = lambda timezone: NoopScheduler()
sys.modules['app.scheduler'] = stub

tmp=tempfile.TemporaryDirectory()
os.environ['STUDY_NOTIFIER_DB']=str(Path(tmp.name)/'test.db')
os.environ['SESSION_SECRET']='local-test-secret-is-not-for-production'
os.environ['COOKIE_SECURE']='false'
os.environ['APP_USERNAME']='admin'
os.environ['APP_PASSWORD']='admin-test-password'

from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user

with TestClient(app, follow_redirects=True) as admin:
    assert admin.get('/health').status_code == 200
    login=admin.post('/login',data={'username':'admin','password':'admin-test-password','next':'/life'})
    assert login.status_code==200, (login.status_code,login.text[:500])
    paths=['/life','/life/tasks','/life/projects','/life/notes','/life/calendar','/life/focus','/life/goals','/life/search?q=a']
    for path in paths:
        r=admin.get(path)
        assert r.status_code==200, (path,r.status_code,r.text[:1200])
        assert '<html' in r.text
    a=admin.post('/life/tasks',data={'title':'Top-level private task','next_page':'/life/tasks'})
    assert a.status_code==200
    with get_conn() as c:
        task_id=c.execute("SELECT id FROM life_tasks WHERE title='Top-level private task'").fetchone()['id']
    assert admin.get('/life/tasks/'+str(task_id)).status_code==200
    assert admin.post(f'/life/tasks/{task_id}/status',data={'status':'done'}).status_code==200
    proj=admin.post('/life/projects',data={'name':'Engineering prototype','template':'electrical','area':'Work'})
    assert proj.status_code==200
    with get_conn() as c:
        pid=c.execute('SELECT id FROM life_projects ORDER BY id DESC LIMIT 1').fetchone()['id']
        assert c.execute('SELECT COUNT(*) FROM life_tasks WHERE project_id=?',(pid,)).fetchone()[0]==5
    note=admin.post('/life/notes',data={'title':'Private design memo','body':'confidential testing notes','project_id':str(pid)})
    assert note.status_code==200
    with get_conn() as c:
        nid=c.execute('SELECT id FROM life_notes ORDER BY id DESC').fetchone()['id']
    assert admin.get('/life/projects/'+str(pid)).status_code==200
    assert admin.get('/life/notes/'+str(nid)).status_code==200
    assert admin.post('/life/preferences',data={'experience':'professional'}).status_code==200
    assert admin.get('/life').status_code==200
    assert admin.post('/life/habits',data={'title':'Stretch'}).status_code==200
    assert admin.post('/life/goals',data={'title':'Ship this product'}).status_code==200
    assert admin.post('/life/focus/log',data={'minutes':'45','task_id':str(task_id)}).status_code==200
    assert admin.get('/life/export.json').json()['life_projects'][0]['name']=='Engineering prototype'
    csvtext=admin.get('/life/export-tasks.csv').text
    assert 'Top-level private task' in csvtext
    assert admin.get('/life/search?q=prototype').status_code==200
    ok,msg=create_pending_user('teammate','Teammate','teammate-pass-strong')
    assert ok,msg
    with get_conn() as c:
        uid=c.execute("SELECT id FROM users WHERE username='teammate'").fetchone()['id']
        c.execute("UPDATE users SET approved=1 WHERE id=?",(uid,))
        c.commit()
    with TestClient(app,follow_redirects=True) as other:
        assert other.post('/login',data={'username':'teammate','password':'teammate-pass-strong','next':'/life'}).status_code==200
        for path in paths:
            r=other.get(path)
            assert r.status_code==200, (path,r.status_code,r.text[:1500])
        assert 'Top-level private task' not in other.get('/life/tasks?view=all').text
        assert 'Engineering prototype' not in other.get('/life/projects').text
        assert other.get('/life/projects/'+str(pid)).status_code==404
        assert other.get('/life/tasks/'+str(task_id)).status_code==404
        assert other.get('/life/notes/'+str(nid)).status_code==404
        assert other.get('/life/export.json').json()['life_projects']==[]
        assert other.post(f'/life/tasks/{task_id}/status',data={'status':'done'}).status_code==404
        inv=admin.post(f'/life/projects/{pid}/invite',data={'username':'teammate','role':'viewer'})
        assert inv.status_code==200
        assert other.get('/life/projects/'+str(pid)).status_code==200
        assert other.get('/life/notes/'+str(nid)).status_code==200
        shared_task=other.get('/life/tasks?view=all').text
        assert 'Prepare schematics' in shared_task
        assert 'Top-level private task' not in shared_task
        with get_conn() as c:
            shared_id=c.execute('SELECT id FROM life_tasks WHERE project_id=? LIMIT 1',(pid,)).fetchone()['id']
        assert other.post(f'/life/tasks/{shared_id}/status',data={'status':'done'}).status_code==403
        assert other.post(f'/life/notes/{nid}/edit',data={'title':'Stolen','body':'bad'}).status_code==403
        admin.post(f'/life/projects/{pid}/invite',data={'username':'teammate','role':'editor'})
        assert other.post(f'/life/tasks/{shared_id}/status',data={'status':'done'}).status_code==200
        assert other.post('/life/tasks',data={'title':'Collaborator work','project_id':str(pid)}).status_code==200
        assert 'Collaborator work' in admin.get('/life/projects/'+str(pid)).text
        assert other.post('/life/tasks',data={'title':'Other private task'}).status_code==200
        assert 'Other private task' not in admin.get('/life/tasks?view=all').text
        assert other.post('/life/notes',data={'title':'Other private note'}).status_code==200
        assert 'Other private note' not in admin.get('/life/notes').text
        assert other.get('/finance').url.path=='/life'  # legacy private finance stays admin-only
        assert admin.post(f'/life/projects/{pid}/remove/{uid}').status_code==200
        assert other.get('/life/projects/'+str(pid)).status_code==404
    # Timer task linking and completion idempotency
    admin.post('/timers/new',data={'label':'Deep work','minutes':'25','seconds':'0','task_id':str(task_id)})
    with get_conn() as c:
        tid=c.execute('SELECT id FROM timers ORDER BY id DESC').fetchone()['id']
        from datetime import datetime,timezone,timedelta
        c.execute('UPDATE timers SET started_at_utc=? WHERE id=?',((datetime.now(timezone.utc)-timedelta(minutes=12)).isoformat(),tid))
        c.commit()
    admin.post(f'/timers/{tid}/complete')
    admin.post(f'/timers/{tid}/complete')
    with get_conn() as c:
        assert c.execute('SELECT COUNT(*) FROM life_time_entries WHERE note=?',( 'Deep work',)).fetchone()[0]==1
    print('PASS: routes render; private records isolated; sharing permissions; templates; goals; habits; exports; focus log idempotency')

print('Temporary database cleared.')
tmp.cleanup()
