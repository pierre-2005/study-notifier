"""Disposable, loopback-only browser fixture. Never reads the installation database."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',required=True)
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    root=Path(args.data_dir).resolve()
    root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):raise SystemExit('Browser fixtures require an empty data directory.')
    os.environ.update(STUDY_NOTIFIER_DB=str(root/'fixture.sqlite'),SESSION_SECRET='browser-fixture-secret-only',
        APP_USERNAME='demo',APP_PASSWORD='MloPreviewOnly!234',COOKIE_SECURE='false',
        MLO_PUBLIC_URL=f'http://127.0.0.1:{args.port}',MLO_SCHEDULER_ENABLED='false',
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
        (root/'fixture.json').write_text(json.dumps({'project_id':pid,'task_ids':ids}))
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=args.port,log_level='warning')


if __name__=='__main__':main()
