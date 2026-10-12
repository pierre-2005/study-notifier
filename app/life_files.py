"""Private attachment store with owner/project access checks and forced downloads."""
from __future__ import annotations
import os,secrets
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter,Request,HTTPException,UploadFile,File,Form
from fastapi.responses import RedirectResponse,FileResponse
from app.db import DB_PATH,get_conn
from app.lifeos import user_id,task_access,note_access,access

router=APIRouter(prefix='/life/files',tags=['attachments'])
ROOT=Path(os.getenv('MLO_ATTACHMENT_DIR', str(Path(DB_PATH).parent/'mlo_uploads')))
MAX_BYTES=int(os.getenv('MLO_MAX_UPLOAD_BYTES','10485760'))
ALLOWED={'.pdf','.txt','.md','.csv','.png','.jpg','.jpeg','.webp','.gif','.docx','.xlsx','.pptx','.zip','.json','.svg'}


def init_file_schema():
    ROOT.mkdir(parents=True,exist_ok=True)
    with get_conn() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS life_files (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE CASCADE,
          task_id INTEGER REFERENCES life_tasks(id) ON DELETE CASCADE,
          note_id INTEGER REFERENCES life_notes(id) ON DELETE CASCADE,
          filename TEXT NOT NULL, stored TEXT NOT NULL UNIQUE,
          size_bytes INTEGER NOT NULL, created_at TEXT NOT NULL,
          CHECK ((task_id IS NOT NULL)+(project_id IS NOT NULL)+(note_id IS NOT NULL)=1)
        );
        CREATE INDEX IF NOT EXISTS life_files_task ON life_files(task_id);
        CREATE INDEX IF NOT EXISTS life_files_project ON life_files(project_id);
        CREATE INDEX IF NOT EXISTS life_files_note ON life_files(note_id);
        ''')
        conn.commit()


def visible(conn,uid,row,edit=False):
    if row['task_id']:
        task_access(conn,uid,row['task_id'],edit=edit)
    elif row['note_id']:
        note_access(conn,uid,row['note_id'],edit=edit)
    elif row['project_id']:
        access(conn,uid,row['project_id'],edit=edit)
    else: raise HTTPException(404,'File not found')


def file_return(row):
    if row['task_id']:return f"/life/tasks/{row['task_id']}"
    if row['note_id']:return f"/life/notes/{row['note_id']}"
    return f"/life/projects/{row['project_id']}"


@router.post('/upload')
async def upload_file(request:Request,file:UploadFile=File(...),task_id:str=Form(''),note_id:str=Form(''),project_id:str=Form('')):
    uid=user_id(request)
    original=Path((file.filename or '').replace('\\','/')).name[:180]
    extension=Path(original).suffix.lower()
    if not original or extension not in ALLOWED:
        raise HTTPException(415,'File format not supported. Use a document, image, CSV, JSON or ZIP file.')
    identifiers=[bool(task_id),bool(note_id),bool(project_id)]
    if sum(identifiers)!=1:raise HTTPException(422,'Select exactly one parent')
    tid=int(task_id) if task_id.isdigit() else None
    nid=int(note_id) if note_id.isdigit() else None
    pid=int(project_id) if project_id.isdigit() else None
    if sum(v is not None for v in (tid,nid,pid))!=1:raise HTTPException(422,'Invalid parent')
    with get_conn() as conn:
        if tid:task_access(conn,uid,tid,edit=True)
        elif nid:note_access(conn,uid,nid,edit=True)
        else:access(conn,uid,pid,edit=True)
    data=await file.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise HTTPException(413,'The file is too large for this server.')
    key=secrets.token_hex(20)+extension
    location=ROOT/key
    try:
        with location.open('xb') as fp:fp.write(data)
        with get_conn() as conn:
            conn.execute('INSERT INTO life_files(owner_id,project_id,task_id,note_id,filename,stored,size_bytes,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (uid,pid,tid,nid,original,key,len(data),datetime.now(timezone.utc).isoformat()))
            conn.commit()
    except Exception:
        location.unlink(missing_ok=True)
        raise
    return RedirectResponse(f'/life/tasks/{tid}' if tid else f'/life/notes/{nid}' if nid else f'/life/projects/{pid}',status_code=303)


@router.get('/{file_id}')
def download_file(request:Request,file_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        row=conn.execute('SELECT * FROM life_files WHERE id=?',(file_id,)).fetchone()
        if not row:raise HTTPException(404,'File not found')
        visible(conn,uid,row)
    location=ROOT/row['stored']
    if not location.is_file():raise HTTPException(404,'File no longer on this server')
    return FileResponse(location,filename=row['filename'],media_type='application/octet-stream',headers={'X-Content-Type-Options':'nosniff','Cache-Control':'private, no-store'})


@router.post('/{file_id}/delete')
def delete_file(request:Request,file_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        row=conn.execute('SELECT * FROM life_files WHERE id=?',(file_id,)).fetchone()
        if not row:raise HTTPException(404,'File not found')
        visible(conn,uid,row,edit=True)
        destination=file_return(row)
        conn.execute('DELETE FROM life_files WHERE id=?',(file_id,))
        conn.commit()
    (ROOT/row['stored']).unlink(missing_ok=True)
    return RedirectResponse(destination,status_code=303)
