"""Private syllabus review and atomic, duplicate-safe import into real MLO tasks."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import shutil
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import requests
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app.auth import user_capabilities
from app.db import get_conn
from app.lifeos import user_id, now
from app.meta import APP_VERSION
from app.outline_parse import candidates
from app import outline_ai

router=APIRouter(prefix='/life/study',tags=['course outlines'])
from app.ui import templates
MAX_BYTES=10*1024*1024


def init_course_schema():
    with get_conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS life_course_imports (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          fingerprint TEXT NOT NULL, filename TEXT NOT NULL, pages_json TEXT NOT NULL,
          preview_json TEXT NOT NULL, parser TEXT NOT NULL, term_year INTEGER,
          created_at TEXT NOT NULL, committed_at TEXT, course_id INTEGER,
          UNIQUE(user_id,fingerprint)
        );
        CREATE TABLE IF NOT EXISTS life_courses (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER NOT NULL REFERENCES life_projects(id) ON DELETE CASCADE,
          code TEXT NOT NULL, name TEXT NOT NULL, term TEXT NOT NULL,
          created_at TEXT NOT NULL, UNIQUE(user_id,code,term)
        );
        CREATE TABLE IF NOT EXISTS life_course_assessments (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          course_id INTEGER NOT NULL REFERENCES life_courses(id) ON DELETE CASCADE,
          task_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL,
          import_id INTEGER REFERENCES life_course_imports(id) ON DELETE SET NULL,
          kind TEXT NOT NULL, title TEXT NOT NULL, due_on TEXT, due_at_utc TEXT, weight REAL,
          evidence TEXT NOT NULL DEFAULT '', source_page INTEGER, fingerprint TEXT NOT NULL,
          UNIQUE(user_id,course_id,fingerprint)
        );
        CREATE INDEX IF NOT EXISTS course_assessment_task ON life_course_assessments(task_id);
        ''')
        db.commit()


def _can_import(request):
    caps=user_capabilities(request.state.current_user)
    if not caps['import_tasks'] or not caps['projects_create']:
        raise HTTPException(403,'Course import is disabled for this account.')


def parse_upload(data, extension):
    with tempfile.TemporaryDirectory(prefix='mlo-outline-') as tmp:
        path=Path(tmp)/('source'+extension)
        path.write_bytes(data)
        try:
            result=subprocess.run([sys.executable,'-m','app.outline_parse',str(path),extension],
                capture_output=True,timeout=90,cwd=str(Path(__file__).resolve().parent.parent),
                env={**{k:os.environ[k] for k in ("SystemRoot","TEMP","TMP","TESSDATA_PREFIX") if k in os.environ},"PATH":os.environ.get("PATH","") if os.name=="nt" else "/usr/bin:/bin","LANG":"C.UTF-8","PYTHONUTF8":"1","PYTHONPATH":str(Path(__file__).resolve().parent.parent),"MLO_TESSERACT":shutil.which("tesseract") or "tesseract","MLO_PDFTOPPM":shutil.which("pdftoppm") or "pdftoppm"})
        except subprocess.TimeoutExpired as exc:
            raise ValueError('This document took too long to read. Split it into smaller files.') from exc
        if len(result.stdout)>3_000_000:
            raise ValueError('The extracted document is too large.')
        try:
            parsed=json.loads(result.stdout)
        except (ValueError,UnicodeDecodeError) as exc:
            raise ValueError('The document could not be read. Try a different format.') from exc
        if result.returncode or 'error' in parsed:
            raise ValueError(parsed.get('error','The document could not be read.'))
        return parsed['pages']


def view(request,name,**context):
    return templates.TemplateResponse(request,name,{'request':request,**context})


@router.get('/import',response_class=HTMLResponse)
def upload_page(request:Request):
    _can_import(request)
    return view(request,'course_import.html',ai_enabled=outline_ai.enabled(),error='',year=date.today().year)


@router.post('/import',response_class=HTMLResponse)
async def upload(request:Request,file:UploadFile=File(...),term_year:int=Form(...),use_ai:bool=Form(False)):
    _can_import(request)
    uid=user_id(request)
    from app.auth_delivery import allow
    if not allow('outline-upload:'+str(uid),20,60):
        raise HTTPException(429,'Too many imports. Try again in an hour.')
    if not 2000<=term_year<=2100:
        raise HTTPException(422,'Choose a valid term year.')
    extension=Path(file.filename or '').suffix.lower()
    if extension not in ('.pdf','.docx','.png','.jpg','.jpeg','.txt'):
        raise HTTPException(415,'Use PDF, DOCX, PNG, JPG or text.')
    data=await file.read(MAX_BYTES+1)
    if not data or len(data)>MAX_BYTES:
        raise HTTPException(413,'Upload a file of up to 10 MB.')
    fingerprint=hashlib.sha256(data).hexdigest()
    with get_conn() as db:
        existing=db.execute('SELECT id FROM life_course_imports WHERE user_id=? AND fingerprint=?',(uid,fingerprint)).fetchone()
    if existing:
        return RedirectResponse(f"/life/study/import/{existing['id']}",303)
    try:
        pages=await run_in_threadpool(parse_upload,data,extension)
        rows=await run_in_threadpool(outline_ai.extract,pages,term_year) if use_ai else candidates(pages,term_year)
        # Validate all untrusted model fields even before showing the preview.
        for row in rows:
            if not isinstance(row.get('title'),str) or not isinstance(row.get('evidence'),str):
                raise ValueError('The extractor returned invalid rows. Use local extraction.')
            row['title']=row['title'][:240]
            row['evidence']=row['evidence'][:800]
        preview={'rows':rows,'course_name':'','course_code':'','term':str(term_year)}
        first='\n'.join(p['text'] for p in pages)[:5000]
        code=re.search(r'\b([A-Z]{3,5}\s?\d{3}[A-Z]?)\b',first)
        if code: preview['course_code']=code[1]
        with get_conn() as db:
            db.execute('DELETE FROM life_course_imports WHERE user_id=? AND committed_at IS NULL AND created_at<?',
                       (uid,(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()))
            db.execute('''INSERT OR IGNORE INTO life_course_imports
                (user_id,fingerprint,filename,pages_json,preview_json,parser,term_year,created_at)
                VALUES(?,?,?,?,?,?,?,?)''',(uid,fingerprint,Path(file.filename or 'outline').name[:180],
                json.dumps(pages),json.dumps(preview),'ai' if use_ai else 'local',term_year,now()))
            import_id=db.execute('SELECT id FROM life_course_imports WHERE user_id=? AND fingerprint=?',(uid,fingerprint)).fetchone()[0]
            db.commit()
    except (ValueError,RuntimeError,subprocess.SubprocessError,requests.RequestException) as exc:
        return view(request,'course_import.html',ai_enabled=outline_ai.enabled(),error=('AI extraction is unavailable. Retry or use local extraction.' if isinstance(exc,requests.RequestException) else str(exc)[:300]),year=term_year)
    return RedirectResponse(f'/life/study/import/{import_id}',303)


def owned_import(db,uid,import_id):
    row=db.execute('SELECT * FROM life_course_imports WHERE id=? AND user_id=?',(import_id,uid)).fetchone()
    if not row: raise HTTPException(404,'Import not found')
    return row


@router.get('/import/{import_id}',response_class=HTMLResponse)
def review(request:Request,import_id:int):
    with get_conn() as db:
        row=owned_import(db,user_id(request),import_id)
    return view(request,'course_review.html',record=row,preview=json.loads(row['preview_json']),pages=json.loads(row['pages_json']))


class Assessment(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    title:str=Field(min_length=1,max_length=240)
    kind:str
    due_on:str|None=None
    time:str|None=None
    weight:float|None=Field(default=None,ge=0,le=100,allow_inf_nan=False)
    source_index:int|None=None


class Commit(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    course_name:str=Field(min_length=1,max_length=160)
    course_code:str=Field(min_length=1,max_length=40)
    term:str=Field(min_length=1,max_length=80)
    rows:list[Assessment]=Field(max_length=200)


@router.post('/import/{import_id}/commit')
def commit(request:Request,import_id:int,body:Commit):
    _can_import(request)
    uid=user_id(request)
    if not all(v.strip() for v in (body.course_name,body.course_code,body.term)):
        raise HTTPException(422,'Enter the course name, code and term.')
    from app.v37 import read_user_setup
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        record=owned_import(db,uid,import_id)
        if record['committed_at']:
            return {'ok':True,'course_id':record['course_id'],'created':0,'already_imported':True}
        prefs=read_user_setup(db,uid)
        zone=ZoneInfo(prefs['timezone'])
        source_rows=json.loads(record['preview_json'])['rows']
        clean=[]
        for row in body.rows:
            if row.kind not in ('assignment','exam','lab'):
                raise HTTPException(422,'Choose an assessment type')
            if not row.title.strip(): raise HTTPException(422,'Enter an assessment title')
            try:
                day=date.fromisoformat(row.due_on) if row.due_on else None
                if day and not 2000<=day.year<=2100: raise ValueError()
                stamp=None
                if row.time:
                    if not day or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',row.time): raise ValueError()
                    local=datetime.fromisoformat(day.isoformat()+'T'+row.time).replace(tzinfo=zone)
                    stamp=local.astimezone(timezone.utc)
                    if stamp.astimezone(zone).replace(tzinfo=None)!=local.replace(tzinfo=None):
                        raise ValueError()
                    if local.replace(fold=0).utcoffset()!=local.replace(fold=1).utcoffset():
                        raise ValueError()
            except ValueError as exc:
                raise HTTPException(422,'Check assessment dates and times, including daylight saving changes.') from exc
            original={}
            if row.source_index is not None:
                if not 0<=row.source_index<len(source_rows): raise HTTPException(422,'Invalid source row')
                original=source_rows[row.source_index]
            clean.append((row,day,stamp,original))
        code=body.course_code.strip().upper()
        course=db.execute('SELECT * FROM life_courses WHERE user_id=? AND code=? AND term=?',(uid,code,body.term.strip())).fetchone()
        if not course:
            project=db.execute('''INSERT INTO life_projects(owner_id,name,description,area,template,created_at,updated_at)
                VALUES(?,?,?,'Study','blank',?,?)''',(uid,body.course_name.strip(),'Course assessments',now(),now()))
            course_id=db.execute('INSERT INTO life_courses(user_id,project_id,code,name,term,created_at) VALUES(?,?,?,?,?,?)',
                (uid,project.lastrowid,code,body.course_name.strip(),body.term.strip(),now())).lastrowid
            project_id=project.lastrowid
        else:
            course_id,project_id=course['id'],course['project_id']
        created=0
        for row,day,stamp,original in clean:
            fingerprint=hashlib.sha256(json.dumps([row.title.strip().casefold(),row.kind,day.isoformat() if day else None]).encode()).hexdigest()
            if db.execute('SELECT 1 FROM life_course_assessments WHERE user_id=? AND course_id=? AND fingerprint=?',(uid,course_id,fingerprint)).fetchone():
                continue
            task=db.execute('''INSERT INTO life_tasks(owner_id,project_id,title,description,area,due_on,created_at,updated_at)
                VALUES(?,?,?,?,'Study',?,?,?)''',(uid,project_id,row.title.strip(),
                original.get('evidence','')[:800],day.isoformat() if day else None,now(),now()))
            db.execute('''INSERT INTO life_course_assessments(user_id,course_id,task_id,import_id,kind,title,due_on,
                due_at_utc,weight,evidence,source_page,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                (uid,course_id,task.lastrowid,import_id,row.kind,row.title.strip(),day.isoformat() if day else None,
                 stamp.isoformat() if stamp else None,row.weight,original.get('evidence','')[:800],original.get('source_page'),fingerprint))
            created+=1
        db.execute('UPDATE life_course_imports SET committed_at=?,course_id=? WHERE id=?',(now(),course_id,import_id))
        db.commit()
    return {'ok':True,'course_id':course_id,'created':created}


@router.post('/import/{import_id}/delete')
def delete_import(request:Request,import_id:int):
    uid=user_id(request)
    with get_conn() as db:
        owned_import(db,uid,import_id)
        db.execute('DELETE FROM life_course_imports WHERE id=? AND user_id=?',(import_id,uid))
        db.commit()
    return RedirectResponse('/life/study',303)


@router.get('/courses/{course_id}',response_class=HTMLResponse)
def course_page(request:Request,course_id:int):
    uid=user_id(request)
    with get_conn() as db:
        course=db.execute('SELECT * FROM life_courses WHERE id=? AND user_id=?',(course_id,uid)).fetchone()
        if not course: raise HTTPException(404,'Course not found')
        assessments=db.execute('''SELECT a.*,t.status,t.title AS task_title,t.due_on AS task_due_on FROM life_course_assessments a
            LEFT JOIN life_tasks t ON t.id=a.task_id WHERE a.course_id=? AND a.user_id=? ORDER BY a.due_on,a.id''',(course_id,uid)).fetchall()
    return view(request,'study_course.html',course=course,assessments=assessments)
