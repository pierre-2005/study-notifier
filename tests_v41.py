"""Task-map integrity, personal layouts, scan pairing and enhanced-save contracts."""
import json,os,tempfile,time,unittest
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch
_tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(_tmp.name)/'v41.sqlite'),SESSION_SECRET='v41-fixture-secret-only',APP_USERNAME='admin',APP_PASSWORD='FixtureAdminOnly!234',COOKIE_SECURE='false',MLO_PUBLIC_URL='https://organizer.overvault.ca',MLO_SCHEDULER_ENABLED='false',MLO_CALENDAR_AUTO_SYNC='false',MLO_SMTP_HOST='')
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user
from app import phones

class V41Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.owner=TestClient(app,follow_redirects=False);cls.owner.__enter__();cls.owner.post('/login',data={'username':'admin','password':'FixtureAdminOnly!234'})
  cls.others={}
  for name in ('viewer','outsider'):
   create_pending_user(name,name,'FixtureMemberOnly!234')
   with get_conn() as db:db.execute('UPDATE users SET approved=1 WHERE username=?',(name,));db.commit()
   c=TestClient(app,follow_redirects=False);c.post('/login',data={'username':name,'password':'FixtureMemberOnly!234'});cls.others[name]=c
 @classmethod
 def tearDownClass(cls):
  for c in cls.others.values():c.close()
  cls.owner.__exit__(None,None,None);_tmp.cleanup()
 def setUp(self):
  response=self.owner.post('/life/projects',data={'name':self._testMethodName});self.pid=int(response.headers['location'].rsplit('/',1)[1])
  self.owner.post(f'/life/projects/{self.pid}/invite',data={'username':'viewer','role':'viewer'})
 def task(self,name,parent='',**extra):
  r=self.owner.post('/life/tasks',data={'title':name,'project_id':str(self.pid),'parent_id':str(parent),**extra},headers={'X-MLO-Action':'fetch'});self.assertEqual(r.status_code,200,r.text);return r.json()
 def graph(self,client=None):return (client or self.owner).get(f'/api/v4/projects/{self.pid}/map')
 def layout(self,points,version='',client=None,**extra):return (client or self.owner).put(f'/api/v4/projects/{self.pid}/map/layout',json={'points':points,'expected_version':version,**extra})
 def relate(self,source,parent=None,deps=None):return self.owner.post(f'/api/v4/projects/{self.pid}/map/relationships',json={'task_id':source['id'],'parent_id':parent,'prerequisites':deps or [],'expected_updated_at':source['updated_at']})
 def test_graph_uses_existing_ids_and_ownership(self):
  a=self.task('Root');b=self.task('Child',a['id']);g=self.graph().json();self.assertEqual({n['id'] for n in g['nodes']},{a['id'],b['id']});self.assertIn({'from':a['id'],'to':b['id'],'kind':'parent'},g['edges']);self.assertEqual(self.graph(self.others['outsider']).status_code,404);self.assertFalse(self.graph(self.others['viewer']).json()['can_edit'])
 def test_layout_is_personal_and_versioned(self):
  a=self.task('A');point={'id':a['id'],'x':130.5,'y':210.0};first=self.layout([point]);self.assertEqual(first.status_code,200,first.text);version=first.json()['version'];self.assertEqual(self.graph().json()['positions'][str(a['id'])]['x'],130.5)
  viewer=self.layout([{'id':a['id'],'x':10.0,'y':20.0}],client=self.others['viewer']);self.assertEqual(viewer.status_code,200);self.assertEqual(self.graph().json()['positions'][str(a['id'])]['x'],130.5)
  self.assertEqual(self.layout([point]).status_code,409);self.assertEqual(self.layout([point],client=self.others['outsider']).status_code,404);self.assertEqual(self.layout([],version,reset=True).json()['positions'],{})
 def test_layout_validates_before_writes(self):
  a=self.task('A');point={'id':a['id'],'x':10.0,'y':20.0}
  self.assertEqual(self.layout([point,point]).status_code,422);self.assertEqual(self.layout([dict(point,id=987654)]).status_code,422)
  for bad in ('NaN','Infinity','100000000'):
   body='{"points":[{"id":'+str(a['id'])+',"x":'+bad+',"y":0}],"expected_version":""}'
   response=self.owner.put(f'/api/v4/projects/{self.pid}/map/layout',content=body,headers={'Content-Type':'application/json'});self.assertEqual(response.status_code,422,response.text)
  self.assertEqual(self.graph().json()['positions'],{})
 def test_relationship_changes_are_atomic_and_cycle_safe(self):
  a=self.task('A');b=self.task('B');c=self.task('C');changed=self.relate(a,parent=c['id'],deps=[b['id']]);self.assertEqual(changed.status_code,200,changed.text)
  fresh_b=next(n for n in changed.json()['nodes'] if n['id']==b['id']);failed=self.relate(fresh_b,parent=a['id'],deps=[a['id']]);self.assertEqual(failed.status_code,409,failed.text)
  result=self.graph().json();self.assertIsNone(next(n for n in result['nodes'] if n['id']==b['id'])['parent_id']);self.assertNotIn({'from':a['id'],'to':b['id'],'kind':'prerequisite'},result['edges'])
  fresh_c=next(n for n in result['nodes'] if n['id']==c['id']);self.assertEqual(self.relate(fresh_c,parent=a['id']).status_code,409)
 def test_relationship_acl_and_stale_revision(self):
  a=self.task('A');body={'task_id':a['id'],'parent_id':None,'prerequisites':[],'expected_updated_at':a['updated_at']}
  self.assertEqual(self.others['viewer'].post(f'/api/v4/projects/{self.pid}/map/relationships',json=body).status_code,403)
  self.owner.post(f'/api/v4/projects/{self.pid}/move',json={'task_id':a['id'],'status':'doing'});self.assertEqual(self.owner.post(f'/api/v4/projects/{self.pid}/map/relationships',json=body).status_code,409)
 def test_enhanced_redirect_skips_followup_page_but_preserves_session(self):
  response=self.owner.post(f'/life/projects/{self.pid}/edit',data={'name':'Changed project','status':'active'},headers={'X-MLO-Enhanced':'1','Accept':'application/json'});self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['redirect'],f'/life/projects/{self.pid}');self.assertIn('set-cookie',response.headers);self.assertEqual(self.owner.get(f'/life/projects/{self.pid}').status_code,200)
  a=self.task('A');r=self.owner.post(f'/life/tasks/{a["id"]}/edit',data={'title':''},headers={'X-MLO-Enhanced':'1','Accept':'application/json'});self.assertEqual(r.status_code,422);self.assertNotIn('redirect',r.json())
 def test_no_login_qr_is_bounded_scoped_and_revocable(self):
  self.owner.post('/life/devices',data={'name':'Pairing fixture'})
  with get_conn() as db:d=dict(db.execute('SELECT * FROM life_devices ORDER BY id DESC LIMIT 1').fetchone())
  import qrcode
  original=qrcode.QRCode.add_data;links=[]
  def record(qr,value,*args,**kwargs):links.append(value);return original(qr,value,*args,**kwargs)
  with patch.object(qrcode.QRCode,'add_data',record):
   for endpoint in ('qr.png','ios-qr.png'):self.assertEqual(self.owner.get(f'/life/devices/{d["id"]}/{endpoint}').status_code,200)
  guest=TestClient(app,follow_redirects=False)
  try:
   for link in links:
    path=urlsplit(link).path+'?'+urlsplit(link).query;r=guest.get(path);self.assertEqual(r.status_code,200,r.text);self.assertIn(d['topic'],r.text);self.assertNotIn('Sign in',r.text);self.assertEqual(r.headers['referrer-policy'],'no-referrer');self.assertEqual(r.headers['cache-control'],'private, no-store');self.assertIn('noindex',r.headers['x-robots-tag'])
   path=urlsplit(links[0]).path;self.assertEqual(guest.get(path+'broken').status_code,404)
   with patch('itsdangerous.timed.time.time',return_value=time.time()+phones.PAIR_MAX_AGE+3):self.assertEqual(guest.get(path).status_code,410)
   self.assertEqual(self.others['outsider'].get(f'/life/devices/{d["id"]}/qr.png').status_code,404)
   self.owner.post(f'/life/devices/{d["id"]}/delete');self.assertEqual(guest.get(path).status_code,404)
  finally:guest.close()
 def test_recurring_completion_counters_are_authoritative(self):
  task=self.task('Recurring task',recurrence='daily',due_on='2026-11-01');path=f'/life/tasks/{task["id"]}/status';headers={'X-MLO-Action':'fetch'}
  for status,delta in [('done',0),('todo',1),('done',-1),('done',0)]:
   response=self.owner.post(path,data={'status':status},headers=headers);self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['open_delta'],delta)
  with get_conn() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM life_tasks WHERE project_id=?',(self.pid,)).fetchone()[0],2)
 def test_large_map_keeps_real_count_and_existing_tasks(self):
  with get_conn() as db:
   uid=db.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
   db.executemany('INSERT INTO life_tasks(owner_id,project_id,title,created_at,updated_at) VALUES(?,?,?,?,?)',[(uid,self.pid,f'Boundary task {i}','fixture','fixture') for i in range(2001)]);db.commit()
  data=self.graph().json();self.assertEqual(data['total'],2001);self.assertEqual(data['limit'],2000);self.assertEqual(data['nodes'],[])
  self.assertEqual(self.layout([]).status_code,422)
  with get_conn() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM life_tasks WHERE project_id=?',(self.pid,)).fetchone()[0],2001)
 def test_new_table_is_additive_and_idempotent(self):
  a=self.task('Existing task')
  from app.v4_schema import init_v4_schema
  with get_conn() as db:before=tuple(db.execute('SELECT * FROM life_tasks WHERE id=?',(a['id'],)).fetchone())
  init_v4_schema();init_v4_schema()
  with get_conn() as db:self.assertEqual(tuple(db.execute('SELECT * FROM life_tasks WHERE id=?',(a['id'],)).fetchone()),before);self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__=='__main__':unittest.main()
