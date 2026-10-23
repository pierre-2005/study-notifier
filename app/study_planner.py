"""Private, deterministic study planning over real tasks and owned calendar records."""
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db import get_conn
from app.lifeos import user_id
from app.meta import APP_VERSION
from app.v37 import read_user_setup
from app.legacy_access import owns_legacy_data

UTC=timezone.utc
router=APIRouter(prefix='/life/study/planner',tags=['study planner'])
templates=Jinja2Templates(directory=str(Path(__file__).parent/'templates'))
templates.env.globals['APP_VERSION']=APP_VERSION


class Window(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    weekday:int=Field(ge=0,le=6)
    start:str=Field(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')
    end:str=Field(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')

    @model_validator(mode='after')
    def order(self):
        if self.start>=self.end:raise ValueError('Availability must end after it starts.')
        return self


class Preferences(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    windows:list[Window]=Field(default_factory=lambda:[Window(weekday=d,start='17:00',end='20:00') for d in range(5)],min_length=1,max_length=28)
    block_minutes:int=Field(default=50,ge=15,le=180)
    break_minutes:int=Field(default=10,ge=0,le=60)
    daily_minutes:int=Field(default=180,ge=15,le=600)
    default_minutes:int=Field(default=60,ge=15,le=1440)
    horizon_days:int=Field(default=14,ge=1,le=30)
    automatic:bool=False

    @model_validator(mode='after')
    def disjoint(self):
        for day in range(7):
            rows=sorted((w for w in self.windows if w.weekday==day),key=lambda w:w.start)
            if any(a.end>b.start for a,b in zip(rows,rows[1:])):raise ValueError('Availability windows cannot overlap.')
        return self


class Apply(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    preview_id:str=Field(pattern=r'^[a-f0-9]{32}$')


class Pin(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    pinned:bool


def init_study_schema():
    with get_conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS life_study_preferences (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          preferences_json TEXT NOT NULL, updated_at TEXT NOT NULL, last_attempt_at TEXT
        );
        CREATE TABLE IF NOT EXISTS life_study_blocks (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL,
          event_id INTEGER NOT NULL UNIQUE REFERENCES life_local_events(id) ON DELETE CASCADE,
          event_version TEXT NOT NULL, pinned INTEGER NOT NULL DEFAULT 0, revision TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS study_blocks_user ON life_study_blocks(user_id,task_id);
        CREATE TABLE IF NOT EXISTS life_study_plans (
          id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          created_at TEXT NOT NULL, expires_at TEXT NOT NULL, snapshot TEXT NOT NULL,
          plan_json TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'preview',
          before_json TEXT, after_snapshot TEXT
        );
        CREATE INDEX IF NOT EXISTS study_plans_user ON life_study_plans(user_id,created_at);
        ''')
        columns={r[1] for r in db.execute('PRAGMA table_info(life_study_preferences)')}
        if 'last_error' not in columns:db.execute('ALTER TABLE life_study_preferences ADD COLUMN last_error TEXT')
        db.commit()


def preferences(db,uid):
    row=db.execute('SELECT preferences_json FROM life_study_preferences WHERE user_id=?',(uid,)).fetchone()
    return Preferences.model_validate(json.loads(row[0])) if row else Preferences()


def stamp(value,zone):
    text=str(value)
    if len(text)==10:return datetime.combine(date.fromisoformat(text),time(),zone).astimezone(UTC)
    result=datetime.fromisoformat(text.replace('Z','+00:00'))
    return (result.replace(tzinfo=zone) if result.tzinfo is None else result).astimezone(UTC)


def valid_local(day,clock,zone):
    result=datetime.combine(day,time.fromisoformat(clock),zone)
    if (result.astimezone(UTC).astimezone(zone).replace(tzinfo=None)!=result.replace(tzinfo=None)
            or result.replace(fold=0).utcoffset()!=result.replace(fold=1).utcoffset()):return None
    return result.astimezone(UTC)


def inputs(db,uid):
    prefs=preferences(db,uid);workspace=read_user_setup(db,uid)
    tasks=[dict(r) for r in db.execute('''SELECT t.*,a.due_on AS source_due,a.due_at_utc,
          COALESCE((SELECT SUM(minutes) FROM life_time_entries WHERE task_id=t.id AND owner_id=?),0) AS logged,
          EXISTS(SELECT 1 FROM life_task_dependencies d JOIN life_tasks p ON p.id=d.depends_on_id WHERE d.task_id=t.id AND p.status!='done') AS blocked
        FROM life_tasks t LEFT JOIN life_course_assessments a ON a.task_id=t.id AND a.user_id=?
        LEFT JOIN life_projects project ON project.id=t.project_id
        LEFT JOIN life_project_members member ON member.project_id=t.project_id AND member.user_id=?
        WHERE t.owner_id=? AND t.area='Study' AND t.status!='done'
          AND (t.project_id IS NULL OR project.owner_id=? OR member.user_id IS NOT NULL)
          AND NOT EXISTS(SELECT 1 FROM life_tasks child WHERE child.parent_id=t.id AND child.project_id IS t.project_id)
        ORDER BY t.due_on IS NULL,t.due_on,CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,t.id LIMIT 201''',(uid,uid,uid,uid,uid))]
    events=[dict(r) for r in db.execute('''SELECT e.*,b.id AS block_id,b.task_id,b.pinned,b.event_version,b.revision
        FROM life_local_events e LEFT JOIN life_study_blocks b ON b.event_id=e.id AND b.user_id=e.user_id
        WHERE e.user_id=? ORDER BY e.id''',(uid,))]
    external=[dict(r) for r in db.execute('''SELECT e.*,c.provider FROM life_external_events e
        JOIN life_calendar_connections c ON c.id=e.connection_id WHERE c.user_id=? ORDER BY e.connection_id,e.uid''',(uid,))]
    classes=[];legacy_events=[]
    if owns_legacy_data(db,uid):
        classes=[dict(r) for r in db.execute('SELECT * FROM class_meetings WHERE active=1 ORDER BY id')]
        legacy_events=[dict(r) for r in db.execute('SELECT * FROM events ORDER BY id')]
    connections=[{'id':r['id'],'label':r['label'],'ready':bool(r['last_synced_at'] and not r['last_error']),
        'stale':bool(r['last_synced_at'] and stamp(r['last_synced_at'],UTC)<datetime.now(UTC)-timedelta(days=1))}
        for r in db.execute('SELECT id,label,last_synced_at,last_error FROM life_calendar_connections WHERE user_id=?',(uid,))]
    data={'connections':connections,'preferences':prefs.model_dump(),'timezone':workspace['timezone'],'day_time':workspace['day_time'],
          'tasks':tasks,'events':events,'external':external,'classes':classes,'legacy_events':legacy_events}
    data['snapshot']=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return data


def is_managed_future(event,at):
    return (event['block_id'] is not None and not event['pinned'] and event['event_version']==event['updated_at_utc']
            and stamp(event['start_at_utc'],UTC)>at)


def make_plan(data,at):
    at=at.astimezone(UTC);prefs=Preferences.model_validate(data['preferences']);zone=ZoneInfo(data['timezone'])
    if any(not c['ready'] or c['stale'] for c in data.get('connections',[])):
        raise HTTPException(409,'A connected calendar needs synchronization. Open Connected calendars, refresh it and try again.')
    first=at.astimezone(zone).date();last=first+timedelta(days=prefs.horizon_days)
    busy=[];secured={};daily={};warnings=[];windows=[]
    def reserve(start,end):
        if end>at and start<datetime.combine(last,time(),zone).astimezone(UTC):busy.append((start,end))
    for event in data['events']:
        if is_managed_future(event,at):continue
        start,end=stamp(event['start_at_utc'],UTC),stamp(event['end_at_utc'],UTC)
        reserve(start,end)
        if event['block_id'] and start>at:
            minutes=int((end-start).total_seconds()/60)
            secured.setdefault(event['task_id'],[]).append((start,end,minutes))
            day=start.astimezone(zone).date();daily[day]=daily.get(day,0)+minutes
    unknown=0
    for event in data['external']:
        if not event['is_busy']:continue
        try:
            event_zone=UTC if event['provider']=='microsoft' and not event['is_all_day'] else zone
            if event['is_all_day']:
                start=stamp(event['starts_on'],zone)
                end=stamp(str(event['ends_at'])[:10],zone) if event['ends_at'] else start+timedelta(days=1)
            elif event['ends_at']:
                start=stamp(event['starts_at'] or event['starts_on'],event_zone);end=stamp(event['ends_at'],event_zone)
            else:
                start=stamp(event['starts_on'],zone);end=stamp((date.fromisoformat(event['starts_on'])+timedelta(days=1)).isoformat(),zone);unknown+=1
            reserve(start,end)
        except (TypeError,ValueError):
            raise HTTPException(409,'A cached calendar event has an invalid date. Reconnect its calendar before planning.')
    if unknown:warnings.append(f'{unknown} cached events have no end time. Their dates are held until calendar synchronization updates them.')
    for event in data['legacy_events']:
        start=stamp(event['start_at_utc'],UTC)
        # Historical events have an optional end; reserve the day when unknown.
        end=stamp(event['end_at_utc'],UTC) if event.get('end_at_utc') else start+timedelta(days=1)
        reserve(start,end)
    for offset in range(prefs.horizon_days):
        day=first+timedelta(days=offset)
        for row in data['classes']:
            if day.weekday()!=row['weekday']:continue
            start=valid_local(day,row['start_time_local'],zone)
            end=start+timedelta(minutes=row['duration_minutes']) if start else None
            if start and end:reserve(start,end)
        for window in prefs.windows:
            if day.weekday()!=window.weekday:continue
            start,end=valid_local(day,window.start,zone),valid_local(day,window.end,zone)
            if not start or not end:
                warnings.append(f'Availability on {day.isoformat()} crosses an ambiguous or missing local time and was skipped.');continue
            windows.append((max(start,at+timedelta(minutes=15)),end))
    blocks=[];unplaced=[];tasks=[]
    if len(data['tasks'])>200:warnings.append('Only the first 200 open study tasks are planned. Complete or narrow your study workload before planning the rest.')
    for task in data['tasks'][:200]:
        if not task['due_on']:unplaced.append({'task_id':task['id'],'title':task['title'],'minutes':task['estimated_minutes'] or prefs.default_minutes,'reason':'Set a due date'});continue
        try:
            due=(stamp(task['due_at_utc'],zone) if task['source_due']==task['due_on'] and task['due_at_utc'] else
                 datetime.combine(date.fromisoformat(task['due_on']),time.fromisoformat(data['day_time']),zone).astimezone(UTC))
        except (ValueError,TypeError):
            unplaced.append({'task_id':task['id'],'title':task['title'],'minutes':task['estimated_minutes'] or prefs.default_minutes,'reason':'Check the due date'});continue
        tasks.append((due,{'urgent':0,'high':1,'normal':2,'low':3}.get(task['priority'],2),task['id'],task))
    for due,_,_,task in sorted(tasks):
        held=sum(minutes for start,end,minutes in secured.get(task['id'],[]) if end<=due)
        remaining=max(0,(task['estimated_minutes'] or prefs.default_minutes)-task['logged']-held)
        if task['status']=='blocked' or task['blocked']:
            if remaining:unplaced.append({'task_id':task['id'],'title':task['title'],'minutes':remaining,'reason':'Complete prerequisites or unblock this task'})
            continue
        for window_start,window_end in sorted(windows):
            if not remaining:break
            cursor=window_start.replace(second=0,microsecond=0)
            if cursor<window_start:cursor+=timedelta(minutes=1)
            cursor+=timedelta(minutes=(-cursor.minute)%5)
            end_limit=min(window_end,due)
            while remaining and cursor<end_limit:
                day=cursor.astimezone(zone).date();capacity=prefs.daily_minutes-daily.get(day,0)
                if capacity<min(15,remaining):break
                # Include a transition buffer around existing commitments.
                padding=timedelta(minutes=prefs.break_minutes)
                occupied=sorted((a-padding,b+padding) for a,b in busy if b+padding>cursor and a-padding<end_limit)
                crossing=next(((a,b) for a,b in occupied if a<=cursor<b),None)
                if crossing:
                    cursor=crossing[1];continue
                stop=min(end_limit,next((a for a,b in occupied if a>cursor),end_limit))
                minutes=min(remaining,prefs.block_minutes,capacity,int((stop-cursor).total_seconds()/60))
                if minutes<min(15,remaining):
                    cursor=next((b for a,b in occupied if b>cursor),end_limit);continue
                finish=cursor+timedelta(minutes=minutes)
                blocks.append({'task_id':task['id'],'title':task['title'],'start':cursor.isoformat(),'end':finish.isoformat(),'minutes':minutes})
                busy.append((cursor,finish));daily[day]=daily.get(day,0)+minutes;remaining-=minutes
                cursor=finish+padding
                if len(blocks)>500:raise HTTPException(422,'This plan exceeds 500 blocks. Reduce the planning horizon.')
        if remaining:unplaced.append({'task_id':task['id'],'title':task['title'],'minutes':remaining,'reason':'Deadline has passed' if due<=at else 'Not enough available time before the deadline'})
    return {'blocks':blocks,'unplaced':unplaced,'warnings':list(dict.fromkeys(warnings)),
            'minutes':sum(b['minutes'] for b in blocks),'timezone':data['timezone'],'created_at':at.isoformat(),
            'range_start':first.isoformat(),'range_end':(last-timedelta(days=1)).isoformat()}


def current_blocks(db,uid):
    return [dict(r) for r in db.execute('''SELECT b.*,e.title,e.start_at_utc,e.end_at_utc,e.updated_at_utc,
        t.title AS task_title FROM life_study_blocks b JOIN life_local_events e ON e.id=b.event_id
        LEFT JOIN life_tasks t ON t.id=b.task_id WHERE b.user_id=? AND e.end_at_utc>? ORDER BY e.start_at_utc''',
        (uid,datetime.now(UTC).isoformat()))]


def apply_plan(db,uid,record,at):
    if record['state']=='applied':return {'ok':True,'revision':record['id'],'created':0,'already_applied':True}
    if record['state']!='preview' or record['expires_at']<=at.isoformat():raise HTTPException(409,'Preview expired. Generate a new plan.')
    data=inputs(db,uid)
    if data['snapshot']!=record['snapshot']:raise HTTPException(409,'Tasks, availability or calendars changed. Generate a fresh preview.')
    plan=json.loads(record['plan_json']);before=[];available={};created=0
    for event in data['events']:
        if is_managed_future(event,at):
            before.append(event)
            key=(event['task_id'],stamp(event['start_at_utc'],UTC).isoformat(),stamp(event['end_at_utc'],UTC).isoformat())
            available.setdefault(key,[]).append(event)
    for block in plan['blocks']:
        if stamp(block['start'],UTC)<=at:raise HTTPException(409,'The preview includes a time that has passed. Generate a new plan.')
        version=at.isoformat();title=('Study · '+block['title'])[:220]
        key=(block['task_id'],block['start'],block['end']);matches=available.get(key,[])
        if matches:
            # Keep stable event IDs and reminder delivery history for unchanged
            # slots. Renaming a task must not generate another reminder.
            existing=matches.pop()
            db.execute('UPDATE life_local_events SET title=?,updated_at_utc=? WHERE id=? AND user_id=?',
                (title,version,existing['id'],uid))
            db.execute('UPDATE life_study_blocks SET revision=?,event_version=? WHERE id=? AND user_id=?',
                (record['id'],version,existing['block_id'],uid))
        else:
            event=db.execute('''INSERT INTO life_local_events(user_id,title,kind,start_at_utc,end_at_utc,notes,created_at_utc,updated_at_utc)
                VALUES(?,?,'study',?,?,?,?,?)''',(uid,title,block['start'],block['end'],
                f"Task: /life/tasks/{block['task_id']}",version,version))
            db.execute('INSERT INTO life_study_blocks(user_id,task_id,event_id,event_version,revision) VALUES(?,?,?,?,?)',
                (uid,block['task_id'],event.lastrowid,version,record['id']))
            created+=1
    for matches in available.values():
        for event in matches:db.execute('DELETE FROM life_local_events WHERE id=? AND user_id=?',(event['id'],uid))
    after=inputs(db,uid)['snapshot']
    db.execute("UPDATE life_study_plans SET state='applied',before_json=?,after_snapshot=? WHERE id=?",
               (json.dumps(before),after,record['id']))
    return {'ok':True,'revision':record['id'],'created':created,'planned':len(plan['blocks'])}


def preview(db,uid,at):
    data=inputs(db,uid);plan=make_plan(data,at);ident=secrets.token_hex(16)
    db.execute('DELETE FROM life_study_plans WHERE user_id=? AND created_at<?',(uid,(at-timedelta(days=30)).isoformat()))
    db.execute('INSERT INTO life_study_plans(id,user_id,created_at,expires_at,snapshot,plan_json) VALUES(?,?,?,?,?,?)',
        (ident,uid,at.isoformat(),(at+timedelta(minutes=15)).isoformat(),data['snapshot'],json.dumps(plan)))
    return ident,plan


@router.get('',response_class=HTMLResponse)
def planner_page(request:Request):
    uid=user_id(request)
    with get_conn() as db:
        prefs=preferences(db,uid).model_dump();blocks=current_blocks(db,uid);zone=ZoneInfo(read_user_setup(db,uid)['timezone'])
        latest=db.execute("SELECT id FROM life_study_plans WHERE user_id=? AND state='applied' AND created_at>? ORDER BY created_at DESC LIMIT 1",(uid,(datetime.now(UTC)-timedelta(days=1)).isoformat())).fetchone()
        status=db.execute('SELECT last_error FROM life_study_preferences WHERE user_id=?',(uid,)).fetchone()
        for block in blocks:
            block['local_start']=stamp(block['start_at_utc'],UTC).astimezone(zone).strftime('%a %b %d · %H:%M')
            block['local_end']=stamp(block['end_at_utc'],UTC).astimezone(zone).strftime('%H:%M')
            block['pinned']=bool(block['pinned'] or block['event_version']!=block['updated_at_utc'])
    return templates.TemplateResponse(request,'study_planner.html',{'request':request,'preferences':prefs,'blocks':blocks,'timezone':str(zone),
        'last_revision':latest['id'] if latest else '', 'planner_error':status['last_error'] if status else ''})


@router.put('/preferences')
def save_preferences(request:Request,body:Preferences):
    with get_conn() as db:
        db.execute('''INSERT INTO life_study_preferences(user_id,preferences_json,updated_at) VALUES(?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET preferences_json=excluded.preferences_json,updated_at=excluded.updated_at,last_attempt_at=NULL''',
            (user_id(request),json.dumps(body.model_dump()),datetime.now(UTC).isoformat()));db.commit()
    return {'ok':True}


@router.post('/preview')
def preview_plan(request:Request):
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE');ident,plan=preview(db,user_id(request),datetime.now(UTC));db.commit()
    return {'preview_id':ident,**plan}


@router.post('/apply')
def commit_plan(request:Request,body:Apply):
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        record=db.execute('SELECT * FROM life_study_plans WHERE id=? AND user_id=?',(body.preview_id,user_id(request))).fetchone()
        if not record:raise HTTPException(404,'Plan not found')
        result=apply_plan(db,user_id(request),record,datetime.now(UTC));db.commit()
    return result


@router.post('/undo')
def undo_plan(request:Request,body:Apply):
    uid=user_id(request);at=datetime.now(UTC)
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        record=db.execute('SELECT * FROM life_study_plans WHERE id=? AND user_id=?',(body.preview_id,uid)).fetchone()
        if not record:raise HTTPException(404,'Plan not found')
        if record['state']!='applied' or record['created_at']<(at-timedelta(days=1)).isoformat():raise HTTPException(409,'This plan can no longer be undone.')
        if inputs(db,uid)['snapshot']!=record['after_snapshot']:raise HTTPException(409,'Your calendar or tasks changed. Clear or edit blocks individually instead.')
        db.execute('DELETE FROM life_local_events WHERE user_id=? AND id IN (SELECT event_id FROM life_study_blocks WHERE user_id=? AND revision=?)',(uid,uid,record['id']))
        for event in json.loads(record['before_json']):
            if stamp(event['start_at_utc'],UTC)<=at:continue
            db.execute('''INSERT INTO life_local_events(id,user_id,title,kind,location,start_at_utc,end_at_utc,notes,created_at_utc,updated_at_utc)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',tuple(event[k] for k in ('id','user_id','title','kind','location','start_at_utc','end_at_utc','notes','created_at_utc','updated_at_utc')))
            prior_id=event['block_id'] if not db.execute('SELECT 1 FROM life_study_blocks WHERE id=?',(event['block_id'],)).fetchone() else None
            db.execute('INSERT INTO life_study_blocks(id,user_id,task_id,event_id,event_version,pinned,revision) VALUES(?,?,?,?,?,?,?)',
                (prior_id,uid,event['task_id'],event['id'],event['event_version'],event['pinned'],event['revision']))
        db.execute("UPDATE life_study_plans SET state='undone' WHERE id=?",(record['id'],));db.commit()
    return {'ok':True}


@router.put('/blocks/{block_id}')
def pin_block(request:Request,block_id:int,body:Pin):
    with get_conn() as db:
        result=db.execute('''UPDATE life_study_blocks SET pinned=?,event_version=(SELECT updated_at_utc FROM life_local_events WHERE id=event_id)
            WHERE id=? AND user_id=?''',(int(body.pinned),block_id,user_id(request)))
        if result.rowcount!=1:raise HTTPException(404,'Study block not found')
        db.commit()
    return {'ok':True}


@router.post('/clear')
def clear_plan(request:Request):
    uid=user_id(request);at=datetime.now(UTC)
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE');count=0
        for event in inputs(db,uid)['events']:
            if is_managed_future(event,at):
                db.execute('DELETE FROM life_local_events WHERE id=? AND user_id=?',(event['id'],uid));count+=1
        prefs=preferences(db,uid).model_copy(update={'automatic':False})
        db.execute('UPDATE life_study_preferences SET preferences_json=? WHERE user_id=?',(json.dumps(prefs.model_dump()),uid))
        db.commit()
    return {'ok':True,'removed':count}


def process_study_plans(at=None):
    at=(at or datetime.now(UTC)).astimezone(UTC);created=0
    with get_conn() as db:
        users=db.execute('''SELECT p.user_id FROM life_study_preferences p JOIN users u ON u.id=p.user_id
            WHERE u.active=1 AND u.approved=1 AND (u.requires_email_verification=0 OR u.email_verified=1)
            AND json_extract(p.preferences_json,'$.automatic')=1
            AND (p.last_attempt_at IS NULL OR p.last_attempt_at<?) ORDER BY p.last_attempt_at LIMIT 20''',((at-timedelta(minutes=15)).isoformat(),)).fetchall()
    for user in users:
        uid=user['user_id']
        try:
            with get_conn() as db:
                db.execute('BEGIN IMMEDIATE')
                if not preferences(db,uid).automatic:continue
                data=inputs(db,uid);zone=ZoneInfo(data['timezone'])
                previous=db.execute("SELECT * FROM life_study_plans WHERE user_id=? AND state='applied' ORDER BY created_at DESC LIMIT 1",(uid,)).fetchone()
                unchanged=(previous and previous['after_snapshot']==data['snapshot'] and
                    stamp(previous['created_at'],UTC).astimezone(zone).date()==at.astimezone(zone).date())
                if not unchanged:
                    ident,plan=preview(db,uid,at)
                    record=db.execute('SELECT * FROM life_study_plans WHERE id=?',(ident,)).fetchone()
                    apply_plan(db,uid,record,at);created+=len(plan['blocks'])
                db.execute('UPDATE life_study_preferences SET last_attempt_at=?,last_error=NULL WHERE user_id=?',(at.isoformat(),uid));db.commit()
        except (HTTPException,ValueError,TypeError):
            with get_conn() as db:
                db.execute('UPDATE life_study_preferences SET last_attempt_at=?,last_error=? WHERE user_id=?',
                    (at.isoformat(),'The plan could not be updated. Open Study planner to review your dates and calendars.',uid));db.commit()
    return created
