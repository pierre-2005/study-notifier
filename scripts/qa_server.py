"""Disposable, loopback-only browser fixture. Never reads the installation database."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',required=True)
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--map-size',type=int,default=0)
    args=parser.parse_args()
    root=Path(args.data_dir).resolve()
    root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):raise SystemExit('Browser fixtures require an empty data directory.')
    os.environ.update(STUDY_NOTIFIER_DB=str(root/'fixture.sqlite'),SESSION_SECRET='browser-fixture-secret-only',
        APP_USERNAME='demo',APP_PASSWORD='MloPreviewOnly!234',COOKIE_SECURE='false',
        MLO_PUBLIC_URL='https://organizer.example',MLO_SCHEDULER_ENABLED='false',
        MLO_CALENDAR_AUTO_SYNC='false',MLO_OUTLINE_AI_ENABLED='false',MLO_SMTP_HOST='',
        MLO_ATTACHMENT_DIR=str(root/'uploads'))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_conn
    from app.v37 import save_user_setup
    from datetime import date,timedelta
    with TestClient(app,follow_redirects=False) as client:
        assert client.post('/login',data={'username':'demo','password':'MloPreviewOnly!234'}).status_code==303
        with get_conn() as db:
            uid=db.execute("SELECT id FROM users WHERE username='demo'").fetchone()[0]
            db.execute("UPDATE users SET display_name='Alex' WHERE id=?",(uid,))
            save_user_setup(db,uid,{'selected_modules':['tasks','projects','calendar','study','work','money','notes','focus'],
                'theme':'light','palette':'ocean','reminders':{'task':[1440],'study':[1440],'event':[30]},'onboarding_completed':True})
            db.commit()
        response=client.post('/life/projects',data={'name':'Semester workspace','area':'Study','template':'blank',
            'description':'Coursework, design projects and upcoming deadlines.'})
        pid=int(response.headers['location'].rsplit('/',1)[1]);ids=[]
        for index,(title,status,priority) in enumerate([
            ('Finish the circuit design report','todo','high'),('Review lecture notes','doing','normal'),
            ('Wait for project feedback','blocked','normal'),('Set up the workspace','done','normal')]):
            response=client.post('/life/tasks',data={'title':title,'project_id':pid,'priority':priority,
                'due_on':(date.today()+timedelta(days=index)).isoformat()})
            with get_conn() as db:tid=db.execute('SELECT MAX(id) FROM life_tasks').fetchone()[0]
            ids.append(tid);client.post(f'/life/tasks/{tid}/status',data={'status':status})
            if index==0:
                for text in ('Check calculations','Create the final diagrams'):
                    client.post('/life/tasks',data={'title':text,'project_id':pid,'parent_id':tid})
        client.post('/life/notes',data={'title':'Ideas for the next design review','body':'Questions to explore in the next meeting.'})
        fixture={'project_id':pid,'task_ids':ids}
        def post(path,**data):
            response=client.post(path,data=data)
            assert response.status_code==303,(path,response.status_code,response.text[:300])
            return response
        post('/courses/new',name='Electrical systems',term='Fall 2026',color='#3975b7')
        with get_conn() as db:fixture['course_id']=db.execute('SELECT MAX(id) FROM courses').fetchone()[0]
        post('/items/new',course_id=fixture['course_id'],type='exam',title='Systems midterm',due_at_local='2026-11-20T10:00',weight='25')
        post('/jobs/new',company='Northwind Engineering',role='Design intern',link='https://example.com/careers',status='interview',followup_at_local='2026-11-15T09:00')
        post('/expenses/new',title='Apartment rent',category='Housing',amount='1450',due_at_local='2026-11-01T09:00',recurrence='monthly')
        post('/classes/new',title='Systems lecture',weekday='1',start_time_local='10:00',duration_minutes='50',location='Engineering 204')
        post('/events/new',title='Project review',start_at_local='2026-11-12T14:00',end_at_local='2026-11-12T15:00')
        post('/life/goals',title='Complete the semester project',target_on='2026-12-15')
        post('/life/habits',title='Review notes for 15 minutes')
        for key,table in [('item_id','items'),('job_id','jobs'),('expense_id','expenses'),('class_id','class_meetings'),('event_id','events'),('note_id','life_notes')]:
            with get_conn() as db:fixture[key]=db.execute('SELECT MAX(id) FROM '+table).fetchone()[0]
        for key,kind,title in [('space_id','blank','Design notebook'),('grocery_id','grocery','Home groceries')]:
            fixture[key]=int(post('/sections/new',name=title,section_type=kind).headers['location'].rsplit('/',1)[1])
        sid=fixture['space_id'];gid=fixture['grocery_id']
        post(f'/sections/{sid}/update',content='Questions, decisions and reference material for the next design review.')
        post(f'/sections/{sid}/checklist/add',content='Review component availability')
        post(f'/sections/{gid}/groceries/items/add',name='Oats',unit='kg',aisle='Breakfast')
        post(f'/sections/{gid}/groceries/items/add',name='Milk',unit='L',aisle='Dairy')
        post(f'/sections/{gid}/groceries/recipes/add',name='Overnight oats',notes='Prepare for the next morning.')
        with get_conn() as db:
            iid=db.execute('SELECT id FROM grocery_items WHERE name=?',('Oats',)).fetchone()[0]
            rid=db.execute('SELECT MAX(id) FROM grocery_recipes').fetchone()[0]
        post(f'/sections/{gid}/groceries/recipes/{rid}/ingredient',grocery_item_id=iid,quantity='0.1',unit='kg')
        post(f'/sections/{gid}/groceries/prices/add',grocery_item_id=iid,total_cost='4.50',quantity='1',store='Local market',purchased_on='2026-10-20')
        from app.finance import service
        from app.finance.parser import Transaction
        service.save_budget_rows('Monthly plan',[
            {'section':'income','name':'Employment income','amount':'2400','frequency':'Biweekly'},
            {'section':'expenses','name':'Mortgage or rent','amount':'1450','frequency':'Monthly','stage':'essentials'},
            {'section':'expenses','name':'Groceries','amount':'110','frequency':'Weekly','stage':'essentials'},
            {'section':'expenses','name':'Streaming media subscriptions','amount':'22.50','frequency':'Monthly','stage':'flexible'},
            {'section':'savings','name':'Emergency fund','amount':'300','frequency':'Monthly'}])
        with get_conn() as db:
            for index in range(72):
                service.insert_transaction(db,Transaction(date=f'2026-{9+index%2:02d}-{1+index%28:02d}',description=['Weekly groceries','Coffee with friends','Transit pass','Bookshop'][index%4]+f' {index+1}',amount=round(12.45+index*1.63,2),category=['Groceries','Cafés and coffee shops','Public transit','Hobbies and recreation'][index%4],bank='BMO' if index%2 else 'Scotiabank',source_file='demonstration.pdf'))
            db.commit()
        from app.auth import create_pending_user
        for username,label in [('read_only','Read-only collaborator'),('editor_user','Editor collaborator')]:
            create_pending_user(username,label,'FixtureMemberOnly!234')
            with get_conn() as db:db.execute('UPDATE users SET approved=1 WHERE username=?',(username,));db.commit()
        post(f'/life/projects/{pid}/invite',username='read_only',role='viewer')
        post(f'/life/projects/{pid}/invite',username='editor_user',role='editor')
        post('/life/notes',title='Shared design notes',body='## Read-only preview\n\nA shared note with **safe formatting**.',project_id=pid)
        with get_conn() as db:fixture['shared_note_id']=db.execute('SELECT MAX(id) FROM life_notes').fetchone()[0]
        post('/life/devices',name='Demonstration phone')
        with get_conn() as db:fixture['device_id']=db.execute('SELECT MAX(id) FROM life_devices').fetchone()[0]
        if args.map_size:
            assert 1<=args.map_size<=2000
            from app.lifeos import now
            with get_conn() as db:
                ts=now();cur=db.execute('INSERT INTO life_projects(owner_id,name,created_at,updated_at) VALUES(?,?,?,?)',(uid,'Map performance fixture',ts,ts));perf_pid=cur.lastrowid;perf_ids=[]
                for i in range(args.map_size):
                    parent=perf_ids[(i-1)//3] if i else None
                    cur=db.execute('INSERT INTO life_tasks(owner_id,project_id,parent_id,title,status,created_at,updated_at,position) VALUES(?,?,?,?,?,?,?,?)',(uid,perf_pid,parent,f'Performance task {i+1}',('todo','doing','blocked','done')[i%4],ts,ts,i));perf_ids.append(cur.lastrowid)
                db.commit();fixture['performance_project_id']=perf_pid;fixture['performance_task_ids']=perf_ids
        (root/'fixture.json').write_text(json.dumps(fixture))
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=args.port,log_level='warning')


if __name__=='__main__':main()
