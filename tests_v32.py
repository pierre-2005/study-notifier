"""V3.2 regression: stored layout, multi-user isolation, destructive project cleanup, calendars."""
import os,sys,types,tempfile,json
from pathlib import Path
from cryptography.fernet import Fernet
class NoopScheduler:
 def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda _:NoopScheduler();sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as tmp:
 os.environ.update({'SESSION_SECRET':'dev-only-test-secret-123','APP_USERNAME':'admin','APP_PASSWORD':'strong-test-password','STUDY_NOTIFIER_DB':str(Path(tmp)/'app.db'),'COOKIE_SECURE':'false','MLO_CREDENTIAL_KEY':Fernet.generate_key().decode()})
 from fastapi.testclient import TestClient
 from app.main import app
 from app.db import get_conn
 from app.auth import create_pending_user
 from app.life_files import ROOT
 with TestClient(app,follow_redirects=True) as alice:
  assert alice.post('/login',data={'username':'admin','password':'strong-test-password','next':'/life'}).status_code==200
  for path in ['/life','/life/calendar','/life/calendars','/life/projects']:
   r=alice.get(path);assert r.status_code==200,(path,r.status_code,r.text[:800])
  home=alice.get('/life').text
  assert 'data-widget-grid' in home and 'mlo-landscape' in home and 'data-dashboard-edit' in home
  assert 'No setup. No complicated' not in home
  layout=alice.get('/life/layout').json()
  assert 'widget_order' in layout
  layout['nav_labels']={'life-home':'My Command Center'}
  layout['widget_hidden']=['money']
  layout['widget_order']=list(reversed(layout['widget_order']))
  assert alice.post('/life/layout',json=layout).json()['ok']
  assert alice.get('/life/layout').json()['nav_labels']['life-home']=='My Command Center'
  assert alice.post('/life/layout',json={'nav_labels':{'evil':'bad'},'widget_order':['hacked','tasks']}).status_code==200
  assert 'evil' not in alice.get('/life/layout').json()['nav_labels']
  r=alice.post('/life/calendars/feed',data={'provider':'apple','label':'Personal Apple','url':'https://p54-caldav.icloud.com/published/2/example'})
  assert r.status_code==200 and 'Personal Apple' in alice.get('/life/calendars').text
  assert alice.post('/life/calendars/feed',data={'provider':'ical','label':'not safe','url':'http://127.0.0.1:8000/health'}).status_code==422
  project_response=alice.post('/life/projects',data={'name':'Delete Test Project','area':'Work','template':'electrical'},follow_redirects=False)
  assert project_response.status_code==303
  project_id=int(project_response.headers['location'].split('/')[-1])
  with get_conn() as db:
   tid=db.execute('SELECT id FROM life_tasks WHERE project_id=? LIMIT 1',(project_id,)).fetchone()['id']
   assert db.execute('SELECT COUNT(*) FROM life_tasks WHERE project_id=?',(project_id,)).fetchone()[0]>=1
  assert alice.post('/life/files/upload',data={'project_id':str(project_id)},files={'file':('draft.pdf',b'dummy','application/pdf')}).status_code==200
  assert alice.post(f'/life/projects/{project_id}/delete',data={'confirmation':'wrong'}).status_code==422
  ok,msg=create_pending_user('tester2','Different user','strong-password-123');assert ok,msg
  with get_conn() as db:
   db.execute("UPDATE users SET approved=1 WHERE username='tester2'");db.commit()
  with TestClient(app,follow_redirects=True) as bob:
   assert bob.post('/login',data={'username':'tester2','password':'strong-password-123','next':'/life'}).status_code==200
   assert 'My Command Center' not in str(bob.get('/life/layout').json())
   assert bob.get('/life/calendars').status_code==200
   assert 'Personal Apple' not in bob.get('/life/calendars').text
   assert bob.post(f'/life/projects/{project_id}/delete',data={'confirmation':'Delete Test Project'}).status_code==404
  assert alice.post(f'/life/projects/{project_id}/delete',data={'confirmation':'Delete Test Project'},follow_redirects=False).status_code==303
  with get_conn() as db:
   assert db.execute('SELECT COUNT(*) FROM life_tasks WHERE project_id=?',(project_id,)).fetchone()[0]==0
   assert db.execute('SELECT COUNT(*) FROM life_files WHERE project_id=?',(project_id,)).fetchone()[0]==0
  assert alice.get(f'/life/projects/{project_id}').status_code==404
  print('PASS v3.2: responsive dashboard markup, saved private layout, safe calendar connection, multi-account privacy, project delete cascade')
