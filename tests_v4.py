"""v4 data-integrity and authorization acceptance over disposable records."""
import json,os,tempfile,unittest,sqlite3,subprocess
from pathlib import Path
from datetime import datetime,timezone,date,timedelta
from decimal import Decimal
from unittest.mock import patch
_tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(_tmp.name)/'v4.sqlite'),SESSION_SECRET='v4-fixture-only',APP_USERNAME='admin',APP_PASSWORD='TestAdminPassword!123',COOKIE_SECURE='false',MLO_SCHEDULER_ENABLED='false',MLO_CALENDAR_AUTO_SYNC='false',MLO_SMTP_HOST='')
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user
from app.finance import service,budget
from app.finance.db import init_finance_schema
from app.ui import safe_href
from app import lifeos

class V4Acceptance(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.admin=TestClient(app,follow_redirects=False);cls.admin.__enter__();cls.admin.post('/login',data={'username':'admin','password':'TestAdminPassword!123'})
  cls.clients={}
  for name in ('alice','bob','viewer','editor'):
   create_pending_user(name,name,'TestMemberPassword!123')
   with get_conn() as db:db.execute('UPDATE users SET approved=1 WHERE username=?',(name,));db.commit()
   c=TestClient(app,follow_redirects=False);c.post('/login',data={'username':name,'password':'TestMemberPassword!123'});cls.clients[name]=c
  with get_conn() as db:cls.ids={r['username']:r['id'] for r in db.execute('SELECT id,username FROM users')}
 @classmethod
 def tearDownClass(cls):
  for c in cls.clients.values():c.close()
  cls.admin.__exit__(None,None,None);_tmp.cleanup()
 def last(self,table):
  with get_conn() as db:return db.execute('SELECT MAX(id) FROM '+table).fetchone()[0]
 def post(self,path,data,who='admin',**kw):return (self.admin if who=='admin' else self.clients[who]).post(path,data=data,**kw)
 def test_01_money_validation_and_atomicity(self):
  self.assertEqual(budget.money_decimal('1,234.565'),Decimal('1234.57'))
  service.save_budget_rows('Before',[{'section':'income','name':'Salary','amount':'2500','frequency':'Monthly'}])
  for bad in ('-1','NaN','Infinity','1e9','12,34','1.2.3','999999999999999999999'):
   with self.subTest(bad=bad):
    with self.assertRaises(ValueError):service.save_budget_rows('After',[{'section':'income','name':'Salary','amount':'1','frequency':'Monthly'},{'section':'expenses','name':'Invalid','amount':bad,'frequency':'Weekly'}])
    self.assertEqual(service.budget_data()['name'],'Before');self.assertEqual(service.budget_data()['income']['Salary']['amount'],2500)
 def test_02_revision_conflicts_and_stage_metadata(self):
  revision=service.budget_data()['revision']
  new=service.save_budget_rows('Versioned',[{'section':'expenses','name':'Custom flexible','amount':'12.34','frequency':'Weekly','stage':'flexible'}],revision)
  self.assertEqual(new,revision+1);self.assertEqual(service.budget_data()['stages']['Custom flexible'],'flexible')
  self.assertIn('Custom flexible',service.list_categories())
  with self.assertRaises(service.BudgetConflict):service.save_budget_rows('Stale',[],revision)
  self.assertEqual(service.budget_data()['name'],'Versioned')
  with get_conn() as db:db.execute("INSERT OR REPLACE INTO finance_settings VALUES('budget_stages','[]')");db.commit()
  self.assertEqual(service.budget_data()['stages'],{})
 def test_03_http_budget_failure_retains_values_and_revision(self):
  data={'revision':str(service.budget_data()['revision']),'name':'Unsaved draft','row_key':'a','section__a':'income','name__a':'Salary','amount__a':'NaN','frequency__a':'Monthly'}
  r=self.post('/finance/budget/save',data);self.assertEqual(r.status_code,422);self.assertIn('value="NaN"',r.text);self.assertIn('Unsaved draft',r.text)
  data['amount__a']='100';data['revision']='-1';r=self.post('/finance/budget/save',data,headers={'accept':'application/json'});self.assertEqual(r.status_code,409)
 def test_04_frequency_conversions(self):
  for frequency,factor in budget.ANNUAL_MULTIPLIERS.items():self.assertAlmostEqual(budget.monthlyize(120,frequency),10*factor)
  for rows in ([{'section':'wat','name':'Bad'}],[{'section':'income','name':'Salary','frequency':'Daily'}],[{'section':'income','name':'Duplicate'},{'section':'income','name':'duplicate'}]):
   with self.assertRaises(ValueError):service.save_budget_rows('Bad',rows)
 def test_05_rule_deletion_survives_initialization(self):
  service.delete_rule('Groceries','COSTCO WHOLESALE');init_finance_schema();init_finance_schema()
  self.assertNotIn('COSTCO WHOLESALE',service.load_rules()['Groceries'])
 def test_06_transactions_and_month_validation(self):
  for month in ('','%','2026-13','2026-1','2026-01%'):
   with self.assertRaises(ValueError):service.remove_month(month)
  for values in ({'date':'2026-02-30','description':'x','amount':'10'},{'date':'2026-01-01','description':'','amount':'10'},{'date':'2026-01-01','description':'x','amount':'inf'}):
   with self.assertRaises(ValueError):service.update_transaction(999,values)
 def test_07_worker_timeout_and_upload_limits(self):
  with patch.object(service.subprocess,'run',side_effect=subprocess.TimeoutExpired('parser',45)):
   with self.assertRaisesRegex(ValueError,'too long'):service.import_pdf_bytes('fixture.pdf',b'%PDF-test-v4')
  r=self.admin.post('/finance/import',files={'files':('invalid.pdf',b'not a PDF','application/pdf')});self.assertIn('valid PDF',r.text)
  r=self.admin.post('/finance/import',files=[('files',(f'{i}.pdf',b'%PDF-','application/pdf')) for i in range(11)]);self.assertEqual(r.status_code,413)
 def test_08_note_conflict_private_and_viewer(self):
  self.post('/life/projects',{'name':'V4 note project'},who='alice');pid=self.last('life_projects')
  self.post(f'/life/projects/{pid}/invite',{'username':'viewer','role':'viewer'},who='alice')
  self.post(f'/life/projects/{pid}/invite',{'username':'editor','role':'editor'},who='alice')
  self.post('/life/notes',{'title':'Versioned note','body':'Original','project_id':pid},who='alice');nid=self.last('life_notes')
  with get_conn() as db:version=db.execute('SELECT updated_at FROM life_notes WHERE id=?',(nid,)).fetchone()[0]
  data={'title':'Saved','body':'One\n\nTwo','base_version':version}
  r=self.post(f'/life/notes/{nid}/edit',data,who='editor',headers={'accept':'application/json'});self.assertEqual(r.status_code,200);self.assertNotEqual(r.json()['version'],version)
  self.assertEqual(self.post(f'/life/notes/{nid}/edit',data,who='alice').status_code,409)
  self.assertEqual(self.post(f'/life/notes/{nid}/edit',data,who='viewer').status_code,403)
  self.assertEqual(self.clients['bob'].get(f'/life/notes/{nid}').status_code,404)
  with get_conn() as db:self.assertEqual(db.execute('SELECT body FROM life_notes WHERE id=?',(nid,)).fetchone()[0],'One\n\nTwo')
 def test_09_goal_habit_crud_ownership_and_local_day(self):
  self.post('/life/goals',{'title':'Initial'},who='alice');gid=self.last('life_goals')
  self.assertEqual(self.post(f'/life/goals/{gid}/edit',{'title':'Changed','target_on':'2026-12-15'},who='alice').status_code,303)
  for op,data in [('edit',{'title':'Steal'}),('delete',{}),('complete',{})]:self.assertEqual(self.post(f'/life/goals/{gid}/{op}',data,who='bob').status_code,404)
  self.assertEqual(self.post('/life/habits',{'title':' '},who='alice').status_code,422)
  self.post('/life/habits',{'title':'Daily'},who='alice');hid=self.last('life_habits')
  from app.v37 import save_user_setup
  with get_conn() as db:save_user_setup(db,self.ids['alice'],{'timezone':'Pacific/Kiritimati'});db.commit()
  class Clock(datetime):
   @classmethod
   def now(cls,tz=None):return datetime(2026,10,26,12,30,tzinfo=timezone.utc).astimezone(tz)
  with patch.object(lifeos,'datetime',Clock):
   self.post(f'/life/habits/{hid}/check',{},who='alice')
   with get_conn() as db:self.assertEqual(db.execute('SELECT day FROM life_habit_days WHERE habit_id=?',(hid,)).fetchone()[0],'2026-10-27')
  self.assertEqual(self.post(f'/life/habits/{hid}/edit',{'title':'Renamed'},who='alice').status_code,303)
  self.assertEqual(self.post(f'/life/habits/{hid}/delete',{},who='bob').status_code,404)
  self.assertEqual(self.post(f'/life/habits/{hid}/delete',{},who='alice').status_code,303)
 def test_10_space_partial_update_conflicts_and_roles(self):
  r=self.post('/sections/new',{'name':'Shared notebook'},who='alice');sid=int(r.headers['location'].rsplit('/',1)[1])
  self.post(f'/sections/{sid}/update',{'content':'Preserve this'},who='alice')
  self.post(f'/sections/{sid}/share',{'user_id':self.ids['editor'],'can_edit':'on'},who='alice')
  self.post(f'/sections/{sid}/share',{'user_id':self.ids['viewer'],'can_edit':'off'},who='alice')
  with get_conn() as db:version=db.execute('SELECT updated_at_utc FROM workspace_sections WHERE id=?',(sid,)).fetchone()[0]
  self.assertEqual(self.post(f'/sections/{sid}/update',{'name':'Renamed','settings_form':'1','base_version':version},who='alice').status_code,303)
  self.assertEqual(self.post(f'/sections/{sid}/update',{'content':'Lost','base_version':version},who='editor').status_code,409)
  self.assertEqual(self.post(f'/sections/{sid}/update',{'name':'No'},who='editor').status_code,403)
  self.assertEqual(self.post(f'/sections/{sid}/update',{'content':'No'},who='viewer').status_code,403)
  with get_conn() as db:self.assertEqual(db.execute('SELECT content FROM workspace_sections WHERE id=?',(sid,)).fetchone()[0],'Preserve this')
 def test_11_grocery_quantities_prices_and_date(self):
  sid=int(self.post('/sections/new',{'name':'Groceries','section_type':'grocery'},who='alice').headers['location'].rsplit('/',1)[1])
  self.post(f'/sections/{sid}/groceries/items/add',{'name':'Rice'},who='alice');iid=self.last('grocery_items');eid=self.last('grocery_list_entries')
  for value in ('nan','inf','-1','0'):
   self.assertEqual(self.post(f'/sections/{sid}/groceries/list/{eid}/update',{'quantity':value},who='alice').status_code,422)
  for cost,day in [('nan','2026-10-20'),('1','2026-02-30')]:self.assertEqual(self.post(f'/sections/{sid}/groceries/prices/add',{'grocery_item_id':iid,'quantity':'1','total_cost':cost,'purchased_on':day},who='alice').status_code,422)
  self.assertEqual(self.post(f'/sections/{sid}/groceries/prices/add',{'grocery_item_id':iid,'quantity':'1','total_cost':'2','purchased_on':'2026-10-20'},who='bob').status_code,404)
 def test_12_bill_edits_shift_pending_only(self):
  r=self.post('/expenses/new',{'title':'Bill edit fixture','amount':'20','due_at_local':'2026-11-01T09:00'});eid=int(r.headers['location'].rsplit('/',1)[1])
  with get_conn() as db:
   ts='2026-10-30T09:00:00+00:00';db.execute("DELETE FROM reminders WHERE entity_type='expense' AND entity_id=?",(eid,))
   for sent in (None,'2026-10-20T00:00:00+00:00'):db.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc,sent_at_utc) VALUES('expense',?,?,?, ?,?)",(eid,ts,'Bill','2026-10-20',sent))
   db.commit()
  self.assertEqual(self.post(f'/expenses/{eid}/update',{'title':'Changed bill','amount':'25.555','due_at_local':'2026-11-02T09:00','recurrence':'monthly','recurrence_interval':'1'}).status_code,303)
  with get_conn() as db:
   self.assertEqual(db.execute('SELECT amount FROM expenses WHERE id=?',(eid,)).fetchone()[0],25.56)
   rows=db.execute("SELECT * FROM reminders WHERE entity_type='expense' AND entity_id=? ORDER BY id",(eid,)).fetchall();self.assertEqual(rows[0]['remind_at_utc'],'2026-10-31T09:00:00+00:00');self.assertEqual(rows[1]['remind_at_utc'],ts)
 def test_13_api_compatibility_and_prerequisite_removal(self):
  self.post('/life/projects',{'name':'API compatibility'},who='alice');pid=self.last('life_projects')
  for suffix in ('v4','v37'):
   self.assertEqual(self.clients['alice'].get(f'/api/{suffix}/projects/{pid}/board').status_code,200)
   self.assertEqual(self.clients['bob'].get(f'/api/{suffix}/projects/{pid}/board').status_code,404)
  tids=[]
  for title in ('Prerequisite','Dependent'):
   self.post('/life/tasks',{'title':title,'project_id':pid},who='alice');tids.append(self.last('life_tasks'))
  self.post(f'/life/tasks/{tids[1]}/dependency',{'depends_on':tids[0]},who='alice')
  self.assertEqual(self.post(f'/life/tasks/{tids[1]}/dependency/{tids[0]}/delete',{},who='bob').status_code,404)
  self.assertEqual(self.post(f'/life/tasks/{tids[1]}/dependency/{tids[0]}/delete',{},who='alice').status_code,303)
 def test_14_safe_links_and_errors(self):
  for value in ('javascript:alert(1)','//evil.example','https://[broken','https://example.com:bad','https://user:secret@example.com','/\\evil.example'):
   self.assertEqual(safe_href(value),'')
  self.assertEqual(safe_href('https://example.com/path'),'https://example.com/path')
  response=self.admin.get('/missing-v4-route');self.assertEqual(response.status_code,404);self.assertIn('Page not found',response.text)
  response=self.admin.post('/expenses/new',data={'title':'x','amount':'NaN','due_at_local':'broken'},headers={'accept':'application/json'});self.assertEqual(response.status_code,422)

if __name__=='__main__':unittest.main()
