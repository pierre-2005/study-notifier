"""Safe, preview-first CSV migration into the unified task engine.

Uploads stay in SQLite only until confirmed or expired. No arbitrary filesystem writes.
"""
from __future__ import annotations
import csv,hashlib,io,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.lifeos import user_id, now, pick, safe_day, AREAS, PRIORITIES
from app.meta import APP_VERSION

router=APIRouter(prefix='/life/import',tags=['import'])
from app.ui import templates


def init_import_schema():
    with get_conn() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS life_import_previews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          sha256 TEXT NOT NULL, rows_json TEXT NOT NULL,
          created_at TEXT NOT NULL, committed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_life_imports_owner ON life_import_previews(owner_id,created_at DESC);
        ''')
        conn.commit()


def field(row, *names):
    normalized={str(k or '').strip().lower().replace('_',' ').replace('-',' '):str(v or '').strip() for k,v in row.items()}
    return next((normalized[n] for n in names if normalized.get(n)), '')


def parse_rows(blob):
    try: content=blob.decode('utf-8-sig')
    except UnicodeDecodeError: raise HTTPException(422,'CSV must be UTF-8 encoded.')
    csv_reader=csv.DictReader(io.StringIO(content))
    if not csv_reader.fieldnames: raise HTTPException(422,'The file needs a header row.')
    records=[]
    for line in csv_reader:
        if len(records)>=2000:raise HTTPException(422,'Please import 2,000 rows or fewer per upload.')
        title=field(line,'title','task','task name','name','content')[:240]
        if not title: continue
        due=field(line,'due on','due date','due','deadline','date')
        if due:
            try: due=safe_day(due[:10])
            except HTTPException: due=None  # Ambiguous external dates require later manual correction.
        status=field(line,'status','state').lower()
        if status in ('complete','completed','finished'):status='done'
        if status in ('in progress','in-progress'):status='doing'
        status=pick(status,('todo','doing','blocked','done'),'todo')
        priority=pick(field(line,'priority').lower(),PRIORITIES,'normal')
        project=field(line,'project','project name')[:160]
        area=pick(field(line,'area','category'),AREAS,'Personal')
        records.append({'title':title,'description':field(line,'description','notes')[:10000],
                        'due_on':due,'status':status,'priority':priority,'area':area,'project':project})
    if not records:raise HTTPException(422,'No task titles found. Include a Title or Task column.')
    return records


@router.get('',response_class=HTMLResponse)
def import_page(request:Request):
    user_id(request)
    return templates.TemplateResponse(request,'life_import.html',{'request':request,'preview':None,'error':None})


@router.post('/preview',response_class=HTMLResponse)
async def preview(request:Request,file:UploadFile=File(...)):
    uid=user_id(request)
    blob=await file.read(1_050_000)
    if len(blob)>1_000_000: raise HTTPException(413,'Maximum CSV upload size is 1 MB')
    records=parse_rows(blob)
    digest=hashlib.sha256(blob).hexdigest()
    with get_conn() as conn:
        completed=conn.execute('SELECT 1 FROM life_import_previews WHERE owner_id=? AND sha256=? AND committed_at IS NOT NULL',(uid,digest)).fetchone()
        if completed: raise HTTPException(409,'This exact CSV was already imported. Change the file if you want to import new data.')
        cur=conn.execute('INSERT INTO life_import_previews(owner_id,sha256,rows_json,created_at) VALUES(?,?,?,?)',
                         (uid,digest,json.dumps(records),now()))
        iid=cur.lastrowid
        conn.commit()
    return templates.TemplateResponse(request,'life_import.html',{'request':request,'preview':{'id':iid,'count':len(records),'rows':records[:12],'projects':len(set(r['project'] for r in records if r['project']))},'error':None})


@router.post('/{import_id}/commit')
def commit(request:Request,import_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        record=conn.execute('SELECT * FROM life_import_previews WHERE id=? AND owner_id=?',(import_id,uid)).fetchone()
        if not record: raise HTTPException(404,'Import preview not found')
        if record['committed_at']: raise HTTPException(409,'This import was already completed')
        timestamp=datetime.fromisoformat(record['created_at'])
        if datetime.now(timezone.utc)-timestamp>timedelta(hours=24):
            raise HTTPException(410,'Preview expired. Upload the CSV again.')
        if conn.execute('SELECT 1 FROM life_import_previews WHERE owner_id=? AND sha256=? AND committed_at IS NOT NULL',(uid,record['sha256'])).fetchone():
            raise HTTPException(409,'This CSV was already imported')
        rows=json.loads(record['rows_json'])
        project_cache={}
        ts=now()
        for row in rows:
            name=row['project']
            pid=None
            if name:
                if name not in project_cache:
                    existing=conn.execute('SELECT id FROM life_projects WHERE owner_id=? AND name=? AND status!=?',(uid,name,'archived')).fetchone()
                    if existing: project_cache[name]=existing['id']
                    else:
                        cur=conn.execute('INSERT INTO life_projects(owner_id,name,area,template,created_at,updated_at) VALUES(?,?,?,\'blank\',?,?)',
                                         (uid,name,row['area'],ts,ts))
                        project_cache[name]=cur.lastrowid
                pid=project_cache[name]
            conn.execute('''INSERT INTO life_tasks(owner_id,project_id,title,description,status,priority,area,due_on,created_at,updated_at,completed_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
              (uid,pid,row['title'],row['description'],row['status'],row['priority'],row['area'],row['due_on'],ts,ts,ts if row['status']=='done' else None))
        conn.execute('UPDATE life_import_previews SET committed_at=? WHERE id=?',(ts,import_id))
        conn.commit()
    return RedirectResponse('/life/tasks?view=all',status_code=303)
