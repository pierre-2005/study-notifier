"""v3.4 regression tests for pagination, scoped bulk edits, reports and upgrades."""
import os,sys,tempfile,types,re
from pathlib import Path
class NoopScheduler:
    def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda timezone:NoopScheduler()
sys.modules['app.scheduler']=stub
scratch=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(scratch.name)/'mlo.db'),SESSION_SECRET='test-secret-v34',COOKIE_SECURE='false',APP_USERNAME='admin',APP_PASSWORD='admin-pass-strong')
from fastapi.testclient import TestClient
from app.main import app
from app.meta import APP_VERSION
from app.db import get_conn
from app.auth import create_pending_user
from app.lifeos import filtered_tasks
with TestClient(app,follow_redirects=False) as c:
    assert c.post('/login',data={'username':'admin','password':'admin-pass-strong','next':'/life'}).status_code==303
    assert c.get('/life/tasks').status_code==200
    assert c.get('/life/insights').status_code==200
    assert c.get('/life/tasks?project=').status_code==200, 'Empty project selection must not error'
    assert 'Add task' in c.get('/life').text
    assert 'flow34.js' in c.get('/life').text
    assert 'max-age=31536000' in c.get(f'/static/flow34.css?v={APP_VERSION}').headers['cache-control']
    tasks=[(1, None,None,f'Backlog {i:03}', '', 'todo','normal','Personal',None, f'2026-10-10T12:00:00',f'2026-10-10T12:00:00') for i in range(127)]
    with get_conn() as db:
        uid=db.execute("SELECT id FROM users WHERE username='admin'").fetchone()['id']
        db.executemany('''INSERT INTO life_tasks(owner_id,project_id,parent_id,title,description,status,priority,area,due_on,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',[(uid,*t[1:]) for t in tasks])
        db.commit()
    first=c.get('/life/tasks?view=open')
    assert first.status_code==200
    assert '127' in first.text and 'Page 1 of 4' in first.text
    assert c.get('/life/tasks?view=open&page=2').status_code==200
    assert 'Page 2 of 4' in c.get('/life/tasks?view=open&page=2').text
    assert 'Backlog 069' in c.get('/life/tasks?q=Backlog+069').text
    assert 'No matching tasks' in c.get('/life/tasks?q=Backlog%25').text
    assert 'No matching tasks' in c.get('/life/tasks?q=Backlog_').text
    assert c.get('/life/tasks?priority=urgent').status_code==200
    assert c.get('/life/tasks?area=Work').status_code==200
    assert c.get('/life/tasks?sort=priority').status_code==200
    assert c.get('/life/tasks?project=999999').status_code==404
    with get_conn() as db:
        ids=[r['id'] for r in db.execute('SELECT id FROM life_tasks ORDER BY id LIMIT 3')]
    bad=c.post('/life/tasks/batch',data={'ids':[str(ids[0]),'999999'],'operation':'done'})
    assert bad.status_code==404
    with get_conn() as db:
        assert db.execute('SELECT status FROM life_tasks WHERE id=?',(ids[0],)).fetchone()['status']=='todo'
    response=c.post('/life/tasks/batch',data={'ids':[str(x) for x in ids],'operation':'high'})
    assert response.status_code==303
    with get_conn() as db:
        assert all(db.execute('SELECT priority FROM life_tasks WHERE id=?',(x,)).fetchone()['priority']=='high' for x in ids)
    assert c.post('/life/tasks/batch',data={'ids':[str(x) for x in ids],'operation':'done'}).status_code==303
    with get_conn() as db:
        assert all(db.execute('SELECT status FROM life_tasks WHERE id=?',(x,)).fetchone()['status']=='done' for x in ids)
    assert c.get('/life/insights').status_code==200
    assert '3' in c.get('/life/insights').text
    # Saved task views are private per account and removable.
    view=c.post('/life/tasks/views',data={'name':'Weekly high priorities','view':'open','area':'Work','priority':'high','sort':'priority'})
    assert view.status_code==303
    assert 'Weekly high priorities' in c.get('/life/tasks').text
    with get_conn() as db:
        saved=db.execute('SELECT id,query_params FROM life_task_views WHERE user_id=?',(uid,)).fetchone()
        assert 'priority=high' in saved['query_params']
    assert c.post('/life/tasks',data={'title':'Cross-origin blocked'},headers={'Origin':'https://wrong.example'}).status_code==403
    with get_conn() as db:
        assert db.execute('SELECT COUNT(*) FROM life_tasks WHERE title=?',('Cross-origin blocked',)).fetchone()[0]==0
    ok,_=create_pending_user('teammate','Teammate','teammate-pass-strong')
    assert ok
    c.post('/life/projects',data={'name':'Shared proof project','area':'Work','template':'blank'})
    with get_conn() as db:
        project_id=db.execute("SELECT id FROM life_projects WHERE name='Shared proof project'").fetchone()['id']
    c.post('/life/tasks',data={'title':'Viewer must not edit','project_id':str(project_id)})
    with get_conn() as db:
        shared_id=db.execute("SELECT id FROM life_tasks WHERE title='Viewer must not edit'").fetchone()['id']
    with get_conn() as db:
        db.execute("UPDATE users SET approved=1 WHERE username='teammate'")
        db.commit()
    assert c.post(f'/life/projects/{project_id}/invite',data={'username':'teammate','role':'viewer'}).status_code==303
    with TestClient(app,follow_redirects=False) as t:
        assert t.post('/login',data={'username':'teammate','password':'teammate-pass-strong','next':'/life'}).status_code==303
        assert 'Backlog 069' not in t.get('/life/tasks').text
        assert 'Backlog 069' not in t.get('/life/insights').text
        assert 'Weekly high priorities' not in t.get('/life/tasks').text
        assert 'Viewer must not edit' in t.get('/life/tasks?view=all').text
        with get_conn() as db:
            from app.lifeos import filtered_tasks
            entries,*_=filtered_tasks(db,db.execute("SELECT id FROM users WHERE username='teammate'").fetchone()['id'],view='all',query='Viewer must not edit')
            assert len(entries)==1 and entries[0]['can_edit']==0
        assert t.post('/life/tasks/batch',data={'ids':str(shared_id),'operation':'done'}).status_code==403
        assert t.post('/life/tasks/batch',data={'ids':str(ids[0]),'operation':'todo'}).status_code==404
    assert c.get('/life/insights').status_code==200
    assert c.post('/life/tasks/views/'+str(saved['id'])+'/delete').status_code==303
    assert 'Weekly high priorities' not in c.get('/life/tasks').text
    assert (Path(scratch.name)/'mlo.pre-mlo-v3.4.sqlite.backup').exists() # second application lifecycle makes pre-upgrade backup
    print('PASS v3.4: server-side filtering, escaped search, pagination, bulk atomicity, private analytics, assets, quick capture')
scratch.cleanup()
