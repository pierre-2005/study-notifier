"""Coherent Study, Work, Money and Spaces navigation over original source-of-truth data.

The old academic/job/finance tables are not copied or exposed to secondary users.
Personal tasks and projects remain scoped through lifeos access checks.
"""
from pathlib import Path
from datetime import date, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.lifeos import user_id, data_for, projects_for
from app.meta import APP_VERSION
from app.workspace import list_sections_for_user

router = APIRouter(prefix='/life', tags=['life-areas'])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent/'templates'))
templates.env.globals['APP_VERSION'] = APP_VERSION
templates.env.globals['current_day'] = lambda: date.today().isoformat()

def admin(request):
    return request.state.current_user['role'] == 'admin'

def render(request, template, **kwargs):
    return templates.TemplateResponse(request, template, {'request':request,**kwargs})

@router.get('/study',response_class=HTMLResponse)
def study(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        tasks=[dict(x) for x in data_for(conn,uid,'open',limit=200) if x['area']=='Study'][:8]
        projects=[dict(x) for x in projects_for(conn,uid) if x['area']=='Study'][:6]
        courses=[];items=[];classes=[]
        if admin(request):
            courses=conn.execute('''SELECT c.id,c.name,c.term,c.color,COUNT(i.id) AS open_count FROM courses c
                LEFT JOIN items i ON i.course_id=c.id AND i.status!='done'
                GROUP BY c.id ORDER BY c.created_at_utc DESC LIMIT 12''').fetchall()
            items=conn.execute('''SELECT i.id,i.title,i.type,i.status,i.due_at_utc,c.name AS course_name
                FROM items i JOIN courses c ON c.id=i.course_id
                WHERE i.status!='done' ORDER BY i.due_at_utc LIMIT 12''').fetchall()
            classes=conn.execute('''SELECT id,title,weekday,start_time_local,location FROM class_meetings
                WHERE active=1 ORDER BY weekday,start_time_local LIMIT 12''').fetchall()
    return render(request,'life_study.html',tasks=tasks,projects=projects,courses=courses,items=items,classes=classes,legacy=admin(request))

@router.get('/work',response_class=HTMLResponse)
def work(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        tasks=[dict(x) for x in data_for(conn,uid,'open',limit=200) if x['area']=='Work'][:10]
        projects=[dict(x) for x in projects_for(conn,uid) if x['area']=='Work'][:8]
        jobs=[]
        if admin(request):
            jobs=conn.execute('''SELECT id,company,role,status,followup_at_utc
                FROM jobs ORDER BY updated_at_utc DESC LIMIT 20''').fetchall()
    return render(request,'life_work.html',tasks=tasks,projects=projects,jobs=jobs,legacy=admin(request))

@router.get('/money',response_class=HTMLResponse)
def money(request:Request):
    uid=user_id(request)
    if not admin(request):
        return render(request,'life_money.html',expenses=[],total_unpaid=0,upcoming=0,legacy=False)
    with get_conn() as conn:
        rows=conn.execute('''SELECT id,title,category,amount,due_at_utc,status,recurrence
            FROM expenses ORDER BY CASE WHEN status='unpaid' THEN 0 ELSE 1 END,due_at_utc LIMIT 30''').fetchall()
        totals=conn.execute("SELECT COALESCE(SUM(amount),0) AS total,COUNT(*) AS count FROM expenses WHERE status='unpaid'").fetchone()
    return render(request,'life_money.html',expenses=rows,total_unpaid=totals['total'],upcoming=totals['count'],legacy=True)

@router.get('/spaces',response_class=HTMLResponse)
def spaces(request:Request):
    uid=user_id(request)
    sections=list_sections_for_user(uid,sidebar_only=False)
    with get_conn() as conn:
        projects=projects_for(conn,uid)[:12]
    return render(request,'life_spaces.html',sections=sections,projects=projects)
