"""MLO 3 core: private-by-default projects, tasks, notes, planning, habits and reports.

Every database query for mutable user content is scoped by the authenticated user,
including project memberships, and uses bound SQL parameters.
"""
from __future__ import annotations

import csv
import io
import json
import calendar
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.config import settings
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.meta import APP_VERSION

router = APIRouter(prefix="/life", tags=["life-os"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
templates.env.globals["APP_VERSION"] = APP_VERSION
templates.env.globals["current_day"] = lambda: date.today().isoformat()

AREAS = ("Personal", "Work", "Study", "Home", "Health", "Other")
PRIORITIES = ("low", "normal", "high", "urgent")
STATUSES = ("todo", "doing", "blocked", "done")
CAREERS = {
    "blank": ("Start from scratch", [], ""),
    "personal": ("Personal goals", ["Define the outcome", "Choose the next step", "Review your progress"], "Personal"),
    "student": ("Study plan", ["Gather course requirements", "Plan study blocks", "Complete assignments", "Review before exams"], "Study"),
    "electrical": ("Electrical engineering", ["Review requirements", "Prepare schematics", "Build BOM", "Submit design review", "Complete verification"], "Work"),
    "software": ("Software development", ["Define requirements", "Plan implementation", "Build first release", "Test key workflows", "Deploy and monitor"], "Work"),
    "mechanical": ("Mechanical engineering", ["Design brief", "CAD concept", "Prototype plan", "Design verification", "Release documentation"], "Work"),
    "biomedical": ("Biomedical engineering", ["User needs", "Design inputs", "Risk analysis", "Verification plan", "Design review"], "Work"),
    "project_manager": ("Project management", ["Project charter", "Scope and WBS", "Schedule milestones", "Risk register", "Status review"], "Work"),
    "freelancer": ("Client project", ["Confirm client brief", "Agree deliverables", "Produce first draft", "Client review", "Final handover"], "Work"),
    "content": ("Content creator", ["Collect ideas", "Draft content", "Edit content", "Schedule publishing", "Review analytics"], "Work"),
    "construction": ("Construction", ["Review drawings", "Plan resources", "Procure materials", "Complete inspections", "Close deficiencies"], "Work"),
    "research": ("Research", ["Define question", "Review literature", "Plan experiments", "Analyze results", "Draft report"], "Study"),
    "business": ("Small business", ["Define customer need", "Build sales pipeline", "Set operations checklist", "Review financial plan", "Quarterly review"], "Work"),
    "family": ("Family organization", ["Family calendar", "Household tasks", "Budget check-in", "Meal plan", "Monthly review"], "Home"),
    "civil": ("Civil / structural engineer", ["Define scope and permits", "Review plans and drawings", "Coordinate submittals", "Schedule field inspections", "Close outstanding issues"], "Work"),
    "chemical": ("Chemical / process engineer", ["Document process requirements", "Review P&IDs", "Collect HAZOP actions", "Prepare trial plan", "Close safety review"], "Work"),
    "manufacturing": ("Manufacturing / industrial engineer", ["Analyze production flow", "Plan capacity", "Write SOPs", "Track quality actions", "Review maintenance"], "Work"),
    "aerospace": ("Aerospace / automotive engineer", ["Capture configuration baseline", "Review requirements", "Plan validation tests", "Track supplier deliverables", "Close verification gates"], "Work"),
    "data_ml": ("Data scientist / ML engineer", ["Define evaluation metric", "Catalog datasets", "Run baseline experiment", "Track model evaluations", "Prepare deployment checks"], "Work"),
    "architect": ("Architect / urban planner", ["Confirm design brief", "Prepare concept drawings", "Collect approvals", "Review permits", "Record client feedback"], "Work"),
    "skilled_trades": ("Skilled trades", ["Confirm work order", "Plan tools and materials", "Perform site checklist", "Document inspection", "Close service report"], "Work"),
    "it": ("IT / sysadmin", ["Triage issues", "Review asset inventory", "Schedule change window", "Prepare rollback plan", "Update knowledge base"], "Work"),
    "health_admin": ("Healthcare administration", ["Review shift schedule", "Track credentials", "Prepare training", "Complete administrative checklists", "Review continuing education"], "Work"),
    "pharmacy": ("Pharmacy / laboratory admin", ["Review supply expiry", "Update SOPs", "Track staff training", "Schedule quality review", "Check inventory"], "Work"),
    "legal": ("Legal practice admin", ["Capture matter deadlines", "Collect documents", "Review evidence requests", "Draft next actions", "Record billable time"], "Work"),
    "accounting": ("Accounting / audit", ["Collect source documents", "Reconcile accounts", "Perform review checks", "Track outstanding client requests", "Prepare close report"], "Work"),
    "finance": ("Financial analyst", ["Define research question", "Review model inputs", "Record assumptions", "Prepare draft report", "Complete review"], "Work"),
    "teacher": ("Teacher / educator", ["Outline learning objectives", "Prepare lesson resources", "Plan assignments", "Schedule grading", "Review class outcomes"], "Work"),
    "hr": ("Human resources", ["Confirm hiring need", "Review applicants", "Schedule interviews", "Prepare onboarding", "Track training"], "Work"),
    "sales": ("Sales / account manager", ["Qualify leads", "Prepare proposals", "Schedule follow-ups", "Review pipeline", "Track quarterly targets"], "Work"),
    "marketing": ("Marketing / social media", ["Plan campaign brief", "Develop content calendar", "Draft creative assets", "Schedule approval", "Review analytics"], "Work"),
    "writing": ("Writer / editor / journalist", ["Collect story ideas", "Review sources", "Write draft", "Complete editorial review", "Publish and archive"], "Work"),
    "designer": ("Designer / creative", ["Collect design brief", "Prepare concepts", "Gather references", "Review client feedback", "Deliver assets"], "Work"),
    "executive": ("Executive / team lead", ["Define quarterly priorities", "Review delegated work", "Record key decisions", "Track blockers", "Prepare weekly review"], "Work"),
    "property": ("Property / real estate", ["Review properties", "Schedule viewings", "Track documents", "Plan maintenance", "Follow up with contacts"], "Work"),
    "hospitality": ("Hospitality / retail", ["Create opening checklist", "Plan staff schedule", "Review inventory", "Log incidents", "Prepare closing checklist"], "Work"),
    "logistics": ("Logistics / supply chain", ["Review purchase orders", "Track shipments", "Monitor delivery exceptions", "Contact suppliers", "Review weekly operations"], "Work"),
    "nonprofit": ("Nonprofit / public service", ["Define program outcomes", "Plan stakeholder meetings", "Track grant milestones", "Organize evidence", "Prepare outcomes report"], "Work"),
    "coaching": ("Coach / trainer", ["Define program goals", "Plan sessions", "Organize equipment", "Schedule client follow-ups", "Review progress"], "Work"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today() -> str:
    return datetime.now(ZoneInfo(settings.timezone)).date().isoformat()


def user_day(conn, uid):
    from app.v37 import read_user_setup
    return datetime.now(ZoneInfo(read_user_setup(conn,uid)['timezone'])).date()


def user_id(request: Request) -> int:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return int(user["id"])


def text_clean(value: str, limit: int = 200) -> str:
    return (value or "").strip()[:limit]


def pick(value, allowed, fallback):
    return value if value in allowed else fallback


def safe_day(value: str) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(422, "Invalid date")


def redirect(path="/life"):
    if not path.startswith("/life") or path.startswith("//") or "\r" in path or "\n" in path:
        path = "/life"
    return RedirectResponse(path, status_code=303)


def init_life_schema():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS life_preferences (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          experience TEXT NOT NULL DEFAULT 'simple' CHECK(experience IN ('simple','guided','professional')),
          default_area TEXT NOT NULL DEFAULT 'Personal', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS life_projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT 'Personal',
          color TEXT NOT NULL DEFAULT '#7285d5', template TEXT NOT NULL DEFAULT 'blank',
          status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','on_hold','complete','archived')),
          due_on TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_projects_owner ON life_projects(owner_id,status,updated_at DESC);
        CREATE TABLE IF NOT EXISTS life_project_members (
          project_id INTEGER NOT NULL REFERENCES life_projects(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          role TEXT NOT NULL DEFAULT 'editor' CHECK(role IN ('viewer','editor')),
          PRIMARY KEY(project_id,user_id)
        );
        CREATE INDEX IF NOT EXISTS life_members_user ON life_project_members(user_id,project_id);
        CREATE TABLE IF NOT EXISTS life_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE CASCADE,
          parent_id INTEGER REFERENCES life_tasks(id) ON DELETE CASCADE,
          title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','blocked','done')),
          priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('low','normal','high','urgent')),
          area TEXT NOT NULL DEFAULT 'Personal', due_on TEXT,
          estimated_minutes INTEGER NOT NULL DEFAULT 0, recurrence TEXT NOT NULL DEFAULT 'none'
            CHECK(recurrence IN ('none','daily','weekly','monthly')),
          position INTEGER NOT NULL DEFAULT 0, completed_at TEXT,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_tasks_owner_due ON life_tasks(owner_id,status,due_on);
        CREATE INDEX IF NOT EXISTS life_tasks_project_status ON life_tasks(project_id,status,position);
        CREATE TABLE IF NOT EXISTS life_task_dependencies (
          task_id INTEGER NOT NULL REFERENCES life_tasks(id) ON DELETE CASCADE,
          depends_on_id INTEGER NOT NULL REFERENCES life_tasks(id) ON DELETE CASCADE,
          PRIMARY KEY(task_id,depends_on_id), CHECK(task_id != depends_on_id)
        );
        CREATE TABLE IF NOT EXISTS life_project_records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL REFERENCES life_projects(id) ON DELETE CASCADE,
          created_by INTEGER NOT NULL REFERENCES users(id),
          record_type TEXT NOT NULL CHECK(record_type IN ('milestone','risk','issue','decision','deliverable')),
          title TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
          severity TEXT NOT NULL DEFAULT 'medium' CHECK(severity IN ('low','medium','high')),
          status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','monitor','resolved')),
          due_on TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_project_records_project ON life_project_records(project_id,record_type,status);
        CREATE TABLE IF NOT EXISTS life_notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE CASCADE,
          title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT 'Personal',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_notes_owner ON life_notes(owner_id,updated_at DESC);
        CREATE TABLE IF NOT EXISTS life_goals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, target_on TEXT, area TEXT NOT NULL DEFAULT 'Personal',
          status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','complete')),
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS life_habits (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, area TEXT NOT NULL DEFAULT 'Personal',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS life_habit_days (
          habit_id INTEGER NOT NULL REFERENCES life_habits(id) ON DELETE CASCADE,
          day TEXT NOT NULL, PRIMARY KEY(habit_id,day)
        );
        CREATE TABLE IF NOT EXISTS life_time_entries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL,
          project_id INTEGER REFERENCES life_projects(id) ON DELETE SET NULL,
          minutes INTEGER NOT NULL CHECK(minutes>0 AND minutes<=1440),
          note TEXT NOT NULL DEFAULT '', occurred_on TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_time_owner ON life_time_entries(owner_id,occurred_on DESC);
        CREATE TABLE IF NOT EXISTS life_task_views (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          query_params TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_task_views_user ON life_task_views(user_id,id DESC);
        """)
        # Index legacy timeline sources used by the consolidated calendar.
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_items_due ON items(due_at_utc)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_events_start ON events(start_at_utc)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_jobs_followup ON jobs(followup_at_utc)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_tasks_parent ON life_tasks(parent_id,project_id,position)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_tasks_owner_created ON life_tasks(owner_id,created_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_tasks_owner_area ON life_tasks(owner_id,area,status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mlo_time_day ON life_time_entries(owner_id,occurred_on)')
        conn.commit()


def pref(conn, uid):
    row = conn.execute("SELECT * FROM life_preferences WHERE user_id=?", (uid,)).fetchone()
    if row:
        return dict(row)
    return {"experience":"simple","default_area":"Personal"}


def access(conn, uid, project_id, edit=False):
    row = conn.execute("""
      SELECT p.*, CASE WHEN p.owner_id=? THEN 'owner' ELSE m.role END AS my_role
      FROM life_projects p LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=?
      WHERE p.id=? AND (p.owner_id=? OR m.user_id IS NOT NULL)
    """, (uid, uid, project_id, uid)).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    if edit and row["my_role"] == "viewer":
        raise HTTPException(403, "Read-only project")
    return row


def task_access(conn, uid, task_id, edit=False):
    row = conn.execute("SELECT * FROM life_tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Task not found")
    if row["project_id"]:
        access(conn, uid, row["project_id"], edit=edit)
    elif row["owner_id"] != uid:
        raise HTTPException(404, "Task not found")
    return row


def note_access(conn, uid, note_id, edit=False):
    row = conn.execute("SELECT * FROM life_notes WHERE id=?", (note_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Note not found")
    if row["project_id"]:
        access(conn, uid, row["project_id"], edit=edit)
    elif row["owner_id"] != uid:
        raise HTTPException(404, "Note not found")
    return row


def tasks_sql(uid):
    # Notes and tasks in shared projects are deliberately accessible only to explicit members.
    return ("(t.owner_id=? AND t.project_id IS NULL OR EXISTS (SELECT 1 FROM life_projects p "
            "LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=? "
            "WHERE p.id=t.project_id AND (p.owner_id=? OR m.user_id IS NOT NULL)))", (uid,uid,uid))


def data_for(conn, uid, view='all', project=None, limit=150, area=None):
    local_day=user_day(conn,uid)
    cond, params = tasks_sql(uid)
    where = [cond]
    vals = list(params)
    if project is not None:
        access(conn, uid, project)
        where.append("t.project_id=?")
        vals.append(project)
    if view in ("today", "upcoming", "overdue"):
        where.append("t.status != 'done'")
        if view == "today":
            where.append("(t.due_on<=? OR t.due_on IS NULL)")
            vals.append(local_day.isoformat())
        elif view == "overdue":
            where.append("t.due_on<?")
            vals.append(local_day.isoformat())
        else:
            where.append("t.due_on>? AND t.due_on<=?")
            vals.extend([local_day.isoformat(), (local_day+timedelta(days=14)).isoformat()])
    elif view == "done":
        where.append("t.status='done'")
    elif view == "inbox":
        where.append("t.project_id IS NULL AND t.status!='done'")
    elif view == "open":
        where.append("t.status!='done'")
    if area in AREAS:
        where.append('t.area=?')
        vals.append(area)
    vals.append(limit)
    return conn.execute(f"""
       SELECT t.*, p.name AS project_name FROM life_tasks t
       LEFT JOIN life_projects p ON p.id=t.project_id
       WHERE {' AND '.join(where)}
       ORDER BY CASE WHEN t.status='done' THEN 1 ELSE 0 END,
                CASE WHEN t.due_on IS NULL THEN 1 ELSE 0 END, t.due_on,
                CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 ELSE 2 END,
                t.id DESC LIMIT ?
    """, vals).fetchall()



def filtered_tasks(conn, uid, view='open', project=None, *, query='', priority='', area='', sort='due', page=1, page_size=40):
    """Paginated, permission-scoped task finder; never materializes the entire list."""
    local_day=user_day(conn,uid)
    cond, params = tasks_sql(uid)
    clauses = [cond]
    vals = list(params)
    if project is not None:
        access(conn, uid, project)
        clauses.append('t.project_id=?')
        vals.append(project)
    if view in ('today','upcoming','overdue'):
        clauses.append("t.status!='done'")
        if view == 'today':
            clauses.append('(t.due_on<=? OR t.due_on IS NULL)')
            vals.append(local_day.isoformat())
        elif view == 'overdue':
            clauses.append('t.due_on<?')
            vals.append(local_day.isoformat())
        else:
            clauses.append('t.due_on>? AND t.due_on<=?')
            vals.extend([local_day.isoformat(), (local_day+timedelta(days=14)).isoformat()])
    elif view == 'done': clauses.append("t.status='done'")
    elif view == 'inbox': clauses.append("t.project_id IS NULL AND t.status!='done'")
    elif view == 'open': clauses.append("t.status!='done'")
    if priority in PRIORITIES:
        clauses.append('t.priority=?'); vals.append(priority)
    if area in AREAS:
        clauses.append('t.area=?'); vals.append(area)
    if query:
        pattern='%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        clauses.append("(t.title LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\')")
        vals.extend([pattern,pattern])
    where=' AND '.join(clauses)
    total=conn.execute(f'SELECT COUNT(*) FROM life_tasks t WHERE {where}', vals).fetchone()[0]
    sort_sql={
      'due': "CASE WHEN t.due_on IS NULL THEN 1 ELSE 0 END, t.due_on, t.id DESC",
      'priority': "CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, t.due_on, t.id DESC",
      'newest': 't.id DESC',
      'oldest': 't.id ASC',
      'title': 't.title COLLATE NOCASE, t.id DESC'
    }.get(sort, 'CASE WHEN t.due_on IS NULL THEN 1 ELSE 0 END, t.due_on, t.id DESC')
    page_size=max(10,min(100,int(page_size)))
    pages=max(1,(total+page_size-1)//page_size)
    page=max(1,min(int(page),pages))
    rows=conn.execute(f"""SELECT t.*, p.name AS project_name,
            CASE WHEN t.project_id IS NULL OR p.owner_id=? OR EXISTS(
                SELECT 1 FROM life_project_members m WHERE m.project_id=t.project_id AND m.user_id=? AND m.role='editor'
            ) THEN 1 ELSE 0 END AS can_edit
            FROM life_tasks t LEFT JOIN life_projects p ON p.id=t.project_id WHERE {where}
            ORDER BY {sort_sql} LIMIT ? OFFSET ?""",(uid,uid,*vals,page_size,(page-1)*page_size)).fetchall()
    return rows,total,page,pages

def task_nodes_for(conn,uid,rows):
    from app.task_service import task_forest
    visible={t['id']:dict(t) for t in rows}
    original=set(visible)
    local_day=user_day(conn,uid).isoformat()
    for _ in range(8):
        missing={t['parent_id'] for t in visible.values() if t['parent_id'] and t['parent_id'] not in visible}
        if not missing: break
        cond,params=tasks_sql(uid)
        ancestors=conn.execute(f"SELECT t.*,p.name AS project_name FROM life_tasks t LEFT JOIN life_projects p ON p.id=t.project_id WHERE {cond} AND t.id IN ({','.join('?' for _ in missing)})",(*params,*missing)).fetchall()
        if not ancestors: break
        visible.update({r['id']:dict(r) for r in ancestors})
    roles={r['id']:r['my_role'] for r in conn.execute("SELECT p.id,CASE WHEN p.owner_id=? THEN 'owner' ELSE m.role END AS my_role FROM life_projects p LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=? WHERE p.owner_id=? OR m.user_id IS NOT NULL",(uid,uid,uid))}
    for task in visible.values():
        task['overdue']=bool(task['due_on'] and task['due_on']<local_day and task['status']!='done')
        task['can_edit']=(task['owner_id']==uid) if task['project_id'] is None else roles.get(task['project_id']) in ('owner','editor')
        task['is_context']=task['id'] not in original
    forest=task_forest(list(visible.values()))
    if visible:
        totals={r['root']:r for r in conn.execute(f"""WITH RECURSIVE family(root,id,status,project_id) AS (
            SELECT id,id,status,project_id FROM life_tasks WHERE id IN ({','.join('?' for _ in visible)})
            UNION SELECT f.root,c.id,c.status,c.project_id FROM life_tasks c JOIN family f ON c.parent_id=f.id
            WHERE c.project_id IS f.project_id AND (c.project_id IS NOT NULL OR c.owner_id=?))
            SELECT root,SUM(id!=root) AS total,SUM(id!=root AND status='done') AS done FROM family GROUP BY root""",(*visible,uid))}
        def apply(nodes):
            for node in nodes:
                if node['id'] in totals:
                    node['subtask_total']=totals[node['id']]['total'];node['subtask_done']=totals[node['id']]['done']
                apply(node['children'])
        apply(forest)
    return forest


def projects_for(conn, uid):
    return conn.execute("""
       SELECT p.*, (SELECT COUNT(*) FROM life_tasks t WHERE t.project_id=p.id) AS task_count,
          (SELECT COUNT(*) FROM life_tasks t WHERE t.project_id=p.id AND t.status='done') AS done_count,
          CASE WHEN p.owner_id=? THEN 'owner' ELSE m.role END AS my_role
       FROM life_projects p LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=?
       WHERE (p.owner_id=? OR m.user_id IS NOT NULL) AND p.status!='archived'
       ORDER BY CASE WHEN p.status='active' THEN 0 ELSE 1 END,p.updated_at DESC
    """,(uid,uid,uid)).fetchall()


def render(request, name, **kwargs):
    return templates.TemplateResponse(request, name, {"request":request, **kwargs})


@router.get("", response_class=HTMLResponse)
def home(request: Request):
    uid = user_id(request)
    with get_conn() as conn:
        local_today=user_day(conn,uid)
        from app.v37 import read_user_setup
        zone=ZoneInfo(read_user_setup(conn,uid)['timezone'])
        tasks = data_for(conn,uid,'today',limit=12)
        task_nodes=task_nodes_for(conn,uid,tasks)
        projects = projects_for(conn,uid)[:5]
        stats = conn.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done FROM life_tasks WHERE owner_id=?",(uid,)).fetchone()
        focus = conn.execute("SELECT COALESCE(SUM(minutes),0) AS total FROM life_time_entries WHERE owner_id=? AND occurred_on>=?",(uid,(local_today-timedelta(days=6)).isoformat())).fetchone()['total']
        preference = pref(conn,uid)
        is_admin=getattr(request.state,'legacy_owner',False)
        study=[];bills=[];jobs=[]
        if is_admin:
            study=conn.execute("SELECT i.id,i.title,i.type,i.due_at_utc,c.name AS course_name FROM items i JOIN courses c ON c.id=i.course_id WHERE i.status!='done' ORDER BY i.due_at_utc LIMIT 4").fetchall()
            bills=conn.execute("SELECT id,title,amount,due_at_utc FROM expenses WHERE status='unpaid' ORDER BY due_at_utc LIMIT 3").fetchall()
            jobs=conn.execute("SELECT id,company,role,followup_at_utc FROM jobs WHERE followup_at_utc IS NOT NULL ORDER BY followup_at_utc LIMIT 3").fetchall()
    from datetime import datetime
    month_start=local_today.replace(day=1)
    month_end=(month_start.replace(day=28)+timedelta(days=4)).replace(day=1)
    month_days=calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year,month_start.month)
    event_dates=set()
    with get_conn() as conn:
        for row in conn.execute("SELECT due_on FROM life_tasks WHERE owner_id=? AND due_on>=? AND due_on<? AND status!='done'",(uid,month_start.isoformat(),month_end.isoformat())):
            if row['due_on']:event_dates.add(row['due_on'])
        for row in conn.execute('SELECT start_at_utc FROM life_local_events WHERE user_id=? AND start_at_utc>=? AND start_at_utc<?',(uid,month_start.isoformat(),month_end.isoformat())):
            if row['start_at_utc']:event_dates.add(datetime.fromisoformat(row['start_at_utc'].replace('Z','+00:00')).astimezone(zone).date().isoformat())
        for row in conn.execute('SELECT e.starts_on FROM life_external_events e JOIN life_calendar_connections c ON e.connection_id=c.id WHERE c.user_id=? AND e.starts_on>=? AND e.starts_on<? LIMIT 150',(uid,month_start.isoformat(),month_end.isoformat())):
            event_dates.add(row['starts_on'])
    from app.agenda import agenda_for
    with get_conn() as conn:agenda=agenda_for(conn,uid,local_today,zone)
    hour=datetime.now(zone).hour
    greeting='Good morning' if hour<12 else 'Good afternoon' if hour<18 else 'Good evening'
    return render(request,'life_home.html',tasks=tasks,task_nodes=task_nodes,projects=projects,stats=stats,focus=focus,preference=preference,today=local_today.isoformat(),study=study,bills=bills,jobs=jobs,is_admin=is_admin,
        agenda=agenda,greeting=greeting,month_name=local_today.strftime('%B %Y'),month_number=local_today.month,month_weeks=month_days,event_dates=event_dates)



@router.post('/preferences')
def set_preferences(request: Request, experience: str=Form('simple')):
    uid=user_id(request)
    experience=pick(experience,('simple','guided','professional'),'simple')
    with get_conn() as conn:
        conn.execute("INSERT INTO life_preferences(user_id,experience,created_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET experience=excluded.experience",(uid,experience,now()))
        conn.commit()
    return redirect('/life')


@router.get('/tasks', response_class=HTMLResponse)
def tasks_page(request: Request, view: str='open', project: str='',
               q: str='', priority: str='', area: str='', sort: str='due', page: int=1):
    uid=user_id(request)
    view=pick(view,('all','open','inbox','today','upcoming','overdue','done'),'open')
    q=text_clean(q,100)
    if project and not project.isdecimal(): raise HTTPException(422,'Invalid project')
    project=int(project) if project else None
    priority=priority if priority in PRIORITIES else ''
    area=area if area in AREAS else ''
    sort=sort if sort in ('due','priority','newest','oldest','title') else 'due'
    with get_conn() as conn:
        tasks,total,page,pages=filtered_tasks(conn,uid,view,project,query=q,priority=priority,area=area,sort=sort,page=page)
        task_nodes=task_nodes_for(conn,uid,tasks)
        projects=projects_for(conn,uid)
        preference=pref(conn,uid)
        saved_views=conn.execute('SELECT id,name,query_params FROM life_task_views WHERE user_id=? ORDER BY id DESC LIMIT 20',(uid,)).fetchall()
    from urllib.parse import urlencode
    params={'view':view,'q':q,'priority':priority,'area':area,'sort':sort}
    if project is not None: params['project']=project
    query_string=urlencode({k:v for k,v in params.items() if v!=''})
    return render(request,'life_tasks.html',tasks=tasks,task_nodes=task_nodes,projects=projects,view=view,selected_project=project,
                  preference=preference,today=today(),filters=params,total=total,page=page,pages=pages,
                  query_string=query_string,priorities=PRIORITIES,areas=AREAS,saved_views=saved_views)


@router.post('/tasks/views')
def save_task_view(request:Request, name: str=Form(...), view: str=Form('open'),
                   project: str=Form(''),q: str=Form(''),priority: str=Form(''),
                   area: str=Form(''),sort: str=Form('due')):
    uid=user_id(request)
    name=text_clean(name,45)
    if not name: raise HTTPException(422,'A saved filter name is required')
    if project and not project.isdecimal():raise HTTPException(422,'Invalid project')
    with get_conn() as conn:
        if project:access(conn,uid,int(project))
        if conn.execute('SELECT COUNT(*) FROM life_task_views WHERE user_id=?',(uid,)).fetchone()[0]>=20:
            raise HTTPException(422,'Saved filter limit reached (20)')
        from urllib.parse import urlencode
        params={'view':pick(view,('all','open','inbox','today','upcoming','overdue','done'),'open'),
          'q':text_clean(q,100),'priority':priority if priority in PRIORITIES else '',
          'area':area if area in AREAS else '','sort':sort if sort in ('due','priority','newest','oldest','title') else 'due'}
        if project:params['project']=int(project)
        uri=urlencode({k:v for k,v in params.items() if v!=''})
        conn.execute('INSERT INTO life_task_views(user_id,name,query_params,created_at) VALUES(?,?,?,?)',
                     (uid,name,uri,now()))
        conn.commit()
    return redirect('/life/tasks?'+uri)


@router.post('/tasks/views/{view_id}/delete')
def delete_task_view(request:Request,view_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        conn.execute('DELETE FROM life_task_views WHERE user_id=? AND id=?',(uid,view_id))
        conn.commit()
    return redirect('/life/tasks')


@router.post('/tasks')
def create_task(request: Request, title: str=Form(...), project_id: str=Form(''),
                due_on: str=Form(''),priority: str=Form('normal'),area: str=Form('Personal'),
                description: str=Form(''), estimated_minutes: int=Form(0),recurrence: str=Form('none'),parent_id: str=Form(''),
                next_page: str=Form('/life/tasks')):
    uid=user_id(request)
    title=text_clean(title,240)
    if not title:
        raise HTTPException(422,'A task title is required')
    due=safe_day(due_on)
    priority=pick(priority,PRIORITIES,'normal')
    area=pick(area,AREAS,'Personal')
    recurrence=pick(recurrence,('none','daily','weekly','monthly'),'none')
    with get_conn() as conn:
        conn.execute('BEGIN IMMEDIATE')
        pid=int(project_id) if project_id.strip().isdigit() else None
        parent=int(parent_id) if parent_id.strip().isdigit() else None
        if pid:
            area=access(conn,uid,pid,edit=True)['area']
        if parent:
            from app.task_service import validate_parent
            validate_parent(conn,uid,None,parent,pid)
        ts=now()
        conn.execute("""INSERT INTO life_tasks(owner_id,project_id,parent_id,title,description,status,priority,area,due_on,estimated_minutes,recurrence,created_at,updated_at)
                 VALUES(?,?,?,?,?,'todo',?,?,?,?,?,?,?)""",
                 (uid,pid,parent,title,text_clean(description,10000),priority,area,due,max(0,min(100000,estimated_minutes)),recurrence,ts,ts))
        if pid:
            conn.execute('UPDATE life_projects SET updated_at=? WHERE id=?',(ts,pid))
        new_id=conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
    if request.headers.get('x-mlo-action')=='fetch':
        return JSONResponse({'ok':True,'id':new_id,'title':title,'project_id':pid,'due_on':due,'priority':priority})
    return redirect(next_page)


def next_due(due, recurrence):
    dt=date.fromisoformat(due) if due else date.today()
    if recurrence=='daily': return (dt+timedelta(days=1)).isoformat()
    if recurrence=='weekly': return (dt+timedelta(days=7)).isoformat()
    if recurrence=='monthly':
        y=dt.year+(dt.month//12); m=dt.month%12+1
        return dt.replace(year=y,month=m,day=min(dt.day,calendar.monthrange(y,m)[1])).isoformat()
    return None


@router.post('/tasks/{task_id}/status')
def change_task_status(request: Request,task_id:int,status:str=Form('done'), next_page:str=Form('/life/tasks')):
    uid=user_id(request)
    status=pick(status,STATUSES,'todo')
    from app.task_service import transition
    with get_conn() as conn:
        conn.execute('BEGIN IMMEDIATE')
        transition(conn,uid,task_id,status)
        conn.commit()
    if request.headers.get('x-mlo-action')=='fetch':
        return JSONResponse({'ok':True,'status':status})
    return redirect(next_page)


@router.post('/tasks/batch')
def batch_tasks(request: Request, ids: list[int]=Form([]), operation: str=Form('done'),
                next_page: str=Form('/life/tasks')):
    """Atomic, permission-checked multi-select editing with recurring tasks honored."""
    uid=user_id(request)
    unique=list(dict.fromkeys(ids))
    if not unique or len(unique)>100: raise HTTPException(422,'Select between 1 and 100 tasks')
    if operation not in ('done','todo','doing','blocked','high','normal','low','urgent'):
        raise HTTPException(422,'Invalid operation')
    from app.task_service import transition
    with get_conn() as conn:
        conn.execute('BEGIN IMMEDIATE')
        tasks=[task_access(conn,uid,task_id,edit=True) for task_id in unique]
        if operation in STATUSES:
            for row in tasks:
                transition(conn,uid,row['id'],operation,completing=set(unique))
        else:
            for row in tasks:
                conn.execute('UPDATE life_tasks SET priority=?,updated_at=? WHERE id=?',(operation,now(),row['id']))
        conn.commit()
    return redirect(next_page)


@router.get('/tasks/{task_id}',response_class=HTMLResponse)
def task_detail(request: Request,task_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        task=task_access(conn,uid,task_id)
        can_edit=not task['project_id'] or access(conn,uid,task['project_id'])['my_role']!='viewer'
        projects=projects_for(conn,uid)
        subs=[dict(row)|{'can_edit':can_edit} for row in conn.execute('SELECT * FROM life_tasks WHERE parent_id=? AND project_id IS ? AND (project_id IS NOT NULL OR owner_id=?) ORDER BY position,id',(task_id,task['project_id'],uid))]
        deps=conn.execute('SELECT t.id,t.title,t.status FROM life_task_dependencies d JOIN life_tasks t ON t.id=d.depends_on_id WHERE d.task_id=?',(task_id,)).fetchall()
        visible_deps=[]
        for dependency in deps:
            try: task_access(conn,uid,dependency['id']);visible_deps.append(dependency)
            except HTTPException: pass
        deps=visible_deps
        possible_dependencies=[t for t in data_for(conn,uid,'all',limit=200) if t['id'] != task_id and t['project_id']==task['project_id']]
        entries=conn.execute('SELECT * FROM life_time_entries WHERE task_id=? AND owner_id=? ORDER BY id DESC LIMIT 30',(task_id,uid)).fetchall()
        attachments=conn.execute('SELECT * FROM life_files WHERE task_id=? ORDER BY id DESC',(task_id,)).fetchall()
    return render(request,'life_task_detail.html',task=task,can_edit=can_edit,projects=projects,subs=subs,deps=deps,entries=entries,attachments=attachments,possible_dependencies=possible_dependencies)


@router.post('/tasks/{task_id}/edit')
def edit_task(request: Request,task_id:int,title:str=Form(...),description:str=Form(''),status:str=Form('todo'),priority:str=Form('normal'),due_on:str=Form(''),
              recurrence:str=Form('none'),estimated_minutes:int=Form(0)):
    uid=user_id(request)
    title=text_clean(title,240)
    if not title: raise HTTPException(422,'Task title is required')
    from app.task_service import transition
    with get_conn() as conn:
        conn.execute('BEGIN IMMEDIATE')
        task_access(conn,uid,task_id,edit=True)
        conn.execute('''UPDATE life_tasks SET title=?,description=?,priority=?,due_on=?,recurrence=?,estimated_minutes=?,updated_at=? WHERE id=?''',
            (title,text_clean(description,10000),pick(priority,PRIORITIES,'normal'),safe_day(due_on),pick(recurrence,('none','daily','weekly','monthly'),'none'),max(0,min(100000,estimated_minutes)),now(),task_id))
        transition(conn,uid,task_id,pick(status,STATUSES,'todo'))
        conn.commit()
    return redirect(f'/life/tasks/{task_id}')


@router.post('/tasks/{task_id}/delete')
def delete_task(request: Request,task_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        task_access(conn,uid,task_id,edit=True)
        conn.execute('DELETE FROM life_tasks WHERE id=?',(task_id,))
        conn.commit()
    return redirect('/life/tasks')


@router.post('/tasks/{task_id}/dependency')
def add_dependency(request: Request,task_id:int, depends_on:int=Form(...)):
    uid=user_id(request)
    with get_conn() as conn:
        task_access(conn,uid,task_id,edit=True)
        source=task_access(conn,uid,task_id,edit=True)
        target=task_access(conn,uid,depends_on)
        if source['project_id']!=target['project_id']:
            raise HTTPException(422,'Dependencies must belong to the same project')
        if task_id==depends_on: raise HTTPException(422,'Self-dependency is not allowed')
        # Detect cycles by following the transitive graph from the proposed prerequisite.
        cycle=conn.execute('''WITH RECURSIVE ancestors(id) AS (
             SELECT depends_on_id FROM life_task_dependencies WHERE task_id=?
             UNION SELECT d.depends_on_id FROM life_task_dependencies d JOIN ancestors a ON a.id=d.task_id)
             SELECT 1 FROM ancestors WHERE id=? LIMIT 1''',(depends_on,task_id)).fetchone()
        if cycle: raise HTTPException(409,'This dependency would create a cycle')
        conn.execute('INSERT OR IGNORE INTO life_task_dependencies(task_id,depends_on_id) VALUES(?,?)',(task_id,depends_on))
        conn.commit()
    return redirect(f'/life/tasks/{task_id}')


@router.get('/projects',response_class=HTMLResponse)
def project_list(request: Request):
    uid=user_id(request)
    with get_conn() as conn:
        projects=projects_for(conn,uid)
        preference=pref(conn,uid)
    return render(request,'life_projects.html',projects=projects,careers=CAREERS,preference=preference)


@router.post('/projects')
def create_project(request:Request,name:str=Form(...),area:str=Form('Personal'),template:str=Form('blank'),description:str=Form('')):
    uid=user_id(request)
    name=text_clean(name,160)
    if not name: raise HTTPException(422,'Project name is required')
    template=pick(template,CAREERS,'blank')
    area=pick(area,AREAS,CAREERS[template][2] or 'Personal')
    if template!='blank' and area=='Personal' and CAREERS[template][2]:
        area=CAREERS[template][2]
    ts=now()
    with get_conn() as conn:
        cur=conn.execute('INSERT INTO life_projects(owner_id,name,description,area,template,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                         (uid,name,text_clean(description,5000),area,template,ts,ts))
        pid=cur.lastrowid
        for n,title in enumerate(CAREERS[template][1]):
            conn.execute("""INSERT INTO life_tasks(owner_id,project_id,title,status,priority,area,position,created_at,updated_at)
                          VALUES(?,?,?,'todo','normal',?,?,?,?)""",(uid,pid,title,area,n,ts,ts))
        conn.commit()
    return redirect(f'/life/projects/{pid}')


@router.get('/projects/{project_id}',response_class=HTMLResponse)
def project_detail(request:Request,project_id:int,view:str=''):
    uid=user_id(request)
    if not view:
        from app.v37 import read_user_setup
        with get_conn() as db: view=read_user_setup(db,uid)['preferred_view']
    view=pick(view,('board','list','calendar','table'),'board')
    with get_conn() as conn:
        project=access(conn,uid,project_id)
        tasks=conn.execute('SELECT * FROM life_tasks WHERE project_id=? ORDER BY position,id',(project_id,)).fetchall()
        from app.task_service import task_forest
        task_nodes=task_forest([dict(t)|{'can_edit':project['my_role']!='viewer'} for t in tasks])
        notes=conn.execute('SELECT * FROM life_notes WHERE project_id=? ORDER BY updated_at DESC LIMIT 20',(project_id,)).fetchall()
        members=conn.execute('SELECT m.*,u.username,u.display_name FROM life_project_members m JOIN users u ON u.id=m.user_id WHERE m.project_id=?',(project_id,)).fetchall()
        minutes=conn.execute('SELECT COALESCE(SUM(minutes),0) FROM life_time_entries WHERE project_id=?',(project_id,)).fetchone()[0]
        preference=pref(conn,uid)
        records=conn.execute('SELECT * FROM life_project_records WHERE project_id=? ORDER BY status,record_type,due_on,id DESC LIMIT 150',(project_id,)).fetchall()
        attachments=conn.execute('SELECT * FROM life_files WHERE project_id=? ORDER BY id DESC',(project_id,)).fetchall()
    return render(request,'life_project_detail.html',project=project,tasks=tasks,task_nodes=task_nodes,notes=notes,members=members,minutes=minutes,view=view,preference=preference,attachments=attachments,records=records)


@router.post('/projects/{project_id}/edit')
def edit_project(request:Request,project_id:int,name:str=Form(...),description:str=Form(''),status:str=Form('active'),due_on:str=Form('')):
    uid=user_id(request)
    with get_conn() as conn:
        access(conn,uid,project_id,edit=True)
        conn.execute('UPDATE life_projects SET name=?,description=?,status=?,due_on=?,updated_at=? WHERE id=?',
          (text_clean(name,160),text_clean(description,5000),pick(status,('active','on_hold','complete','archived'),'active'),safe_day(due_on),now(),project_id))
        conn.commit()
    return redirect(f'/life/projects/{project_id}')


@router.post('/projects/{project_id}/delete')
def delete_project(request: Request, project_id: int, confirmation: str = Form(...)):
    # Only owners may remove an entire collaborative project.
    uid = user_id(request)
    with get_conn() as conn:
        project = access(conn, uid, project_id)
        if project['owner_id'] != uid:
            raise HTTPException(403, 'Only the project owner can delete it')
        if confirmation != project['name']:
            raise HTTPException(422, 'Type the exact project name to confirm deletion')
        files = conn.execute("""SELECT stored FROM life_files WHERE project_id=? OR task_id IN
          (SELECT id FROM life_tasks WHERE project_id=?) OR note_id IN
          (SELECT id FROM life_notes WHERE project_id=?)""", (project_id,project_id,project_id)).fetchall()
        conn.execute('DELETE FROM life_projects WHERE id=? AND owner_id=?',(project_id,uid))
        conn.commit()
    from app.life_files import ROOT
    for file in files:
        (ROOT/file['stored']).unlink(missing_ok=True)
    return redirect('/life/projects')


@router.post('/projects/{project_id}/records')
def new_project_record(request:Request,project_id:int,record_type:str=Form('milestone'),title:str=Form(...),
                       details:str=Form(''),severity:str=Form('medium'),due_on:str=Form('')):
    uid=user_id(request)
    title=text_clean(title,240)
    if not title:raise HTTPException(422,'A title is required')
    ts=now()
    with get_conn() as conn:
        access(conn,uid,project_id,edit=True)
        conn.execute('INSERT INTO life_project_records(project_id,created_by,record_type,title,details,severity,due_on,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
           (project_id,uid,pick(record_type,('milestone','risk','issue','decision','deliverable'),'milestone'),title,
            text_clean(details,12000),pick(severity,('low','medium','high'),'medium'),safe_day(due_on),ts,ts))
        conn.commit()
    return redirect(f'/life/projects/{project_id}')


@router.post('/projects/{project_id}/records/{record_id}/status')
def project_record_status(request:Request,project_id:int,record_id:int,status:str=Form('resolved')):
    uid=user_id(request)
    with get_conn() as conn:
        access(conn,uid,project_id,edit=True)
        result=conn.execute('UPDATE life_project_records SET status=?,updated_at=? WHERE id=? AND project_id=?',
              (pick(status,('open','monitor','resolved'),'resolved'),now(),record_id,project_id))
        if result.rowcount==0:raise HTTPException(404,'Record not found')
        conn.commit()
    return redirect(f'/life/projects/{project_id}')


@router.post('/projects/{project_id}/invite')
def invite_user(request:Request,project_id:int,username:str=Form(...),role:str=Form('editor')):
    uid=user_id(request)
    with get_conn() as conn:
        project=access(conn,uid,project_id)
        if project['my_role']!='owner': raise HTTPException(403,'Only project owners can invite people')
        other=conn.execute('SELECT id FROM users WHERE username=? COLLATE NOCASE AND approved=1 AND active=1',(text_clean(username,40),)).fetchone()
        if not other: raise HTTPException(404,'No active user with that username')
        if other['id']==uid: raise HTTPException(422,'You already own this project')
        conn.execute('INSERT INTO life_project_members(project_id,user_id,role) VALUES(?,?,?) ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role',
                     (project_id,other['id'],pick(role,('viewer','editor'),'editor')))
        conn.commit()
    return redirect(f'/life/projects/{project_id}')


@router.post('/projects/{project_id}/remove/{member_id}')
def remove_member(request:Request,project_id:int,member_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        project=access(conn,uid,project_id)
        if project['my_role']!='owner' and uid!=member_id: raise HTTPException(403,'Not allowed')
        conn.execute('DELETE FROM life_project_members WHERE project_id=? AND user_id=?',(project_id,member_id))
        conn.commit()
    return redirect(f'/life/projects/{project_id}' if uid!=member_id else '/life/projects')


@router.get('/notes',response_class=HTMLResponse)
def notes_page(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        notes=conn.execute('''SELECT n.*,p.name AS project_name FROM life_notes n
            LEFT JOIN life_projects p ON p.id=n.project_id
            LEFT JOIN life_project_members m ON m.project_id=n.project_id AND m.user_id=?
            WHERE (n.owner_id=? AND n.project_id IS NULL) OR (n.project_id IS NOT NULL AND (p.owner_id=? OR m.user_id IS NOT NULL))
            ORDER BY n.updated_at DESC LIMIT 150''',(uid,uid,uid)).fetchall()
        projects=projects_for(conn,uid)
    return render(request,'life_notes.html',notes=notes,projects=projects)


@router.post('/notes')
def new_note(request:Request,title:str=Form(...),body:str=Form(''),project_id:str=Form(''),area:str=Form('Personal')):
    uid=user_id(request)
    title=text_clean(title,200)
    if not title: raise HTTPException(422,'Note title is required')
    pid=int(project_id) if project_id.isdigit() else None
    with get_conn() as conn:
        if pid: area=access(conn,uid,pid,edit=True)['area']
        ts=now()
        cur=conn.execute('INSERT INTO life_notes(owner_id,project_id,title,body,area,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                         (uid,pid,title,text_clean(body,100000),pick(area,AREAS,'Personal'),ts,ts))
        conn.commit()
        nid=cur.lastrowid
    return redirect(f'/life/notes/{nid}')


@router.get('/notes/{note_id}',response_class=HTMLResponse)
def note_detail(request:Request,note_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        note=note_access(conn,uid,note_id)
        can_edit=not note['project_id'] or access(conn,uid,note['project_id'])['my_role']!='viewer'
        from app.v37 import read_user_setup
        zone=ZoneInfo(read_user_setup(conn,uid)['timezone'])
        reminder=conn.execute('SELECT remind_at_utc FROM life_note_reminders WHERE user_id=? AND note_id=?',(uid,note_id)).fetchone()
        review_at=datetime.fromisoformat(reminder['remind_at_utc']).astimezone(zone).strftime('%Y-%m-%dT%H:%M') if reminder else ''
        attachments=conn.execute('SELECT * FROM life_files WHERE note_id=? ORDER BY id DESC',(note_id,)).fetchall()
    return render(request,'life_note_detail.html',note=note,can_edit=can_edit,review_at=review_at,zone=zone.key,attachments=attachments)


@router.post('/notes/{note_id}/edit')
def save_note(request:Request,note_id:int,title:str=Form(...),body:str=Form('')):
    uid=user_id(request)
    with get_conn() as conn:
        note_access(conn,uid,note_id,edit=True)
        conn.execute('UPDATE life_notes SET title=?,body=?,updated_at=? WHERE id=?',
                     (text_clean(title,200),text_clean(body,100000),now(),note_id))
        conn.commit()
    return redirect(f'/life/notes/{note_id}')


@router.post('/notes/{note_id}/delete')
def delete_note(request:Request,note_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        note_access(conn,uid,note_id,edit=True)
        conn.execute('DELETE FROM life_notes WHERE id=?',(note_id,))
        conn.commit()
    return redirect('/life/notes')


@router.get('/calendar',response_class=HTMLResponse)
def calendar_page(request:Request, month:str=''):
    uid=user_id(request)
    from app.v37 import read_user_setup
    with get_conn() as db: zone=ZoneInfo(read_user_setup(db,uid)['timezone'])
    local_today=datetime.now(zone).date()
    try:
        first=date.fromisoformat(month+'-01') if month else local_today.replace(day=1)
    except ValueError: first=local_today.replace(day=1)
    first=first.replace(day=1)
    if first.year<2000 or first.year>2100: first=local_today.replace(day=1)
    last=date(first.year+(first.month//12),first.month%12+1,1)
    grouped={}
    def add(day,title,href,kind,status=''):
        if first<=day<last:
            grouped.setdefault(day.day,[]).append({'title':title,'href':href,'kind':kind,'status':status})
    def local_day(utc_value):
        try:
            ts=datetime.fromisoformat(str(utc_value).replace('Z','+00:00'))
            if ts.tzinfo is None: ts=ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(zone).date()
        except (ValueError,TypeError): return None
    is_admin=getattr(request.state,'legacy_owner',False)
    with get_conn() as conn:
        cond,params=tasks_sql(uid)
        rows=conn.execute(f'''SELECT t.id,t.title,t.status,t.due_on FROM life_tasks t
            WHERE {cond} AND t.due_on>=? AND t.due_on<? ORDER BY t.due_on,t.id LIMIT 500''',
            (*params,first.isoformat(),last.isoformat())).fetchall()
        for x in rows: add(date.fromisoformat(x['due_on']),x['title'],f'/life/tasks/{x["id"]}','task',x['status'])
        if is_admin:
            # Unique domains retain their source-of-truth records. No replicated school data.
            for x in conn.execute('''SELECT id,title,type,status,due_at_utc FROM items
                     WHERE due_at_utc>=? AND due_at_utc<? LIMIT 500''',
                     ((first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
                d=local_day(x['due_at_utc'])
                if d: add(d,x['title'],f'/items/{x["id"]}',x['type'],x['status'])
            for x in conn.execute('''SELECT id,title,kind,start_at_utc FROM events
                     WHERE start_at_utc>=? AND start_at_utc<? LIMIT 500''',
                     ((first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
                d=local_day(x['start_at_utc'])
                if d: add(d,x['title'],f'/events/{x["id"]}','event')
            for x in conn.execute('SELECT id,title,weekday,start_time_local FROM class_meetings WHERE active=1'):
                for offset in range((last-first).days):
                    d=first+timedelta(days=offset)
                    if d.weekday()==x['weekday']:
                        add(d,x['title']+' · '+x['start_time_local'],f'/classes/{x["id"]}/edit','class')
            for x in conn.execute("SELECT id,title,due_at_utc,status FROM expenses WHERE status='unpaid' AND due_at_utc>=? AND due_at_utc<?",((first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
                d=local_day(x['due_at_utc'])
                if d: add(d,x['title'],f'/expenses/{x["id"]}','bill')
            for x in conn.execute("SELECT id,company,followup_at_utc FROM jobs WHERE followup_at_utc>=? AND followup_at_utc<?",((first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
                d=local_day(x['followup_at_utc'])
                if d: add(d,'Follow up: '+x['company'],f'/jobs/{x["id"]}','job')
        # Private MLO-only events. Legacy shared events above remain admin-visible.
        for x in conn.execute('''SELECT id,title,start_at_utc FROM life_local_events
                         WHERE user_id=? AND start_at_utc>=? AND start_at_utc<? ORDER BY start_at_utc LIMIT 500''',
                         (uid,(first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
            d=local_day(x['start_at_utc'])
            if d:add(d,x['title'],f'/life/calendars/local/{x["id"]}/edit','event')
        # User-specific, previously synchronized external events. No HTTP during page loads.
        for x in conn.execute("""SELECT e.title,e.starts_on,e.starts_at,e.href,e.uid,e.connection_id,c.provider,c.label FROM life_external_events e
                      JOIN life_calendar_connections c ON c.id=e.connection_id
                      WHERE c.user_id=? AND e.starts_on>=? AND e.starts_on<? ORDER BY e.starts_on LIMIT 500""",
                      (uid,(first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
            d=local_day(x['starts_at']) if x['starts_at'] else date.fromisoformat(x['starts_on'])
            if d:add(d, x['title'], (f"/life/calendars/{x['connection_id']}/events/{urllib.parse.quote(x['uid'],safe='')}/edit" if x['provider'] in ('google','microsoft') else (x['href'] if x['href'] and x['href'].startswith('https://') else '/life/calendars')), 'external')
    for values in grouped.values():
        values.sort(key=lambda x: {'class':0,'exam':1,'assignment':2,'lab':2,'event':3,'task':4,'job':5,'bill':6}.get(x['kind'],9))
    weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(first.year,first.month)
    prev=(first-timedelta(days=1)).replace(day=1).strftime('%Y-%m')
    nxt=last.strftime('%Y-%m')
    return render(request,'life_calendar.html',month=first.strftime('%B %Y'),month_num=first.month,weeks=weeks,events=grouped,prev=prev,nxt=nxt,today=local_today.isoformat(),is_admin=is_admin)


@router.get('/goals',response_class=HTMLResponse)
def goals_page(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        goals=conn.execute('SELECT * FROM life_goals WHERE owner_id=? ORDER BY status,target_on,id DESC',(uid,)).fetchall()
        habits=conn.execute('''SELECT h.*,EXISTS(SELECT 1 FROM life_habit_days d WHERE d.habit_id=h.id AND d.day=?) AS checked,
          (SELECT COUNT(*) FROM life_habit_days d WHERE d.habit_id=h.id AND d.day>=?) AS days_7
          FROM life_habits h WHERE h.owner_id=? ORDER BY h.id DESC''',(today(),(date.today()-timedelta(days=6)).isoformat(),uid)).fetchall()
    return render(request,'life_goals.html',goals=goals,habits=habits,today=today())


@router.post('/goals')
def new_goal(request:Request,title:str=Form(...),target_on:str=Form(''),area:str=Form('Personal')):
    uid=user_id(request)
    with get_conn() as conn:
        conn.execute("INSERT INTO life_goals(owner_id,title,target_on,area,created_at) VALUES(?,?,?,?,?)",
                     (uid,text_clean(title,240),safe_day(target_on),pick(area,AREAS,'Personal'),now()))
        conn.commit()
    return redirect('/life/goals')


@router.post('/goals/{goal_id}/complete')
def complete_goal(request:Request,goal_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        conn.execute("UPDATE life_goals SET status=CASE WHEN status='complete' THEN 'active' ELSE 'complete' END WHERE id=? AND owner_id=?",(goal_id,uid))
        conn.commit()
    return redirect('/life/goals')


@router.post('/habits')
def new_habit(request:Request,title:str=Form(...),area:str=Form('Personal')):
    uid=user_id(request)
    with get_conn() as conn:
        conn.execute('INSERT INTO life_habits(owner_id,title,area,created_at) VALUES(?,?,?,?)',
                     (uid,text_clean(title,240),pick(area,AREAS,'Personal'),now()))
        conn.commit()
    return redirect('/life/goals')


@router.post('/habits/{habit_id}/check')
def check_habit(request:Request,habit_id:int):
    uid=user_id(request)
    with get_conn() as conn:
        if not conn.execute('SELECT 1 FROM life_habits WHERE id=? AND owner_id=?',(habit_id,uid)).fetchone():
            raise HTTPException(404,'Habit not found')
        if conn.execute('SELECT 1 FROM life_habit_days WHERE habit_id=? AND day=?',(habit_id,today())).fetchone():
            conn.execute('DELETE FROM life_habit_days WHERE habit_id=? AND day=?',(habit_id,today()))
        else:
            conn.execute('INSERT INTO life_habit_days(habit_id,day) VALUES(?,?)',(habit_id,today()))
        conn.commit()
    return redirect('/life/goals')


@router.get('/focus',response_class=HTMLResponse)
def focus_page(request:Request):
    uid=user_id(request)
    from app.timers import active_timer_for_user, _remaining
    with get_conn() as conn:
        tasks=data_for(conn,uid,'open',limit=100)
        entries=conn.execute('''SELECT e.*,t.title AS task_title,p.name AS project_name FROM life_time_entries e
            LEFT JOIN life_tasks t ON t.id=e.task_id LEFT JOIN life_projects p ON p.id=e.project_id
            WHERE e.owner_id=? ORDER BY e.occurred_on DESC,e.id DESC LIMIT 50''',(uid,)).fetchall()
        total=conn.execute('SELECT COALESCE(SUM(minutes),0) FROM life_time_entries WHERE owner_id=? AND occurred_on>=?',
                (uid,(date.today()-timedelta(days=6)).isoformat())).fetchone()[0]
        saved_timers=conn.execute("SELECT * FROM timers WHERE user_id=? ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END,updated_at_utc DESC LIMIT 20",(uid,)).fetchall()
    timers=[dict(x)|{'remaining':_remaining(x)} for x in saved_timers]
    return render(request,'life_focus.html',tasks=tasks,entries=entries,total=total,timers=timers,active_timer=active_timer_for_user(uid))


@router.post('/focus/log')
def log_time(request:Request,task_id:str=Form(''),minutes:int=Form(...),note:str=Form('')):
    uid=user_id(request)
    if not 0<minutes<=1440: raise HTTPException(422,'Minutes must be between 1 and 1440')
    tid=int(task_id) if task_id.isdigit() else None
    with get_conn() as conn:
        project=None
        if tid: project=task_access(conn,uid,tid)['project_id']
        conn.execute('INSERT INTO life_time_entries(owner_id,task_id,project_id,minutes,note,occurred_on,created_at) VALUES(?,?,?,?,?,?,?)',
                     (uid,tid,project,minutes,text_clean(note,300),today(),now()))
        conn.commit()
    return redirect('/life/focus')


@router.get('/search',response_class=HTMLResponse)
def search_page(request:Request,q:str=''):
    uid=user_id(request)
    q=text_clean(q,100)
    results={"tasks":[],"projects":[],"notes":[]}
    if q:
        with get_conn() as conn:
            mask='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
            cond,params=tasks_sql(uid)
            results['tasks']=conn.execute(f"SELECT t.* FROM life_tasks t WHERE {cond} AND (t.title LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\') LIMIT 50",(*params,mask,mask)).fetchall()
            results['projects']=conn.execute("""SELECT p.* FROM life_projects p LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=?
                  WHERE (p.owner_id=? OR m.user_id IS NOT NULL) AND (p.name LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\') LIMIT 50""",(uid,uid,mask,mask)).fetchall()
            results['notes']=conn.execute("""SELECT n.* FROM life_notes n LEFT JOIN life_projects p ON p.id=n.project_id LEFT JOIN life_project_members m ON m.project_id=n.project_id AND m.user_id=?
                   WHERE ((n.owner_id=? AND n.project_id IS NULL) OR (p.owner_id=? OR m.user_id IS NOT NULL))
                   AND (n.title LIKE ? ESCAPE '\\' OR n.body LIKE ? ESCAPE '\\') LIMIT 50""",(uid,uid,uid,mask,mask)).fetchall()
    return render(request,'life_search.html',q=q,results=results)


@router.get('/insights',response_class=HTMLResponse)
def insights_page(request: Request):
    uid=user_id(request)
    start=(date.today()-timedelta(days=13)).isoformat()
    with get_conn() as conn:
        summary=conn.execute("""SELECT COUNT(*) AS total,
          SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS completed,
          SUM(CASE WHEN status!='done' AND due_on<? THEN 1 ELSE 0 END) AS overdue,
          SUM(CASE WHEN status!='done' AND priority IN ('urgent','high') THEN 1 ELSE 0 END) AS high_priority
          FROM life_tasks WHERE owner_id=?""",(today(),uid)).fetchone()
        completed=conn.execute("""SELECT substr(completed_at,1,10) AS day, COUNT(*) AS n
           FROM life_tasks WHERE owner_id=? AND status='done' AND completed_at>=?
           GROUP BY substr(completed_at,1,10)""",(uid,start)).fetchall()
        focus=conn.execute("""SELECT occurred_on AS day,SUM(minutes) AS minutes
            FROM life_time_entries WHERE owner_id=? AND occurred_on>=?
            GROUP BY occurred_on""",(uid,start)).fetchall()
        project_rows=projects_for(conn,uid)
        upcoming=data_for(conn,uid,'upcoming',limit=8)
    by_completed={r['day']:r['n'] for r in completed}
    by_focus={r['day']:r['minutes'] for r in focus}
    days=[(date.today()-timedelta(days=13-i)).isoformat() for i in range(14)]
    trend=[{'day':d,'label':date.fromisoformat(d).strftime('%a %d'),
            'completed':by_completed.get(d,0),'focus':by_focus.get(d,0)} for d in days]
    max_completed=max([x['completed'] for x in trend]+[1])
    max_focus=max([x['focus'] for x in trend]+[1])
    return render(request,'life_insights.html',summary=summary,trend=trend,projects=project_rows,
       upcoming=upcoming,max_completed=max_completed,max_focus=max_focus,
       total_focus=sum(x['focus'] for x in trend),total_completed=sum(x['completed'] for x in trend))


@router.get('/export.json')
def export_data(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        payload={"format":"mlo-life-v3","generated_at":now()}
        for table in ('life_projects','life_tasks','life_notes','life_goals','life_habits','life_time_entries','life_preferences'):
            payload[table]=[dict(r) for r in conn.execute(f'SELECT * FROM {table} WHERE {"user_id" if table=="life_preferences" else "owner_id"}=?',(uid,)).fetchall()]
        payload['project_records']=[dict(r) for r in conn.execute('SELECT r.* FROM life_project_records r JOIN life_projects p ON p.id=r.project_id WHERE p.owner_id=?',(uid,)).fetchall()]
        payload['habit_days']=[dict(r) for r in conn.execute('SELECT d.* FROM life_habit_days d JOIN life_habits h ON h.id=d.habit_id WHERE h.owner_id=?',(uid,)).fetchall()]
    return Response(json.dumps(payload,indent=2,ensure_ascii=False),media_type='application/json',
         headers={'Content-Disposition':'attachment; filename="mlo-my-data.json"','Cache-Control':'no-store'})


@router.get('/export-tasks.csv')
def export_tasks_csv(request:Request):
    uid=user_id(request)
    with get_conn() as conn:
        rows=data_for(conn,uid,'all',limit=100000)
    output=io.StringIO()
    fields=['title','description','status','priority','area','due_on','recurrence','estimated_minutes','project_name']
    writer=csv.DictWriter(output,fieldnames=fields)
    writer.writeheader()
    for row in rows: writer.writerow({f:row[f] for f in fields})
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="mlo-tasks.csv"'})
