"""Bookmark and cached-form adapters over canonical tasks. No duplicate task store."""
from fastapi import APIRouter,Request,Form,HTTPException
from fastapi.responses import RedirectResponse
from app.db import get_conn
from app.lifeos import user_id,task_access,change_task_status,delete_task,create_task,edit_task
router=APIRouter()

def mapped_task(request,todo_id):
    with get_conn() as conn:
        row=conn.execute('SELECT task_id FROM life_legacy_todo_map WHERE todo_id=?',(todo_id,)).fetchone()
        if not row or not row['task_id']:raise HTTPException(404,'This task was removed.')
        task_access(conn,user_id(request),row['task_id'])
        return row['task_id']

@router.get('/todos/{todo_id}')
def old_task(request:Request,todo_id:int):
    return RedirectResponse(f'/life/tasks/{mapped_task(request,todo_id)}',303)

@router.post('/todos/{todo_id}/status')
def old_task_status(request:Request,todo_id:int,status:str=Form(...)):
    return change_task_status(request,mapped_task(request,todo_id),status,'/life/tasks')

@router.post('/todos/{todo_id}/delete')
def old_task_delete(request:Request,todo_id:int):
    return delete_task(request,mapped_task(request,todo_id))

@router.post('/todos/new')
def old_task_create(request:Request,title:str=Form(...),notes:str=Form(''),due_at_local:str=Form('')):
    from app.timeutil import parse_local_datetime_localinput
    from app.config import settings
    from zoneinfo import ZoneInfo
    due=parse_local_datetime_localinput(due_at_local,settings.timezone).astimezone(ZoneInfo(settings.timezone)).date().isoformat() if due_at_local else ''
    return create_task(request,title,description=notes,due_on=due,project_id='',parent_id='',estimated_minutes=0,priority='normal',area='Personal',recurrence='none',next_page='/life/tasks')

@router.post('/todos/{todo_id}/update')
def old_task_update(request:Request,todo_id:int,title:str=Form(...),notes:str=Form(''),status:str=Form('todo'),due_at_local:str=Form('')):
    from app.timeutil import parse_local_datetime_localinput
    from app.config import settings
    from zoneinfo import ZoneInfo
    tid=mapped_task(request,todo_id)
    with get_conn() as conn:t=task_access(conn,user_id(request),tid,edit=True)
    due=parse_local_datetime_localinput(due_at_local,settings.timezone).astimezone(ZoneInfo(settings.timezone)).date().isoformat() if due_at_local else ''
    return edit_task(request,tid,title,notes,status,t['priority'],due,t['recurrence'],int(t['estimated_minutes'] or 0))

@router.post('/todos/reminder/save')
@router.post('/todos/reminder/test')
def old_reminder_settings():
    return RedirectResponse('/life/onboarding',303)
