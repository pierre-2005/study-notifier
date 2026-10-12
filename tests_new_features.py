"""Upload/import/device/backup regression tests without contacting external providers."""
import os,sys,tempfile,types,io
from pathlib import Path
class NoopScheduler:
 def shutdown(self,wait=False): pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda _:NoopScheduler();sys.modules['app.scheduler']=stub
tmp=tempfile.TemporaryDirectory()
os.environ.update({'SESSION_SECRET':'a-long-test-secret','APP_USERNAME':'admin','APP_PASSWORD':'admin-password','STUDY_NOTIFIER_DB':str(Path(tmp.name)/'data.db'),'COOKIE_SECURE':'false'})
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user
from app.backup import pre_v3_backup
with TestClient(app,follow_redirects=True) as a:
    a.post('/login',data={'username':'admin','password':'admin-password','next':'/life'})
    assert a.get('/life/import').status_code==200
    assert a.get('/life/devices').status_code==200
    blob=b'Title,Description,Due Date,Project,Priority\nInspect panel,Client review,2026-10-30,Engineering board,high\nOrder supplies,Prepare BOM,2026-10-31,Engineering board,normal\n'
    response=a.post('/life/import/preview',files={'file':('sample.csv',blob,'text/csv')})
    assert response.status_code==200,response.text[:1000]
    assert '2 tasks' in response.text
    with get_conn() as c:
        impid=c.execute('SELECT id FROM life_import_previews ORDER BY id DESC').fetchone()['id']
    assert a.post(f'/life/import/{impid}/commit').status_code==200
    assert a.get('/life/projects').text.count('Engineering board')>0
    assert a.get('/life/tasks?view=all').text.count('Inspect panel')>0
    assert a.post(f'/life/import/{impid}/commit',follow_redirects=False).status_code==409
    with get_conn() as c:
        tid=c.execute("SELECT id FROM life_tasks WHERE title='Inspect panel'").fetchone()['id']
    res=a.post('/life/files/upload',files={'file':('design.pdf',b'%PDF-1.7 sample content','application/pdf')},data={'task_id':str(tid)})
    assert res.status_code==200,res.text[:1000]
    with get_conn() as c:
        fileid=c.execute('SELECT id FROM life_files ORDER BY id DESC').fetchone()['id']
    assert 'design.pdf' in a.get(f'/life/tasks/{tid}').text
    assert a.get(f'/life/files/{fileid}').content==b'%PDF-1.7 sample content'
    assert a.post('/life/devices',data={'name':'Work phone'}).status_code==200
    assert 'Work phone' in a.get('/life/devices').text
    with get_conn() as c:
        did=c.execute('SELECT id FROM life_devices ORDER BY id DESC').fetchone()['id']
        topic=c.execute('SELECT topic FROM life_devices WHERE id=?',(did,)).fetchone()['topic']
    assert topic.startswith('mlo-')
    ok,msg=create_pending_user('person2','Person 2','person-two-strong')
    assert ok,msg
    with get_conn() as c:
        c.execute("UPDATE users SET approved=1 WHERE username='person2'");c.commit()
    with TestClient(app,follow_redirects=True) as b:
        b.post('/login',data={'username':'person2','password':'person-two-strong','next':'/life'})
        assert b.get(f'/life/files/{fileid}').status_code==404
        assert b.get('/life/devices').status_code==200
        assert 'Work phone' not in b.get('/life/devices').text
        assert b.post(f'/life/devices/{did}/delete',follow_redirects=False).status_code==303
        assert 'Work phone' in a.get('/life/devices').text
        assert b.post('/life/files/upload',files={'file':('bad.pdf',b'data','application/pdf')},data={'task_id':str(tid)}).status_code==404
    assert a.post(f'/life/files/{fileid}/delete').status_code==200
    assert a.get(f'/life/files/{fileid}').status_code==404
    assert a.get('/life/export.json').status_code==200
    assert pre_v3_backup().is_file()
    print('PASS: CSV preview/commit/idempotency; private file upload/download/delete; per-user phones; pre-upgrade backup')
tmp.cleanup()
