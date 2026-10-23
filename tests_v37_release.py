"""Full API integration, delivery isolation, recovery, and course-import acceptance."""
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import zipfile

_tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(_tmp.name)/'release.db'),SESSION_SECRET='release-test-session-not-production',
    APP_USERNAME='admin',APP_PASSWORD='AdminStrongPassword!123',COOKIE_SECURE='false',MLO_PUBLIC_URL='https://organizer.overvault.ca',
    MLO_SCHEDULER_ENABLED='false',MLO_CALENDAR_AUTO_SYNC='false',MLO_SMTP_HOST='mock',MLO_SMTP_FROM='noreply@example.com')
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_conn
from app.auth import create_pending_user,hash_password,verify_password
from app import account_security as security
from app.v37 import save_user_setup
from app.reminders import process_personal_reminders
from app.task_service import task_forest

class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sent=[]
        cls.mail=patch.object(security,'_send_email',side_effect=lambda to,subject,body:cls.sent.append((to,subject,body)) or True)
        cls.mail.start()
        cls.admin=TestClient(app,follow_redirects=False);cls.admin.__enter__()
        cls.admin.post('/login',data={'username':'admin','password':'AdminStrongPassword!123'})
        cls.clients={}
        for name in ('alice','bob','viewer','editor'):
            create_pending_user(name,name,'TestMemberPassword!123',name+'@example.com')
            with get_conn() as db:
                db.execute('UPDATE users SET approved=1,email_verified=1 WHERE username=?',(name,));db.commit()
            client=TestClient(app,follow_redirects=False)
            client.post('/login',data={'username':name,'password':'TestMemberPassword!123'})
            cls.clients[name]=client
        with get_conn() as db:cls.ids={r['username']:r['id'] for r in db.execute('SELECT id,username FROM users')}
    @classmethod
    def tearDownClass(cls):
        for client in cls.clients.values():client.close()
        cls.admin.__exit__(None,None,None);cls.mail.stop();_tmp.cleanup()
    def project(self,owner='alice'):
        self.clients[owner].post('/life/projects',data={'name':'Acceptance '+self._testMethodName,'template':'blank'})
        with get_conn() as db:return db.execute('SELECT MAX(id) FROM life_projects').fetchone()[0]
    def task(self,pid=None,owner='alice',**fields):
        fields={'title':'Acceptance task','project_id':str(pid) if pid else '',**fields}
        response=self.clients[owner].post('/life/tasks',data=fields)
        self.assertEqual(response.status_code,303,response.text)
        with get_conn() as db:return db.execute('SELECT MAX(id) FROM life_tasks').fetchone()[0]
    def prefs(self,name,modules,rules,**extra):
        with get_conn() as db:
            save_user_setup(db,self.ids[name],{'selected_modules':modules,'reminders':rules,
                'timezone':'America/Edmonton','quiet_start':'00:00','quiet_end':'00:00','onboarding_completed':True,**extra});db.commit()
    def test_all_supported_module_sources_route_only_to_owner_devices(self):
        uid=self.ids['admin'];at=datetime(2026,12,10,16,0,tzinfo=timezone.utc);stamp=at.isoformat()
        with get_conn() as db:
            save_user_setup(db,uid,{'selected_modules':['tasks','projects','calendar','study','work','money','notes','focus'],
                'reminders':{k:[0] for k in ('task','project','event','study','work','bill','notes','focus')},
                'timezone':'America/Edmonton','quiet_start':'00:00','quiet_end':'00:00','onboarding_completed':True})
            device=db.execute('INSERT INTO life_devices(owner_id,name,topic,enabled,created_at) VALUES(?,?,?,1,?)',(uid,'All modules','admin-private-acceptance',stamp)).lastrowid
            project=db.execute('INSERT INTO life_projects(owner_id,name,due_on,created_at,updated_at) VALUES(?,?,?,?,?)',(uid,'Due project','2026-12-10',stamp,stamp)).lastrowid
            for title,area in (('Personal deadline','Personal'),('Work deadline','Work')):
                db.execute('INSERT INTO life_tasks(owner_id,title,area,due_on,created_at,updated_at) VALUES(?,?,?,?,?,?)',(uid,title,area,'2026-12-10',stamp,stamp))
            course=db.execute('INSERT INTO courses(name,created_at_utc) VALUES(?,?)',('Legacy course',stamp)).lastrowid
            for kind in ('assignment','exam','lab'):
                db.execute('INSERT INTO items(course_id,type,title,due_at_utc,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)',(course,kind,kind+' due',stamp,stamp,stamp))
            db.execute('INSERT INTO expenses(title,amount,due_at_utc,created_at_utc,updated_at_utc) VALUES(?,1,?,?,?)',('Bill due',stamp,stamp,stamp))
            db.execute('INSERT INTO jobs(company,role,followup_at_utc,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?)',('Demo company','Engineer',stamp,stamp,stamp))
            db.execute('INSERT INTO life_local_events(user_id,title,start_at_utc,end_at_utc,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)',(uid,'Local event',stamp,(at+timedelta(hours=1)).isoformat(),stamp,stamp))
            connection=db.execute("INSERT INTO life_calendar_connections(user_id,provider,label,secret_blob,created_at) VALUES(?,'google','Test account','mock',?)",(uid,stamp)).lastrowid
            db.execute('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at) VALUES(?,?,?,?,?)',(connection,'owned-event','External event','2026-12-10',stamp))
            note=db.execute('INSERT INTO life_notes(owner_id,title,created_at,updated_at) VALUES(?,?,?,?)',(uid,'Review note',stamp,stamp)).lastrowid
            db.execute('INSERT INTO life_note_reminders(user_id,note_id,remind_at_utc) VALUES(?,?,?)',(uid,note,stamp))
            db.execute("INSERT INTO timers(user_id,label,duration_seconds,remaining_seconds,status,started_at_utc,created_at_utc,updated_at_utc,kind) VALUES(?,?,1500,1500,'running',?,?,?,'focus')",(uid,'Focus deadline',(at-timedelta(minutes=25)).isoformat(),stamp,stamp))
            db.commit()
        deliveries=[]
        self.assertEqual(process_personal_reminders(at,lambda *args:deliveries.append(args) or True),12)
        self.assertEqual({r[0] for r in deliveries},{'admin-private-acceptance'})
        self.assertEqual({r[1] for r in deliveries},{'task','project','event','assignment','exam','lab','work','bill','notes','focus'})
        self.assertEqual(process_personal_reminders(at+timedelta(minutes=1),lambda *args:True),0)
        with get_conn() as db:db.execute('UPDATE life_devices SET enabled=0 WHERE id=?',(device,));db.commit()
    def test_inspector_access_validation_and_conflicts(self):
        pid=self.project();tid=self.task(pid,title='Inspect this task');path=f'/api/v37/tasks/{tid}'
        self.assertEqual(self.clients['bob'].get(path).status_code,404)
        self.assertEqual(self.admin.get(path).status_code,404)
        data=self.clients['alice'].get(path).json();self.assertTrue(data['can_edit'])
        body={k:data['task'][k] for k in ('title','description','status','priority','due_on','recurrence','estimated_minutes')}
        body.update(title='Updated in context',expected_updated_at=data['task']['updated_at'])
        result=self.clients['alice'].patch(path,json=body);self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.clients['alice'].patch(path,json=body).status_code,409)
        self.clients['alice'].post(f'/life/projects/{pid}/invite',data={'username':'viewer','role':'viewer'})
        self.assertFalse(self.clients['viewer'].get(path).json()['can_edit'])
        self.assertEqual(self.clients['viewer'].patch(path,json=body).status_code,403)
        self.assertNotIn('Save changes',self.clients['viewer'].get(f'/life/tasks/{tid}').text)
        self.assertEqual(self.clients['alice'].patch(path,json={**body,'priority':'impossible'}).status_code,422)
    def test_note_review_dates_are_personal(self):
        self.clients['alice'].post('/life/notes',data={'title':'Private reminder note'})
        with get_conn() as db:nid=db.execute('SELECT MAX(id) FROM life_notes').fetchone()[0]
        path=f'/life/notes/{nid}/reminder'
        self.assertEqual(self.clients['bob'].post(path,data={'review_at':'2026-11-15T12:00'}).status_code,404)
        self.assertEqual(self.clients['alice'].post(path,data={'review_at':'2026-11-15T12:00'}).status_code,303)
        self.assertIn('2026-11-15T12:00',self.clients['alice'].get(f'/life/notes/{nid}').text)
        self.assertEqual(self.clients['bob'].post(path+'/delete').status_code,404)
        self.assertEqual(self.clients['alice'].post(path+'/delete').status_code,303)
    def test_layout_preferences_preserve_existing_custom_names(self):
        self.prefs('editor',['tasks','projects'],{'task':[60]})
        uid=self.ids['editor']
        with get_conn() as db:
            db.execute('UPDATE life_layouts SET nav_labels=? WHERE user_id=?',(json.dumps({'life-tasks':'Action list'}),uid));db.commit()
        self.prefs('editor',['tasks','study'],{'task':[60],'study':[1440]},density='compact',preferred_view='table')
        layout=self.clients['editor'].get('/life/layout').json()
        self.assertEqual(layout['nav_labels']['life-tasks'],'Action list')
        self.assertIn('life-projects',layout['nav_hidden']);self.assertNotIn('life-studio',layout['nav_hidden'])
        self.assertIn('data-density="compact"',self.clients['editor'].get('/life').text)
    def test_member_api_and_project_acl(self):
        pid=self.project();tid=self.task(pid)
        self.assertEqual(self.clients['alice'].get(f'/api/v37/projects/{pid}/board').status_code,200)
        for client in (self.clients['bob'],self.admin):self.assertEqual(client.get(f'/api/v37/projects/{pid}/board').status_code,404)
        for user,role in (('viewer','viewer'),('editor','editor')):
            self.clients['alice'].post(f'/life/projects/{pid}/invite',data={'username':user,'role':role})
        self.assertEqual(self.clients['viewer'].post(f'/api/v37/projects/{pid}/move',json={'task_id':tid,'status':'doing'}).status_code,403)
        self.assertEqual(self.clients['editor'].post(f'/api/v37/projects/{pid}/move',json={'task_id':tid,'status':'doing'}).status_code,200)
        anon=TestClient(app)
        self.assertEqual(anon.get(f'/api/v37/projects/{pid}/board').status_code,401)
        self.assertEqual(self.clients['alice'].post(f'/api/v37/projects/{pid}/move',json={'task_id':tid,'status':'todo'},headers={'Origin':'https://evil.example'}).status_code,403)
    def test_nesting_child_status_cycle_and_stale_edit(self):
        pid=self.project();parent=self.task(pid,title='Parent');child=self.task(pid,title='Child')
        api=f'/api/v37/projects/{pid}'
        self.assertEqual(self.clients['alice'].post(api+'/nest',json={'task_id':child,'parent_id':parent}).status_code,200)
        self.assertEqual(self.clients['alice'].post(api+'/nest',json={'task_id':parent,'parent_id':child}).status_code,409)
        r=self.clients['alice'].post(api+'/move',json={'task_id':child,'status':'done'})
        self.assertEqual(r.status_code,200,r.text)
        node=r.json()['board']['columns']['todo'][0];self.assertEqual(node['subtask_done'],1)
        self.assertEqual(self.clients['alice'].post(api+'/move',json={'task_id':parent,'status':'doing','expected_updated_at':'stale'}).status_code,409)
        for view in ('board','list','table','calendar'):
            page=self.clients['alice'].get(f'/life/projects/{pid}?view={view}')
            self.assertEqual(page.status_code,200,page.text[:200])
            self.assertIn('Child',page.text)
    def test_dependencies_and_recurring_all_edit_paths(self):
        pid=self.project();prereq=self.task(pid,title='Prerequisite');tid=self.task(pid,title='Repeat task',recurrence='weekly',due_on='2026-11-05')
        self.clients['alice'].post(f'/life/tasks/{tid}/dependency',data={'depends_on':prereq})
        for path,data in ((f'/api/v37/projects/{pid}/move',{'task_id':tid,'status':'done'}),(f'/life/tasks/{tid}/edit',{'title':'Repeat task','status':'done','recurrence':'weekly','due_on':'2026-11-05'})):
            r=self.clients['alice'].post(path,**({'json':data} if path.startswith('/api') else {'data':data}))
            self.assertEqual(r.status_code,409,r.text)
        self.clients['alice'].post(f'/life/tasks/{prereq}/status',data={'status':'done'})
        for status in ('done','todo','done'):
            self.assertEqual(self.clients['alice'].post(f'/api/v37/projects/{pid}/move',json={'task_id':tid,'status':status}).status_code,200)
        with get_conn() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM life_task_successors WHERE source_id=?',(tid,)).fetchone()[0],1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM life_tasks WHERE project_id=? AND title='Repeat task'",(pid,)).fetchone()[0],2)
    def test_deep_subtree_cannot_exceed_limit(self):
        pid=self.project();parent=None
        for i in range(9):parent=self.task(pid,title=f'Depth {i}',parent_id=str(parent or ''))
        r=self.clients['alice'].post('/life/tasks',data={'title':'Too deep','project_id':pid,'parent_id':parent})
        self.assertEqual(r.status_code,422)
        root=self.task(pid,title='Independent root');child=self.task(pid,title='Independent child',parent_id=root)
        self.assertEqual(self.clients['alice'].post(f'/api/v37/projects/{pid}/nest',json={'task_id':root,'parent_id':parent}).status_code,422)
    def test_corrupt_legacy_cycle_does_not_hide_or_recurse(self):
        rows=[{'id':1,'parent_id':2,'status':'todo'},{'id':2,'parent_id':1,'status':'doing'}]
        tree=task_forest(rows);self.assertEqual({n['id'] for n in tree},{1,2});json.dumps(tree)
    def test_reminder_preferences_isolated_and_muted_persist(self):
        self.prefs('alice',['tasks'],{'task':[]})
        response=self.clients['alice'].get('/api/v37/me/setup')
        self.assertEqual(response.json()['reminders']['task'],[])
        self.assertEqual(self.clients['bob'].get('/api/v37/me/setup').json()['onboarding_completed'],False)
        self.assertEqual(self.clients['alice'].put('/api/v37/me/reminders/task',json=[True]).status_code,422)
        self.assertEqual(self.clients['alice'].put('/api/v37/me/setup',json={'selected_modules':['unknown']}).status_code,422)
    def test_signup_atomic_verification_approval_and_error_retention(self):
        setup={'selected_modules':['tasks','study'],'reminders':{'task':[60],'study':[1440]},'timezone':'America/Edmonton','theme':'light','palette':'ocean','onboarding_completed':True}
        fields={'username':'new_signup','display_name':'New Member','email':'newsignup@example.com','password':'NewUserPassword!123','password_confirm':'wrong','v37_setup':json.dumps(setup)}
        visitor=TestClient(app,follow_redirects=False)
        bad=visitor.post('/signup',data=fields)
        self.assertEqual(bad.status_code,422);self.assertIn('new_signup',bad.text);self.assertNotIn('NewUserPassword!123',bad.text)
        fields['password_confirm']=fields['password'];response=visitor.post('/signup',data=fields)
        self.assertEqual(response.status_code,201,response.text)
        with get_conn() as db:
            user=db.execute("SELECT * FROM users WHERE username='new_signup'").fetchone();uid=user['id']
            self.assertEqual(user['requires_email_verification'],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM v37_reminder_rules WHERE user_id=?',(uid,)).fetchone()[0],2)
        token=re.search(r'/verify-email/([\w-]+)',self.sent[-1][2])[1]
        self.admin.post(f'/admin/users/{uid}/approval',data={'approved':'1'})
        denied=visitor.post('/login',data={'username':'new_signup','password':fields['password']});self.assertEqual(denied.status_code,200);self.assertIn('Verify your email',denied.text)
        self.assertEqual(visitor.post('/verify-email/'+token).status_code,200)
        self.assertEqual(visitor.post('/login',data={'username':'new_signup','password':fields['password']}).status_code,303)
        before=len(self.sent);visitor.post('/signup',data=fields);self.assertEqual(len(self.sent),before)
        self.assertEqual(visitor.get('/api/v37/me/setup').json()['reminders']['task'],[60])
        visitor.close()
    def test_recovery_attempts_expiry_encryption_and_password_change(self):
        from app import auth_delivery as delivery
        from app.auth import update_user_password
        create_pending_user('limits','Limits','LimitsPassword!123','limits@example.com')
        with get_conn() as db:
            uid=db.execute("SELECT id FROM users WHERE username='limits'").fetchone()[0]
            db.execute('UPDATE users SET approved=1,email_verified=1 WHERE id=?',(uid,));db.commit()
        at=datetime(2026,12,1,12,tzinfo=timezone.utc)
        with patch.object(delivery,'now',return_value=at):
            self.assertTrue(delivery.issue_reset_code(uid,'limits@example.com'))
            with get_conn() as db:
                row=db.execute('SELECT * FROM auth_mail_outbox WHERE user_id=?',(uid,)).fetchone()
                self.assertNotIn('limits@example.com',row['payload'])
                import json
                body=json.loads(delivery._cipher().decrypt(row['payload'].encode()))['body']
                code=re.search(r'\b\d{6}\b',body)[0]
                self.assertNotIn(code,db.execute('SELECT code_hash FROM auth_reset_codes WHERE user_id=?',(uid,)).fetchone()[0])
            wrong='111111' if code!='111111' else '222222'
            for _ in range(5):
                with get_conn() as db:
                    db.execute('BEGIN IMMEDIATE');self.assertFalse(delivery.consume_reset_code(db,'limits@example.com',wrong,'ChangedPassword!123'));db.commit()
            with get_conn() as db:
                db.execute('BEGIN IMMEDIATE');self.assertFalse(delivery.consume_reset_code(db,'limits@example.com',code,'ChangedPassword!123'));db.commit()
        with patch.object(delivery,'now',return_value=at+timedelta(minutes=6)):
            self.assertTrue(delivery.issue_reset_code(uid,'limits@example.com'))
            with get_conn() as db:
                payload=db.execute('SELECT payload FROM auth_mail_outbox WHERE user_id=? ORDER BY id DESC',(uid,)).fetchone()[0]
                code=re.search(r'\b\d{6}\b',json.loads(delivery._cipher().decrypt(payload.encode()))['body'])[0]
        with patch.object(delivery,'now',return_value=at+timedelta(minutes=17)):
            with get_conn() as db:
                db.execute('BEGIN IMMEDIATE');self.assertFalse(delivery.consume_reset_code(db,'limits@example.com',code,'ChangedPassword!123'));db.commit()
        update_user_password(uid,'OwnerChangedPassword!123',actor_id=uid)
        with get_conn() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_reset_codes WHERE user_id=? AND used_at IS NULL',(uid,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM auth_mail_outbox WHERE user_id=?',(uid,)).fetchone()[0],0)

    def test_reset_codes_replay_attempt_limit_and_admin_no_impersonation(self):
        user=self.ids['bob'];client=self.clients['bob']
        with get_conn() as db:before=db.execute('SELECT password_hash FROM users WHERE id=?',(user,)).fetchone()[0]
        self.assertEqual(self.admin.post(f'/admin/users/{user}/email',data={'email':'attacker@example.com','admin_password':'AdminStrongPassword!123'}).status_code,403)
        self.assertEqual(self.admin.post(f'/admin/users/{user}/reset-password',data={'admin_password':'AdminStrongPassword!123','new_password':'AttackerPassword!123'}).status_code,303)
        with get_conn() as db:self.assertEqual(db.execute('SELECT password_hash FROM users WHERE id=?',(user,)).fetchone()[0],before)
        code=re.search(r'\b\d{6}\b',self.sent[-1][2])[0]
        visitor=TestClient(app,follow_redirects=False)
        data={'email':'bob@example.com','code':code,'password':'RecoveredPassword!123','confirm':'RecoveredPassword!123'}
        self.assertEqual(visitor.post('/reset-code',data=data).status_code,303)
        self.assertEqual(client.get('/life').status_code,303)
        self.assertEqual(visitor.post('/reset-code',data=data).status_code,200)
        self.assertIn('invalid',visitor.post('/reset-code',data=data).text)
        visitor.close()
    def test_personal_delivery_retry_quiet_timezone_disabled_account(self):
        self.prefs('alice',['tasks'],{'task':[60,0]},quiet_start='22:00',quiet_end='07:00')
        tid=self.task(due_on='2026-11-02')
        with get_conn() as db:
            for name in ('alice','bob'):
                db.execute('INSERT INTO life_devices(owner_id,name,topic,enabled,created_at) VALUES(?,?,?,1,?)',(self.ids[name],name,name+'-private-topic','2026-10-23'))
            db.commit()
        deliveries=[]
        at=datetime(2026,11,2,15,0,tzinfo=timezone.utc) # 08:00 after DST ends, 1h before 09:00.
        self.assertEqual(process_personal_reminders(at,lambda *args:False),0)
        self.assertEqual(process_personal_reminders(at+timedelta(minutes=3),lambda *args:deliveries.append(args) or True),1)
        self.assertEqual(deliveries[0][0],'alice-private-topic')
        self.assertEqual(process_personal_reminders(at+timedelta(minutes=4),lambda *args:True),0)
        self.assertEqual(process_personal_reminders(at.replace(hour=12),lambda *args:True),0)
        with get_conn() as db:db.execute('UPDATE users SET active=0 WHERE id=?',(self.ids['alice'],));db.commit()
        self.assertEqual(process_personal_reminders(at+timedelta(hours=1),lambda *args:True),0)
        with get_conn() as db:db.execute('UPDATE users SET active=1 WHERE id=?',(self.ids['alice'],));db.commit()
    def test_course_import_review_commit_dedupe_and_privacy(self):
        outline=b'ENEL 471 Communications\nAssignment 1 | October 30, 2026 23:59 | 10%\nMidterm | November 5, 2026 | 30%\nFinal exam TBA | 60%\nLab 1 | 11/12/2026\n'
        alice=self.clients['alice'];r=alice.post('/life/study/import',files={'file':('outline.txt',outline,'text/plain')},data={'term_year':'2026'})
        self.assertEqual(r.status_code,303,r.text);path=r.headers['location'];iid=int(path.rsplit('/',1)[1])
        self.assertIn('Ambiguous numeric date',alice.get(path).text)
        for client in (self.clients['bob'],self.admin):self.assertEqual(client.get(path).status_code,404)
        body={'course_name':'Communications','course_code':'ENEL 471','term':'Fall 2026','rows':[
            {'title':'Assignment 1','kind':'assignment','due_on':'2026-10-30','time':'23:59','weight':10.0,'source_index':0},
            {'title':'Final exam','kind':'exam','due_on':None,'time':None,'weight':60.0,'source_index':2}]}
        result=alice.post(path+'/commit',json=body);self.assertEqual(result.status_code,200,result.text)
        course=result.json()['course_id'];self.assertEqual(result.json()['created'],2)
        self.assertEqual(alice.post(path+'/commit',json=body).json()['created'],0)
        self.assertEqual(self.clients['bob'].get(f'/life/study/courses/{course}').status_code,404)
        with get_conn() as db:
            rows=db.execute('SELECT t.* FROM life_tasks t JOIN life_course_assessments a ON a.task_id=t.id WHERE a.course_id=?',(course,)).fetchall()
            self.assertEqual(len(rows),2);self.assertTrue(any(r['due_on'] is None for r in rows));self.assertTrue(all(r['owner_id']==self.ids['alice'] for r in rows))
        duplicate=alice.post('/life/study/import',files={'file':('outline.txt',outline,'text/plain')},data={'term_year':'2026'})
        self.assertEqual(duplicate.headers['location'],path)
        self.assertEqual(self.clients['bob'].post(path+'/delete').status_code,404)
    def test_invalid_upload_and_xml_entity(self):
        alice=self.clients['alice'];r=alice.post('/life/study/import',files={'file':('wrong.pdf',b'not a PDF','application/pdf')},data={'term_year':'2026'})
        self.assertIn('not a valid PDF',r.text)
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as archive:
            archive.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')
        r=alice.post('/life/study/import',files={'file':('unsafe.docx',payload.getvalue(),'application/octet-stream')},data={'term_year':'2026'})
        self.assertNotIn('root:x:',r.text)
        self.assertEqual(r.status_code,200)

if __name__=='__main__':unittest.main(verbosity=2)
