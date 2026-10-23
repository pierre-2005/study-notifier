"""Study scheduling acceptance: conflicts, deadlines, concurrency, privacy and recovery."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

_tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(_tmp.name)/'planner.db'),SESSION_SECRET='planner-fixture-only',
    APP_USERNAME='admin',APP_PASSWORD='AdminStrongPassword!123',COOKIE_SECURE='false',MLO_SCHEDULER_ENABLED='false',MLO_CALENDAR_AUTO_SYNC='false')
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user
from app import study_planner as planner
from app.v37 import save_user_setup
from app.reminders import sources
from app.agenda import agenda_for
UTC=timezone.utc
AT=datetime(2031,3,3,8,tzinfo=UTC)
class Clock(datetime):
    @classmethod
    def now(cls,tz=None):return AT.astimezone(tz) if tz else AT.replace(tzinfo=None)

class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=TestClient(app,follow_redirects=False);cls.admin.__enter__()
        cls.admin.post('/login',data={'username':'admin','password':'AdminStrongPassword!123'})
        cls.clients={}
        for name in ('alice','bob'):
            create_pending_user(name,name,'MemberPassword!123',name+'@example.com')
            with get_conn() as db:db.execute('UPDATE users SET approved=1,email_verified=1 WHERE username=?',(name,));db.commit()
            client=TestClient(app,follow_redirects=False);client.post('/login',data={'username':name,'password':'MemberPassword!123'});cls.clients[name]=client
        with get_conn() as db:cls.uids={r['username']:r['id'] for r in db.execute('SELECT id,username FROM users')}
    @classmethod
    def tearDownClass(cls):
        for client in cls.clients.values():client.close()
        cls.admin.__exit__(None,None,None);_tmp.cleanup()
    def setUp(self):
        self.clock=patch.object(planner,'datetime',Clock);self.clock.start();self.addCleanup(self.clock.stop)
        with get_conn() as db:
            for table in ('life_study_plans','life_study_blocks','life_local_events','life_study_preferences','life_time_entries','life_task_dependencies','life_course_assessments','life_courses','life_tasks','life_project_members','life_projects','life_calendar_connections'):
                db.execute('DELETE FROM '+table)
            for name in ('alice','bob'):
                save_user_setup(db,self.uids[name],{'selected_modules':['study','tasks','calendar'],'timezone':'UTC','day_time':'21:00','onboarding_completed':True})
            db.commit()
        self.client=self.clients['alice'];self.uid=self.uids['alice'];self.path='/life/study/planner'
        self.prefs={'windows':[{'weekday':i,'start':'09:00','end':'13:00'} for i in range(7)],'block_minutes':50,'break_minutes':10,'daily_minutes':180,'default_minutes':60,'horizon_days':7,'automatic':False}
        self.assertEqual(self.client.put(self.path+'/preferences',json=self.prefs).status_code,200)
    def task(self,title='Study this',minutes=100,due='2031-03-04',owner='alice',**extra):
        response=self.clients[owner].post('/life/tasks',data={'title':title,'area':'Study','estimated_minutes':minutes,'due_on':due,**extra});self.assertEqual(response.status_code,303,response.text)
        with get_conn() as db:return db.execute('SELECT MAX(id) FROM life_tasks').fetchone()[0]
    def event(self,start='2031-03-03T09:30:00+00:00',end='2031-03-03T10:30:00+00:00',owner='alice'):
        with get_conn() as db:
            ident=db.execute('INSERT INTO life_local_events(user_id,title,start_at_utc,end_at_utc,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)',(self.uids[owner],'Existing meeting',start,end,AT.isoformat(),AT.isoformat())).lastrowid;db.commit();return ident
    def preview(self):
        response=self.client.post(self.path+'/preview');self.assertEqual(response.status_code,200,response.text);return response.json()
    def apply(self,plan):return self.client.post(self.path+'/apply',json={'preview_id':plan['preview_id']})
    def test_preview_conflicts_estimates_deadlines_and_logged_time(self):
        tid=self.task();self.event();self.task('Other account',owner='bob')
        with get_conn() as db:
            db.execute('INSERT INTO life_time_entries(owner_id,task_id,minutes,occurred_on,created_at) VALUES(?,?,?,?,?)',(self.uid,tid,20,'2031-03-03',AT.isoformat()));db.commit()
        plan=self.preview();self.assertEqual(plan['minutes'],80);self.assertEqual({b['task_id'] for b in plan['blocks']},{tid})
        for block in plan['blocks']:
            start=datetime.fromisoformat(block['start']);end=datetime.fromisoformat(block['end'])
            self.assertTrue(end<=datetime(2031,3,3,9,20,tzinfo=UTC) or start>=datetime(2031,3,3,10,40,tzinfo=UTC))
            self.assertLessEqual(end,datetime(2031,3,4,21,tzinfo=UTC))
        with get_conn() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM life_local_events').fetchone()[0],1)
        self.assertEqual(self.apply(plan).status_code,200);self.assertEqual(self.apply(plan).json()['created'],0)
        with get_conn() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM life_study_blocks').fetchone()[0],len(plan['blocks']))
    def test_replanning_same_slots_retains_event_ids_and_reminder_history(self):
        tid=self.task();self.apply(self.preview())
        with get_conn() as db:before=[r['id'] for r in db.execute('SELECT id FROM life_local_events ORDER BY id')]
        with get_conn() as db:db.execute('UPDATE life_tasks SET title=? WHERE id=?',('Renamed study task',tid));db.commit()
        result=self.apply(self.preview());self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['created'],0)
        with get_conn() as db:
            self.assertEqual([r['id'] for r in db.execute('SELECT id FROM life_local_events ORDER BY id')],before)
            self.assertTrue(all('Renamed' in r['title'] for r in db.execute('SELECT title FROM life_local_events')))
    def test_apply_and_undo_restore_future_plan_without_touching_manual_events(self):
        self.task();meeting=self.event();old=self.preview();self.assertEqual(self.apply(old).status_code,200)
        with get_conn() as db:before=[tuple(r) for r in db.execute('SELECT id,title,start_at_utc,end_at_utc FROM life_local_events ORDER BY id')]
        self.task('New assignment',minutes=30)
        new=self.preview();self.assertEqual(self.apply(new).status_code,200)
        result=self.client.post(self.path+'/undo',json={'preview_id':new['preview_id']});self.assertEqual(result.status_code,200,result.text)
        with get_conn() as db:self.assertEqual([tuple(r) for r in db.execute('SELECT id,title,start_at_utc,end_at_utc FROM life_local_events ORDER BY id')],before)
        self.assertEqual(self.client.post(self.path+'/undo',json={'preview_id':new['preview_id']}).status_code,409)
    def test_stale_preview_expiry_cross_account_and_csrf(self):
        tid=self.task();plan=self.preview()
        other=self.clients['bob'].post(self.path+'/apply',json={'preview_id':plan['preview_id']});self.assertEqual(other.status_code,404)
        self.assertEqual(self.admin.post(self.path+'/apply',json={'preview_id':plan['preview_id']}).status_code,404)
        self.client.post(f'/life/tasks/{tid}/edit',data={'title':'Changed task','area':'Study','due_on':'2031-03-05'})
        self.assertEqual(self.apply(plan).status_code,409)
        plan=self.preview()
        with get_conn() as db:db.execute('UPDATE life_study_plans SET expires_at=? WHERE id=?',((AT-timedelta(seconds=1)).isoformat(),plan['preview_id']));db.commit()
        self.assertEqual(self.apply(plan).status_code,409)
        self.assertEqual(self.client.post(self.path+'/clear',headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(TestClient(app).post(self.path+'/preview',follow_redirects=False).status_code,303)
    def test_pin_manual_edits_and_clear_do_not_destroy_protected_sessions(self):
        self.task();self.assertEqual(self.apply(self.preview()).status_code,200)
        with get_conn() as db:blocks=[dict(r) for r in db.execute('SELECT * FROM life_study_blocks')]
        one,two=blocks[:2]
        self.assertEqual(self.clients['bob'].put(self.path+f"/blocks/{one['id']}",json={'pinned':True}).status_code,404)
        self.client.put(self.path+f"/blocks/{one['id']}",json={'pinned':True})
        with get_conn() as db:db.execute('UPDATE life_local_events SET title=?,updated_at_utc=? WHERE id=?',('Manual revision',(AT+timedelta(seconds=1)).isoformat(),two['event_id']));db.commit()
        plan=self.preview();self.assertEqual(plan['minutes'],0);self.apply(plan)
        result=self.client.post(self.path+'/clear');self.assertEqual(result.json()['removed'],0)
        with get_conn() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM life_study_blocks').fetchone()[0],2)
    def test_blocks_skip_parents_prerequisites_missing_dates_and_completed_work(self):
        parent=self.task('Parent');child=self.task('Child',minutes=40,parent_id=parent);missing=self.task('Needs a date',due='');blocked=self.task('Blocked',minutes=20)
        with get_conn() as db:db.execute('INSERT INTO life_task_dependencies(task_id,depends_on_id) VALUES(?,?)',(blocked,child));db.commit()
        plan=self.preview();self.assertEqual({b['task_id'] for b in plan['blocks']},{child})
        self.assertEqual({t['task_id'] for t in plan['unplaced']},{missing,blocked})
    def test_precise_imported_deadline_and_daily_limit(self):
        tid=self.task('Precise deadline',minutes=240)
        with get_conn() as db:
            pid=db.execute('INSERT INTO life_projects(owner_id,name,area,created_at,updated_at) VALUES(?,?,?,?,?)',(self.uid,'Course','Study',AT.isoformat(),AT.isoformat())).lastrowid
            cid=db.execute('INSERT INTO life_courses(user_id,project_id,code,name,term,created_at) VALUES(?,?,?,?,?,?)',(self.uid,pid,'ENEL','Course','Spring',AT.isoformat())).lastrowid
            db.execute('INSERT INTO life_course_assessments(user_id,course_id,task_id,kind,title,due_on,due_at_utc,fingerprint) VALUES(?,?,?,?,?,?,?,?)',(self.uid,cid,tid,'exam','Precise','2031-03-04','2031-03-03T11:00:00+00:00','precise'));db.commit()
        plan=self.preview();self.assertEqual(plan['minutes'],100);self.assertEqual(plan['unplaced'][0]['minutes'],140)
        self.assertTrue(all(datetime.fromisoformat(b['end'])<=datetime(2031,3,3,11,tzinfo=UTC) for b in plan['blocks']))
    def test_automatic_is_explicit_idempotent_and_skips_unapproved_accounts(self):
        self.task();self.assertEqual(planner.process_study_plans(AT),0)
        self.client.put(self.path+'/preferences',json={**self.prefs,'automatic':True})
        self.assertGreater(planner.process_study_plans(AT),0)
        with get_conn() as db:before=[tuple(r) for r in db.execute('SELECT * FROM life_local_events')]
        self.assertEqual(planner.process_study_plans(AT+timedelta(minutes=20)),0)
        with get_conn() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM life_local_events')],before)
            db.execute('UPDATE users SET approved=0 WHERE id=?',(self.uid,));db.commit()
        self.assertEqual(planner.process_study_plans(AT+timedelta(days=1)),0)
        with get_conn() as db:db.execute('UPDATE users SET approved=1 WHERE id=?',(self.uid,));db.commit()
    def test_stale_or_failed_calendar_blocks_planning_until_refresh(self):
        self.task()
        with get_conn() as db:db.execute("INSERT INTO life_calendar_connections(user_id,provider,label,secret_blob,created_at,last_error) VALUES(?,'google','My account','fake',?,'Refresh failed')",(self.uid,AT.isoformat()));db.commit()
        self.assertEqual(self.client.post(self.path+'/preview').status_code,409)
        with get_conn() as db:db.execute('UPDATE life_calendar_connections SET last_error=NULL,last_synced_at=?',(AT.isoformat(),));db.commit()
        self.assertTrue(self.preview()['blocks'])
    def test_external_busy_free_all_day_and_unknown_end(self):
        self.task(minutes=180)
        with get_conn() as db:
            cid=db.execute("INSERT INTO life_calendar_connections(user_id,provider,label,secret_blob,created_at,last_synced_at) VALUES(?,'microsoft','My account','fake',?,?)",(self.uid,AT.isoformat(),AT.isoformat())).lastrowid
            db.execute('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at,ends_at,is_all_day,is_busy) VALUES(?,?,?,?,?,?,?,?)',(cid,'busy','Busy','2031-03-03','2031-03-03T09:00:00','2031-03-03T12:00:00',0,1))
            db.execute('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at,ends_at,is_all_day,is_busy) VALUES(?,?,?,?,?,?,?,?)',(cid,'free','Free','2031-03-04','2031-03-04T09:00:00Z','2031-03-04T13:00:00Z',0,0))
            db.commit()
        plan=self.preview();self.assertEqual(plan['minutes'],180)
        self.assertTrue(all(b['start']>='2031-03-03T12:10' for b in plan['blocks']))
        with get_conn() as db:db.execute('UPDATE life_external_events SET ends_at=NULL WHERE uid=?',('busy',));db.commit()
        plan=self.preview();self.assertTrue(plan['warnings']);self.assertTrue(all(b['start'][:10]>'2031-03-03' for b in plan['blocks']))
    def test_validation_dst_and_completed_session_reminders(self):
        self.assertEqual(self.client.put(self.path+'/preferences',json={**self.prefs,'windows':[{'weekday':0,'start':'12:00','end':'11:00'}]}).status_code,422)
        self.assertEqual(self.client.put(self.path+'/preferences',json={**self.prefs,'block_minutes':True}).status_code,422)
        self.assertIsNone(planner.valid_local(datetime(2031,3,9).date(),'02:30',ZoneInfo('America/New_York')))
        self.assertIsNone(planner.valid_local(datetime(2031,11,2).date(),'01:30',ZoneInfo('America/New_York')))
        tid=self.task();self.apply(self.preview())
        with get_conn() as db:
            self.assertTrue(list(sources(db,self.uid,['calendar'])))
            db.execute("UPDATE life_tasks SET status='done' WHERE id=?",(tid,));db.commit()
            self.assertEqual(list(sources(db,self.uid,['calendar'])),[])
            self.assertTrue(agenda_for(db,self.uid,AT.date(),ZoneInfo('UTC')))
    def test_planner_page_and_owned_courses_render(self):
        self.task()
        for path in (self.path,'/life/study','/life/work','/life','/settings'):
            response=self.client.get(path);self.assertEqual(response.status_code,200,(path,response.text[:300]))
        self.apply(self.preview());self.assertIn('Upcoming sessions',self.client.get(self.path).text)

if __name__=='__main__':unittest.main(verbosity=2)
