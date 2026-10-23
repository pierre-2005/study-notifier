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
from pydantic import BaseModel, Field
from app.db import get_conn
from app.lifeos import access, task_access, user_id, now, next_due

router = APIRouter(prefix="/api/v37", tags=["MLO interactive workspace"])
STATUSES = ("todo", "doing", "blocked", "done")
MODULE_KIND = {"tasks":"task", "projects":"project", "calendar":"event",
               "study":"study", "work":"work", "money":"bill",
               "notes":"notes", "focus":"focus"}
KINDS = set(MODULE_KIND.values()) | {"assignment", "exam", "lab"}
ALLOWED_OFFSETS = {0, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440, 2880, 4320, 10080, 20160, 43200}
DEFAULT_REMINDERS = {"task":[1440], "project":[2880], "event":[30],
                     "study":[1440], "work":[60], "bill":[4320],
                     "notes":[1440], "focus":[15]}
DEFAULT_MODULES = ["tasks", "projects", "calendar"]
DEFAULT_PREFS = {"selected_modules":DEFAULT_MODULES, "timezone":"America/Edmonton",
                 "quiet_start":"22:00", "quiet_end":"07:00", "preferred_view":"board",
                 "density":"comfortable", "onboarding_completed":False}


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
        db.commit()


def _validate_preferences(data: dict) -> dict:
    if not isinstance(data,dict):
        raise HTTPException(422,"Invalid preferences")
    modules = data.get("selected_modules", DEFAULT_MODULES)
    if not isinstance(modules,list) or not modules or len(modules)>len(MODULE_KIND) or len(set(modules))!=len(modules) or any(m not in MODULE_KIND for m in modules):
        raise HTTPException(422,"Choose at least one supported module")
    zone = data.get("timezone","America/Edmonton")
    if not isinstance(zone,str) or len(zone)>80:
        raise HTTPException(422,"Invalid time zone")
    try: ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError,KeyError):
        raise HTTPException(422,"Unknown time zone")
    import re
    start,end=data.get("quiet_start","22:00"),data.get("quiet_end","07:00")
    if not all(isinstance(v,str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",v) for v in (start,end)):
        raise HTTPException(422,"Quiet hours must be HH:MM")
    view,density=data.get("preferred_view","board"),data.get("density","comfortable")
    if view not in ("board","list","calendar","table") or density not in ("compact","comfortable"):
        raise HTTPException(422,"Invalid display choice")
    return {"selected_modules":modules,"timezone":zone,"quiet_start":start,"quiet_end":end,
            "preferred_view":view,"density":density,
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
    if rules is not None:
        for kind, offsets in rules.items():
            db.execute("DELETE FROM v37_reminder_rules WHERE user_id=? AND kind=?",(uid,kind))
            db.executemany("INSERT INTO v37_reminder_rules(user_id,kind,offset_minutes) VALUES (?,?,?)",
                           [(uid,kind,v) for v in offsets])
    theme=data.get("theme")
    accent=data.get("accent_color")
    palette={"blue":"ocean","violet":"lavender","teal":"sage","coral":"rose"}.get(accent)
    if theme in ("dark","light","system") and palette:
        db.execute("""INSERT INTO life_appearance(user_id,theme,palette,palette_style,updated_at)
             VALUES (?,?,?,'independent',?)
             ON CONFLICT(user_id) DO UPDATE SET theme=excluded.theme,
             palette=excluded.palette,palette_style=excluded.palette_style,
             updated_at=excluded.updated_at""",(uid,theme,palette,timestamp))
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
    return prefs


def project_board(db, pid):
    rows=[dict(x) for x in db.execute("""SELECT id,title,status,parent_id,position,due_on,priority,owner_id
         FROM life_tasks WHERE project_id=? ORDER BY position,id""",(pid,))]
    nodes={r["id"]:{**r,"children":[],"subtask_done":0,"subtask_total":0} for r in rows}
    groups={s:[] for s in STATUSES}
    for row in rows:
        node=nodes[row["id"]]
        parent=nodes.get(row["parent_id"])
        if parent and parent["id"]!=row["id"]:parent["children"].append(node)
        else:groups[row["status"]].append(node)
    def progress(node,seen):
        if node["id"] in seen:return (0,0)
        seen=seen|{node["id"]}
        total=done=0
        for child in node["children"]:
            a,b=progress(child,seen)
            total+=1+a;done+=int(child["status"]=="done")+b
        node["subtask_total"]=total;node["subtask_done"]=done
        return total,done
    for group in groups.values():
        for node in group:progress(node,set())
    return {"project_id":pid,"total":len(rows),"columns":groups}


class Move(BaseModel):
    task_id:int=Field(gt=0)
    status:str
    before_task_id:int|None=None


class Nest(BaseModel):
    task_id:int=Field(gt=0)
    parent_id:int|None=None


class Setup(BaseModel):
    selected_modules:list[str] = Field(default_factory=lambda:list(DEFAULT_MODULES))
    timezone:str="America/Edmonton"
    quiet_start:str="22:00"
    quiet_end:str="07:00"
    preferred_view:str="board"
    density:str="comfortable"
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
    if body.status not in STATUSES:raise HTTPException(422,"Invalid status")
    with get_conn() as db:
        access(db,uid,project_id,edit=True)
        task=task_access(db,uid,body.task_id,edit=True)
        if task["project_id"]!=project_id or task["parent_id"] is not None:
            raise HTTPException(422,"Only root tasks in this project can be moved")
        if body.before_task_id is not None:
            before=task_access(db,uid,body.before_task_id,edit=True)
            if before["project_id"]!=project_id or before["parent_id"] is not None or before["status"]!=body.status:
                raise HTTPException(422,"Invalid drop target")
        if body.status=="done" and task["status"]!="done":
            blocked=db.execute("""SELECT 1 FROM life_task_dependencies d
                   JOIN life_tasks t ON t.id=d.depends_on_id
                   WHERE d.task_id=? AND t.status!='done' LIMIT 1""",(body.task_id,)).fetchone()
            if blocked:raise HTTPException(409,"Finish prerequisites first")
        try:
            db.execute("BEGIN IMMEDIATE")
            prior=task["status"]
            when=now()
            db.execute("UPDATE life_tasks SET status=?,completed_at=?,updated_at=? WHERE id=?",
                       (body.status,when if body.status=="done" else None,when,body.task_id))
            from app.consolidation import mirror_legacy_status
            mirror_legacy_status(db,body.task_id,body.status)
            if body.status=="done" and prior!="done" and task["recurrence"]!="none":
                due=next_due(task["due_on"],task["recurrence"])
                db.execute("""INSERT INTO life_tasks(owner_id,project_id,parent_id,title,description,status,priority,area,due_on,estimated_minutes,recurrence,created_at,updated_at)
                    VALUES(?,?,?,?,?,'todo',?,?,?,?,?,?,?)""",
                    (task["owner_id"],project_id,None,task["title"],task["description"],task["priority"],task["area"],due,task["estimated_minutes"],task["recurrence"],when,when))
            ids=[r[0] for r in db.execute("""SELECT id FROM life_tasks WHERE project_id=? AND status=? AND parent_id IS NULL AND id<>? ORDER BY position,id""",
                                            (project_id,body.status,body.task_id))]
            if body.before_task_id is not None and body.before_task_id!=body.task_id and body.before_task_id in ids:
                ids.insert(ids.index(body.before_task_id),body.task_id)
            else:ids.append(body.task_id)
            for n,tid in enumerate(ids):
                db.execute("UPDATE life_tasks SET position=? WHERE id=?",(n,tid))
            db.execute("""INSERT INTO v37_board_moves(project_id,task_id,actor_id,before_status,after_status,created_at)
                          VALUES (?,?,?,?,?,?)""",(project_id,body.task_id,uid,prior,body.status,when))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        return {"ok":True, "board":project_board(db,project_id)}


@router.post("/projects/{project_id}/nest")
def nest(project_id:int,body:Nest,request:Request):
    uid=user_id(request)
    with get_conn() as db:
        access(db,uid,project_id,edit=True)
        task=task_access(db,uid,body.task_id,edit=True)
        if task["project_id"]!=project_id:raise HTTPException(404,"Task not found")
        if body.parent_id is not None:
            if body.parent_id==body.task_id:raise HTTPException(422,"Cannot nest into itself")
            parent=task_access(db,uid,body.parent_id,edit=True)
            if parent["project_id"]!=project_id:raise HTTPException(422,"Parent must belong to this project")
            seen={body.task_id}
            current=body.parent_id
            while current is not None:
                if current in seen:raise HTTPException(409,"Circular task hierarchy")
                seen.add(current)
                if len(seen)>9:raise HTTPException(422,"Maximum nesting depth is eight")
                current=task_access(db,uid,current)["parent_id"]
        db.execute("UPDATE life_tasks SET parent_id=?,updated_at=? WHERE id=?",
                   (body.parent_id,now(),body.task_id))
        db.commit()
        return {"ok":True,"board":project_board(db,project_id)}


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
def update_reminders(request:Request,kind:str,offsets:list[int]):
    uid=user_id(request)
    if kind not in KINDS:raise HTTPException(404,"Unknown reminder kind")
    parsed=_validate_reminders({kind:offsets})
    with get_conn() as db:
        db.execute("DELETE FROM v37_reminder_rules WHERE user_id=? AND kind=?",(uid,kind))
        db.executemany("INSERT INTO v37_reminder_rules(user_id,kind,offset_minutes) VALUES (?,?,?)",
                       [(uid,kind,v) for v in parsed[kind]])
        db.commit()
    return {"kind":kind,"offsets":parsed[kind]}
