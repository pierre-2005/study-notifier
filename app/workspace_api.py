"""MLO v3.7: authenticated workspace API fitted to the existing lifeos schema.

The life_tasks table already has parent_id, position and status='doing'; do not
run the incompatible prototype migration with parent_task_id/in_progress.
All mutations rely on the signed session and existing project ACL.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict, StrictInt
from typing import Literal
from app.db import get_conn
from app.lifeos import access, task_access, user_id, now
from app.task_service import transition, validate_parent, task_forest

router = APIRouter(prefix="/api/v4", tags=["MLO interactive workspace"])
STATUSES = ("todo", "doing", "blocked", "done")
MODULE_KIND = {"tasks":"task", "projects":"project", "calendar":"event",
               "study":"study", "work":"work", "money":"bill",
               "notes":"notes", "focus":"focus"}
KINDS = set(MODULE_KIND.values()) | {"assignment", "exam", "lab"}
ALLOWED_OFFSETS = {0, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440, 2880, 4320, 10080, 20160, 43200}
DEFAULT_REMINDERS = {"task":[1440], "project":[2880], "event":[30],
                     "study":[1440], "work":[60], "bill":[4320],
                     "notes":[0], "focus":[0]}
DEFAULT_MODULES = ["tasks", "projects", "calendar"]
DEFAULT_PREFS = {"selected_modules":DEFAULT_MODULES, "timezone":"America/Edmonton",
                 "quiet_start":"22:00", "quiet_end":"07:00", "preferred_view":"board",
                 "density":"comfortable", "day_time":"09:00", "onboarding_completed":False}


def init_v37_schema():
    with get_conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS v37_workspace_preferences (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          selected_modules TEXT NOT NULL,
          timezone TEXT NOT NULL DEFAULT 'America/Edmonton',
          quiet_start TEXT NOT NULL DEFAULT '22:00',
          quiet_end TEXT NOT NULL DEFAULT '07:00',
          preferred_view TEXT NOT NULL DEFAULT 'board',
          density TEXT NOT NULL DEFAULT 'comfortable',
          onboarding_completed INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS v37_reminder_rules (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, offset_minutes INTEGER NOT NULL,
          PRIMARY KEY(user_id,kind,offset_minutes)
        );
        CREATE TABLE IF NOT EXISTS v37_board_moves (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          project_id INTEGER NOT NULL, task_id INTEGER NOT NULL,
          actor_id INTEGER NOT NULL, before_status TEXT, after_status TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS v37_task_notifications (
          user_id INTEGER NOT NULL, task_id INTEGER NOT NULL,
          device_id INTEGER NOT NULL, due_on TEXT NOT NULL,
          offset_minutes INTEGER NOT NULL, sent_at TEXT NOT NULL,
          PRIMARY KEY(user_id,task_id,device_id,due_on,offset_minutes)
        );
        CREATE INDEX IF NOT EXISTS v37_rules_user ON v37_reminder_rules(user_id,kind);
        """)
        columns = {r[1] for r in db.execute('PRAGMA table_info(v37_workspace_preferences)')}
        if 'day_time' not in columns:
            db.execute("ALTER TABLE v37_workspace_preferences ADD COLUMN day_time TEXT NOT NULL DEFAULT '09:00'")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS v37_reminder_overrides (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, PRIMARY KEY(user_id,kind)
        );
        CREATE TABLE IF NOT EXISTS life_task_successors (
          source_id INTEGER PRIMARY KEY REFERENCES life_tasks(id) ON DELETE CASCADE,
          successor_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS v37_notification_deliveries (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source TEXT NOT NULL, source_id TEXT NOT NULL,
          device_id INTEGER NOT NULL REFERENCES life_devices(id) ON DELETE CASCADE,
          deadline TEXT NOT NULL, offset_minutes INTEGER NOT NULL,
          state TEXT NOT NULL DEFAULT 'pending', lease_until TEXT, sent_at TEXT,
          attempts INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(user_id,source,source_id,device_id,deadline,offset_minutes)
        );
        CREATE TABLE IF NOT EXISTS life_note_reminders (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          note_id INTEGER NOT NULL REFERENCES life_notes(id) ON DELETE CASCADE,
          remind_at_utc TEXT NOT NULL, PRIMARY KEY(user_id,note_id)
        );
        """)
        db.commit()


def _validate_preferences(data: dict) -> dict:
    if not isinstance(data,dict):
        raise HTTPException(422,"Invalid preferences")
    modules = data.get("selected_modules", DEFAULT_MODULES)
    if not isinstance(modules,list) or not modules or len(modules)>len(MODULE_KIND) or any(not isinstance(m,str) or m not in MODULE_KIND for m in modules) or len(set(modules))!=len(modules):
        raise HTTPException(422,"Choose at least one supported module")
    zone = data.get("timezone","America/Edmonton")
    if not isinstance(zone,str) or len(zone)>80:
        raise HTTPException(422,"Invalid time zone")
    try: ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError,KeyError):
        raise HTTPException(422,"Unknown time zone")
    import re
    start,end=data.get("quiet_start","22:00"),data.get("quiet_end","07:00")
    day_time=data.get("day_time","09:00")
    if not all(isinstance(v,str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",v) for v in (start,end,day_time)):
        raise HTTPException(422,"Quiet hours must be HH:MM")
    view,density=data.get("preferred_view","board"),data.get("density","comfortable")
    if view not in ("board","list","calendar","table") or density not in ("compact","comfortable"):
        raise HTTPException(422,"Invalid display choice")
    return {"selected_modules":modules,"timezone":zone,"quiet_start":start,"quiet_end":end,
            "preferred_view":view,"density":density,"day_time":day_time,
            "onboarding_completed":bool(data.get("onboarding_completed",False))}


def _validate_reminders(value):
    if not isinstance(value,dict) or len(value)>len(KINDS):
        raise HTTPException(422,"Invalid reminder configuration")
    rules={}
    for kind, offsets in value.items():
        if kind not in KINDS or not isinstance(offsets,list) or len(offsets)>10 or len(set(map(str,offsets)))!=len(offsets) or any(type(v) is not int or v not in ALLOWED_OFFSETS for v in offsets):
            raise HTTPException(422,"Choose up to ten distinct supported reminder times")
        rules[kind]=sorted(offsets,reverse=True)
    return rules


def save_user_setup(db, uid: int, data: dict):
    prefs=_validate_preferences(data)
    # A missing reminders key means leave existing rules unchanged.
    rules = _validate_reminders(data["reminders"]) if "reminders" in data else None
    previous=db.execute('SELECT selected_modules FROM v37_workspace_preferences WHERE user_id=?',(uid,)).fetchone()
    old_modules=set(json.loads(previous['selected_modules'])) if previous else set(MODULE_KIND)
    if 'money' in prefs['selected_modules'] and db.execute("SELECT 1 FROM sqlite_master WHERE name='app_settings'").fetchone():
        from app.legacy_access import owns_legacy_data
        if not owns_legacy_data(db,uid): raise HTTPException(403,'Finance is not enabled for this account.')
    timestamp=datetime.now(timezone.utc).isoformat()
    db.execute("""INSERT INTO v37_workspace_preferences
       (user_id,selected_modules,timezone,quiet_start,quiet_end,preferred_view,density,onboarding_completed,updated_at)
       VALUES (?,?,?,?,?,?,?,?,?)
       ON CONFLICT(user_id) DO UPDATE SET selected_modules=excluded.selected_modules,
       timezone=excluded.timezone,quiet_start=excluded.quiet_start,quiet_end=excluded.quiet_end,
       preferred_view=excluded.preferred_view,density=excluded.density,
       onboarding_completed=excluded.onboarding_completed,updated_at=excluded.updated_at""",
       (uid,json.dumps(prefs["selected_modules"]),prefs["timezone"],prefs["quiet_start"],
        prefs["quiet_end"],prefs["preferred_view"],prefs["density"],int(prefs["onboarding_completed"]),timestamp))
    if 'day_time' in {r[1] for r in db.execute('PRAGMA table_info(v37_workspace_preferences)')}:
        db.execute('UPDATE v37_workspace_preferences SET day_time=? WHERE user_id=?',(prefs['day_time'],uid))
    if rules is not None:
        for kind, offsets in rules.items():
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='v37_reminder_overrides'").fetchone():
                db.execute('INSERT OR IGNORE INTO v37_reminder_overrides(user_id,kind) VALUES(?,?)',(uid,kind))
            db.execute("DELETE FROM v37_reminder_rules WHERE user_id=? AND kind=?",(uid,kind))
            db.executemany("INSERT INTO v37_reminder_rules(user_id,kind,offset_minutes) VALUES (?,?,?)",
                           [(uid,kind,v) for v in offsets])
    theme=data.get("theme")
    accent=data.get("accent_color")
    palette=data.get('palette') or {"blue":"ocean","violet":"lavender","teal":"sage","coral":"rose"}.get(accent)
    if palette is not None and palette not in ('neutral','ocean','sage','rose','amber','lavender'):
        raise HTTPException(422,'Invalid palette')
    style=data.get('palette_style','independent')
    if style not in ('independent','full'):
        raise HTTPException(422,'Invalid palette style')
    if theme in ("dark","light","system") and palette:
        db.execute("""INSERT INTO life_appearance(user_id,theme,palette,palette_style,updated_at)
             VALUES (?,?,?,?,?)
             ON CONFLICT(user_id) DO UPDATE SET theme=excluded.theme,
             palette=excluded.palette,palette_style=excluded.palette_style,
             updated_at=excluded.updated_at""",(uid,theme,palette,style,timestamp))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='life_layouts'").fetchone():
        layout=db.execute('SELECT nav_hidden,widget_hidden FROM life_layouts WHERE user_id=?',(uid,)).fetchone()
        nav_hidden=set(json.loads(layout['nav_hidden'])) if layout else set()
        widget_hidden=set(json.loads(layout['widget_hidden'])) if layout else set()
        nav_map={'tasks':'life-tasks','projects':'life-projects','calendar':'life-calendar','study':'life-studio',
                 'work':'life-work','money':'life-money','notes':'life-notes','focus':'life-focus'}
        widgets={'tasks':['tasks','capture'],'projects':['projects'],'calendar':['calendar'],'study':['study'],
                 'work':['career'],'money':['money'],'notes':[],'focus':['focus']}
        selected=set(prefs['selected_modules'])
        for module,key in nav_map.items():
            if module not in selected:
                nav_hidden.add(key);widget_hidden.update(widgets[module])
            elif module not in old_modules:
                nav_hidden.discard(key);widget_hidden.difference_update(widgets[module])
        db.execute('''INSERT INTO life_layouts(user_id,nav_hidden,widget_hidden,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET nav_hidden=excluded.nav_hidden,widget_hidden=excluded.widget_hidden,updated_at=excluded.updated_at''',
            (uid,json.dumps(sorted(nav_hidden)),json.dumps(sorted(widget_hidden)),timestamp))
    return prefs


def read_user_setup(db, uid):
    row=db.execute("SELECT * FROM v37_workspace_preferences WHERE user_id=?",(uid,)).fetchone()
    prefs=dict(DEFAULT_PREFS)
    if row:
        prefs.update({key:row[key] for key in ("timezone","quiet_start","quiet_end","preferred_view","density")})
        prefs["selected_modules"]=json.loads(row["selected_modules"])
        prefs["onboarding_completed"]=bool(row["onboarding_completed"])
    rules={kind:[] for kind in KINDS}
    for item in db.execute("SELECT kind,offset_minutes FROM v37_reminder_rules WHERE user_id=? ORDER BY offset_minutes DESC",(uid,)):
        if item["kind"] in rules: rules[item["kind"]].append(item["offset_minutes"])
    prefs["reminders"]=rules
    prefs['reminder_overrides']=[r['kind'] for r in db.execute('SELECT kind FROM v37_reminder_overrides WHERE user_id=?',(uid,))] if db.execute("SELECT 1 FROM sqlite_master WHERE name='v37_reminder_overrides'").fetchone() else []
    if row and 'day_time' in row.keys(): prefs['day_time']=row['day_time']
    appearance=db.execute('SELECT theme,palette,palette_style FROM life_appearance WHERE user_id=?',(uid,)).fetchone()
    if appearance: prefs.update(dict(appearance))
    else: prefs.update(theme='system',palette='ocean',palette_style='independent')
    return prefs


BOARD_FIELDS=('id','title','status','priority','due_on','parent_id','position','updated_at','project_id')

def board_from_rows(pid,rows):
    groups={s:[] for s in STATUSES}
    for node in task_forest([{key:r[key] for key in BOARD_FIELDS} for r in rows]):
        groups[node['status']].append(node)
    return {'project_id':pid,'total':len(rows),'columns':groups}

def project_board(db,pid):
    rows=db.execute('SELECT '+','.join(BOARD_FIELDS)+' FROM life_tasks WHERE project_id=? ORDER BY position,id',(pid,)).fetchall()
    return board_from_rows(pid,rows)


class Move(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    task_id:int=Field(gt=0)
    status:str
    before_task_id:int|None=None
    expected_updated_at:str|None=None


class Nest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    task_id:int=Field(gt=0)
    parent_id:int|None=None
    expected_updated_at:str|None=None


class Setup(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    selected_modules:list[str] = Field(default_factory=lambda:list(DEFAULT_MODULES))
    timezone:str="America/Edmonton"
    quiet_start:str="22:00"
    quiet_end:str="07:00"
    preferred_view:str="board"
    density:str="comfortable"
    day_time:str="09:00"
    palette:str|None=None
    palette_style:str="independent"
    onboarding_completed:bool=False
    reminders:dict[str,list[int]]|None=None
    theme:str|None=None
    accent_color:str|None=None


@router.get("/projects/{project_id}/board")
def board(project_id:int,request:Request):
    uid=user_id(request)
    with get_conn() as db:
        access(db,uid,project_id)
        return project_board(db,project_id)


@router.post("/projects/{project_id}/move")
def move(project_id:int,body:Move,request:Request):
    uid=user_id(request)
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        access(db,uid,project_id,edit=True)
        task=task_access(db,uid,body.task_id,edit=True)
        if task['project_id']!=project_id: raise HTTPException(404,'Task not found')
        if body.expected_updated_at and body.expected_updated_at!=task['updated_at']:
            raise HTTPException(409,'This task changed. Refresh and try again.')
        if body.before_task_id is not None:
            before=task_access(db,uid,body.before_task_id,edit=True)
            if (before['project_id']!=project_id or before['parent_id']!=task['parent_id']
                    or before['status']!=body.status or before['id']==task['id']):
                raise HTTPException(422,'Choose a different sibling in this column')
        transition(db,uid,body.task_id,body.status)
        ids=[r[0] for r in db.execute("""SELECT id FROM life_tasks WHERE project_id=?
            AND status=? AND parent_id IS ? AND id<>? ORDER BY position,id""",
            (project_id,body.status,task['parent_id'],body.task_id))]
        if body.before_task_id is None: ids.append(body.task_id)
        else: ids.insert(ids.index(body.before_task_id),body.task_id)
        for position,tid in enumerate(ids):
            db.execute('UPDATE life_tasks SET position=? WHERE id=?',(position,tid))
        db.execute('UPDATE life_tasks SET updated_at=? WHERE id=?',(now(),body.task_id))
        db.execute("""INSERT INTO v37_board_moves(project_id,task_id,actor_id,before_status,after_status,created_at)
            VALUES(?,?,?,?,?,?)""",(project_id,body.task_id,uid,task['status'],body.status,now()))
        db.commit()
        return {'ok':True,'board':project_board(db,project_id)}


@router.post("/projects/{project_id}/nest")
def nest(project_id:int,body:Nest,request:Request):
    uid=user_id(request)
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        access(db,uid,project_id,edit=True)
        task=task_access(db,uid,body.task_id,edit=True)
        if task['project_id']!=project_id: raise HTTPException(404,'Task not found')
        if body.expected_updated_at and body.expected_updated_at!=task['updated_at']:
            raise HTTPException(409,'This task changed. Refresh and try again.')
        validate_parent(db,uid,body.task_id,body.parent_id,project_id)
        position=db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM life_tasks WHERE project_id=? AND parent_id IS ?',
                            (project_id,body.parent_id)).fetchone()[0]
        db.execute('UPDATE life_tasks SET parent_id=?,position=?,updated_at=? WHERE id=?',
                   (body.parent_id,position,now(),body.task_id))
        db.commit()
        return {'ok':True,'board':project_board(db,project_id)}


@router.get("/me/setup")
def get_setup(request:Request):
    uid=user_id(request)
    with get_conn() as db:return read_user_setup(db,uid)


@router.put("/me/setup")
def put_setup(request:Request,body:Setup):
    uid=user_id(request)
    data=body.model_dump(exclude_none=True)
    with get_conn() as db:
        save_user_setup(db,uid,data)
        db.commit()
        return read_user_setup(db,uid)


@router.put("/me/reminders/{kind}")
def update_reminders(request:Request,kind:str,offsets:list[StrictInt]):
    uid=user_id(request)
    if kind not in KINDS:raise HTTPException(404,"Unknown reminder kind")
    parsed=_validate_reminders({kind:offsets})
    with get_conn() as db:
        db.execute("DELETE FROM v37_reminder_rules WHERE user_id=? AND kind=?",(uid,kind))
        db.execute("INSERT OR IGNORE INTO v37_reminder_overrides(user_id,kind) VALUES(?,?)",(uid,kind))
        db.executemany("INSERT INTO v37_reminder_rules(user_id,kind,offset_minutes) VALUES (?,?,?)",
                       [(uid,kind,v) for v in parsed[kind]])
        db.commit()
    return {"kind":kind,"offsets":parsed[kind]}


class TaskEdit(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    title:str=Field(min_length=1,max_length=240)
    description:str=Field(default='',max_length=10000)
    status:Literal['todo','doing','blocked','done']
    priority:Literal['low','normal','high','urgent']='normal'
    due_on:str|None=None
    recurrence:Literal['none','daily','weekly','monthly']='none'
    estimated_minutes:int=Field(default=0,ge=0,le=100000)
    expected_updated_at:str


@router.get('/tasks/{task_id}')
def task_preview(request:Request,task_id:int):
    uid=user_id(request)
    with get_conn() as db:
        task=task_access(db,uid,task_id)
        project=access(db,uid,task['project_id']) if task['project_id'] else None
        editable=not project or project['my_role']!='viewer'
        children=[dict(r) for r in db.execute('SELECT id,title,status FROM life_tasks WHERE parent_id=? AND project_id IS ? AND (project_id IS NOT NULL OR owner_id=?) ORDER BY position,id',
                                             (task_id,task['project_id'],uid))]
    return {'task':dict(task),'can_edit':editable,'project_name':project['name'] if project else None,'children':children}


@router.patch('/tasks/{task_id}')
def edit_task_preview(request:Request,task_id:int,body:TaskEdit):
    from app.lifeos import safe_day
    uid=user_id(request)
    if not body.title.strip():raise HTTPException(422,'Enter a task title')
    due=safe_day(body.due_on)
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        task=task_access(db,uid,task_id,edit=True)
        if task['updated_at']!=body.expected_updated_at:
            raise HTTPException(409,'This task changed elsewhere. Reopen it before saving.')
        db.execute('''UPDATE life_tasks SET title=?,description=?,priority=?,due_on=?,recurrence=?,estimated_minutes=?,updated_at=? WHERE id=?''',
                   (body.title.strip(),body.description,body.priority,due,body.recurrence,body.estimated_minutes,now(),task_id))
        transition(db,uid,task_id,body.status)
        db.commit()
    return task_preview(request,task_id)
