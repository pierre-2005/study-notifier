"""A personal canvas layout over real, permission-checked project tasks."""
import json
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from app.db import get_conn
from app.lifeos import access,user_id,now
from app.workspace_api import BOARD_FIELDS

router=APIRouter(prefix='/api/v4/projects',tags=['Task map'])
MAP_LIMIT=2000

def map_from_rows(db,uid,pid,rows,editable):
    if len(rows)>MAP_LIMIT:return {'project_id':pid,'total':len(rows),'nodes':[],'edges':[],'positions':{},'version':'','can_edit':editable,'limit':MAP_LIMIT}
    nodes=[{key:row[key] for key in BOARD_FIELDS} for row in rows];ids={n['id'] for n in nodes}
    edges=[{'from':n['parent_id'],'to':n['id'],'kind':'parent'} for n in nodes if n['parent_id'] in ids]
    edges.extend({'from':e['depends_on_id'],'to':e['task_id'],'kind':'prerequisite'} for e in db.execute('''SELECT d.* FROM life_task_dependencies d JOIN life_tasks a ON a.id=d.task_id JOIN life_tasks b ON b.id=d.depends_on_id WHERE a.project_id=? AND b.project_id=?''',(pid,pid)))
    layout=db.execute('SELECT positions_json,updated_at FROM mlo_task_map_layouts WHERE user_id=? AND project_id=?',(uid,pid)).fetchone()
    try:positions=json.loads(layout['positions_json']) if layout else {}
    except (ValueError,TypeError):positions={}
    positions={str(tid):point for tid,point in positions.items() if str(tid).isdigit() and int(tid) in ids} if isinstance(positions,dict) else {}
    return {'project_id':pid,'total':len(rows),'nodes':nodes,'edges':edges,'positions':positions,'version':layout['updated_at'] if layout else '', 'can_edit':editable}

@router.get('/{project_id}/map')
def task_map(request:Request,project_id:int):
    uid=user_id(request)
    with get_conn() as db:
        project=access(db,uid,project_id)
        rows=db.execute('SELECT '+','.join(BOARD_FIELDS)+' FROM life_tasks WHERE project_id=? ORDER BY position,id',(project_id,)).fetchall()
        return map_from_rows(db,uid,project_id,rows,project['my_role']!='viewer')

class Point(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    id:int=Field(gt=0)
    x:float=Field(ge=-1000000,le=1000000,allow_inf_nan=False)
    y:float=Field(ge=-1000000,le=1000000,allow_inf_nan=False)

class Layout(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    points:list[Point]=Field(default_factory=list,max_length=MAP_LIMIT)
    expected_version:str=Field(max_length=80)
    reset:bool=False

@router.put('/{project_id}/map/layout')
def save_layout(request:Request,project_id:int,body:Layout):
    uid=user_id(request)
    if len({p.id for p in body.points})!=len(body.points):raise HTTPException(422,'Choose each task once')
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE');access(db,uid,project_id)
        ids={row['id'] for row in db.execute('SELECT id FROM life_tasks WHERE project_id=?',(project_id,))}
        if any(p.id not in ids for p in body.points):raise HTTPException(422,'Choose tasks from this project')
        if len(ids)>MAP_LIMIT:raise HTTPException(422,'Use the list or board for projects with more than 2,000 tasks')
        old=db.execute('SELECT positions_json,updated_at FROM mlo_task_map_layouts WHERE user_id=? AND project_id=?',(uid,project_id)).fetchone()
        version=old['updated_at'] if old else ''
        if body.expected_version!=version:raise HTTPException(409,'This layout changed in another tab. Reload the map before arranging it again.')
        try:positions={} if body.reset or not old else json.loads(old['positions_json'])
        except (ValueError,TypeError):positions={}
        if not isinstance(positions,dict):positions={}
        positions={str(k):v for k,v in positions.items() if str(k).isdigit() and int(k) in ids}
        positions.update({str(p.id):{'x':p.x,'y':p.y} for p in body.points});version=now()
        db.execute('''INSERT INTO mlo_task_map_layouts(user_id,project_id,positions_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,project_id) DO UPDATE SET positions_json=excluded.positions_json,updated_at=excluded.updated_at''',(uid,project_id,json.dumps(positions,separators=(',',':')),version));db.commit()
    return {'positions':positions,'version':version}
class Relationships(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    task_id:int=Field(gt=0)
    parent_id:int|None=None
    prerequisites:list[int]=Field(default_factory=list,max_length=100)
    expected_updated_at:str=Field(min_length=1,max_length=80)

@router.post('/{project_id}/map/relationships')
def relationships(request:Request,project_id:int,body:Relationships):
    from app.lifeos import task_access
    from app.task_service import validate_parent
    uid=user_id(request)
    if len(set(body.prerequisites))!=len(body.prerequisites):raise HTTPException(422,'Choose each prerequisite once')
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE');project=access(db,uid,project_id,edit=True);source=task_access(db,uid,body.task_id,edit=True)
        if source['project_id']!=project_id:raise HTTPException(404,'Task not found')
        if source['updated_at']!=body.expected_updated_at:raise HTTPException(409,'This task changed elsewhere. Reload the map before editing its relationships.')
        validate_parent(db,uid,body.task_id,body.parent_id,project_id)
        for tid in body.prerequisites:
            target=task_access(db,uid,tid)
            if target['project_id']!=project_id or tid==body.task_id:raise HTTPException(422,'Choose a different task from this project')
            if source['status']=='done' and target['status']!='done':raise HTTPException(409,'Reopen this task before adding unfinished prerequisites')
        graph={}
        for edge in db.execute('''SELECT d.* FROM life_task_dependencies d JOIN life_tasks t ON t.id=d.task_id WHERE t.project_id=? AND d.task_id<>?''',(project_id,body.task_id)):graph.setdefault(edge['task_id'],[]).append(edge['depends_on_id'])
        graph[body.task_id]=body.prerequisites
        stack=list(body.prerequisites);seen=set()
        while stack:
            tid=stack.pop()
            if tid==body.task_id:raise HTTPException(409,'This prerequisite would create a cycle')
            if tid not in seen:seen.add(tid);stack.extend(graph.get(tid,[]))
        position=source['position']
        if source['parent_id']!=body.parent_id:position=db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM life_tasks WHERE project_id=? AND parent_id IS ?',(project_id,body.parent_id)).fetchone()[0]
        db.execute('UPDATE life_tasks SET parent_id=?,position=?,updated_at=? WHERE id=?',(body.parent_id,position,now(),body.task_id))
        db.execute('DELETE FROM life_task_dependencies WHERE task_id=?',(body.task_id,));db.executemany('INSERT INTO life_task_dependencies(task_id,depends_on_id) VALUES(?,?)',[(body.task_id,tid) for tid in body.prerequisites]);db.commit()
        rows=db.execute('SELECT '+','.join(BOARD_FIELDS)+' FROM life_tasks WHERE project_id=? ORDER BY position,id',(project_id,)).fetchall()
        return map_from_rows(db,uid,project_id,rows,project['my_role']!='viewer')
