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
from app.lifeos import user_id, data_for, projects_for, task_nodes_for
from app.meta import APP_VERSION
from app.workspace import list_sections_for_user

router = APIRouter(prefix='/life', tags=['life-areas'])
from app.ui import templates

def admin(request):
    return getattr(request.state,'legacy_owner',False)

def render(request, template, **kwargs):
    return templates.TemplateResponse(request, template, {'request':request,**kwargs})

@router.get('/study',response_class=HTMLResponse)
def study(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        tasks=[dict(x) for x in data_for(conn,uid,'open',limit=8,area='Study')]
        projects=[dict(x) for x in projects_for(conn,uid) if x['area']=='Study'][:6]
        private_courses=conn.execute('''SELECT c.*,COUNT(t.id) AS task_count,COALESCE(SUM(t.status='done'),0) AS done_count
            FROM life_courses c LEFT JOIN life_tasks t ON t.project_id=c.project_id
            WHERE c.user_id=? GROUP BY c.id ORDER BY c.created_at DESC''',(uid,)).fetchall()
        course_projects={c['project_id'] for c in private_courses}
        projects=[p for p in projects if p['id'] not in course_projects]
        assessments=[dict(r) for r in conn.execute('''SELECT a.*,t.title,t.status,c.name AS course_name,t.due_on AS task_due
            FROM life_course_assessments a JOIN life_courses c ON c.id=a.course_id
            JOIN life_tasks t ON t.id=a.task_id WHERE a.user_id=? AND c.user_id=?
            AND t.owner_id=? AND t.status!='done' ORDER BY t.due_on IS NULL,t.due_on,t.id LIMIT 12''',(uid,uid,uid))]
        task_nodes=task_nodes_for(conn,uid,tasks)
        stats=conn.execute("SELECT COUNT(*) AS total,COALESCE(SUM(status='done'),0) AS done FROM life_tasks WHERE owner_id=? AND area='Study'",(uid,)).fetchone()
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
    return render(request,'life_study.html',tasks=tasks,task_nodes=task_nodes,stats=stats,assessments=assessments,projects=projects,courses=courses,private_courses=private_courses,items=items,classes=classes,legacy=admin(request))

@router.get('/work',response_class=HTMLResponse)
def work(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        tasks=[dict(x) for x in data_for(conn,uid,'open',limit=10,area='Work')]
        task_nodes=task_nodes_for(conn,uid,tasks)
        projects=[dict(x) for x in projects_for(conn,uid) if x['area']=='Work'][:8]
        jobs=[]
        if admin(request):
            jobs=conn.execute('''SELECT id,company,role,status,followup_at_utc
                FROM jobs ORDER BY updated_at_utc DESC LIMIT 20''').fetchall()
    return render(request,'life_work.html',tasks=tasks,task_nodes=task_nodes,projects=projects,jobs=jobs,legacy=admin(request))

@router.get('/money',response_class=HTMLResponse)
def money(request:Request):
    uid=user_id(request)
    if not admin(request):
        return render(request,'life_money.html',expenses=[],total_unpaid=0,upcoming=0,legacy=False)
    from fastapi.responses import RedirectResponse
    return RedirectResponse('/finance',303)

@router.get('/spaces',response_class=HTMLResponse)
def spaces(request:Request):
    uid=user_id(request)
    sections=list_sections_for_user(uid,sidebar_only=False)
    with get_conn() as conn:
        projects=projects_for(conn,uid)[:12]
    return render(request,'life_spaces.html',sections=sections,projects=projects)
