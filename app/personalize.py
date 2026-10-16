"""Per-account interface layout. All requested keys are server-validated."""
import json
import os
from urllib.parse import urlparse
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.db import get_conn
from app.lifeos import user_id
from app.workspace import list_sections_for_user

router = APIRouter(prefix='/life/layout', tags=['interface'])
NAV = ('life-home','life-tasks','life-projects','life-calendar','life-focus',
       'life-notes','life-insights','life-goals','life-search','life-devices','life-import',
       'life-studio','life-work','life-money','life-spaces')
WIDGETS = ('welcome','calendar','capture','tasks','focus','projects','study','money','career','numbers')
DEFAULT_WIDGETS = list(WIDGETS)


def init_layout_schema():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS life_layouts (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            nav_order TEXT NOT NULL DEFAULT '[]', widget_order TEXT NOT NULL DEFAULT '[]',
            nav_labels TEXT NOT NULL DEFAULT '{}', nav_hidden TEXT NOT NULL DEFAULT '[]',
            widget_hidden TEXT NOT NULL DEFAULT '[]', widget_sizes TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL)''')
        # Older v3.2 database installs get the width column without losing saved layouts.
        columns={row['name'] for row in conn.execute('PRAGMA table_info(life_layouts)').fetchall()}
        if 'widget_sizes' not in columns:
            conn.execute("ALTER TABLE life_layouts ADD COLUMN widget_sizes TEXT NOT NULL DEFAULT '{}'")
        conn.execute("""CREATE TABLE IF NOT EXISTS life_appearance (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            theme TEXT NOT NULL DEFAULT 'system',
            palette TEXT NOT NULL DEFAULT 'neutral',
            palette_style TEXT NOT NULL DEFAULT 'independent',
            updated_at TEXT NOT NULL
        )""")
        conn.commit()


def _safe_json(raw, default):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def layout_for(uid):
    with get_conn() as conn:
        row=conn.execute('SELECT * FROM life_layouts WHERE user_id=?',(uid,)).fetchone()
    if not row:
        return {'nav_order': list(NAV),'widget_order':list(WIDGETS), 'nav_labels':{},'nav_hidden':[], 'widget_hidden':[], 'widget_sizes':{}}
    return {key:_safe_json(row[key], {} if key in ('nav_labels','widget_sizes') else []) for key in ('nav_order','widget_order','nav_labels','nav_hidden','widget_hidden','widget_sizes')}


def allowed_nav(uid):
    sections=list_sections_for_user(uid, sidebar_only=True)
    return list(NAV) + [f'section:{int(s["id"])}' for s in sections]


def _order(value, allowed):
    if not isinstance(value,list):
        raise HTTPException(422,'An ordered list is required')
    result=[]
    for key in value:
        if isinstance(key,str) and key in allowed and key not in result:
            result.append(key)
    return result + [key for key in allowed if key not in result]


@router.get('')
def read_layout(request:Request):
    uid=user_id(request)
    data=layout_for(uid)
    data['nav_order']=_order(data['nav_order'],allowed_nav(uid))
    data['widget_order']=_order(data['widget_order'],list(WIDGETS))
    return JSONResponse(data, headers={'Cache-Control':'private, no-store'})


@router.post('')
async def save_layout(request:Request):
    uid=user_id(request)
    origin=request.headers.get('origin')
    allowed_hosts={request.headers.get('host','').lower(), urlparse(os.getenv('MLO_PUBLIC_URL','')).netloc.lower()}
    if origin and urlparse(origin).netloc.lower() not in allowed_hosts:
        raise HTTPException(403,'Cross-origin update rejected')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403,'Cross-site update rejected')
    if request.headers.get('content-type','').split(';',1)[0] != 'application/json':
        raise HTTPException(415,'JSON required')
    body=await request.body()
    if len(body)>12000:raise HTTPException(413,'Layout is too large')
    try: data=json.loads(body)
    except (TypeError,ValueError):raise HTTPException(422,'Invalid JSON')
    if not isinstance(data,dict):raise HTTPException(422,'Invalid layout')
    nav=allowed_nav(uid)
    nav_order=_order(data.get('nav_order',[]),nav)
    widgets=_order(data.get('widget_order',[]),list(WIDGETS))
    labels=data.get('nav_labels',{})
    if not isinstance(labels,dict):raise HTTPException(422,'Invalid labels')
    labels={k:v.strip()[:36] for k,v in labels.items() if k in nav and isinstance(v,str) and v.strip()}
    nav_hidden=[k for k in data.get('nav_hidden',[]) if k in nav] if isinstance(data.get('nav_hidden'),list) else []
    widget_hidden=[k for k in data.get('widget_hidden',[]) if k in WIDGETS] if isinstance(data.get('widget_hidden'),list) else []
    raw_sizes=data.get('widget_sizes',{})
    if not isinstance(raw_sizes,dict):raise HTTPException(422,'Invalid widget widths')
    widget_sizes={k:int(v) for k,v in raw_sizes.items() if k in WIDGETS and str(v) in ('4','6','8','12')}
    with get_conn() as conn:
        conn.execute('''INSERT INTO life_layouts(user_id,nav_order,widget_order,nav_labels,nav_hidden,widget_hidden,widget_sizes,updated_at)
          VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET nav_order=excluded.nav_order,
          widget_order=excluded.widget_order,nav_labels=excluded.nav_labels,nav_hidden=excluded.nav_hidden,
          widget_hidden=excluded.widget_hidden,widget_sizes=excluded.widget_sizes,updated_at=excluded.updated_at''',
          (uid,json.dumps(nav_order),json.dumps(widgets),json.dumps(labels),json.dumps(nav_hidden),json.dumps(widget_hidden),json.dumps(widget_sizes),datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return {'ok':True}


# Private appearance settings are authoritative across Windows PWA and browsers.
VALID_THEMES = {'system', 'light', 'dark'}
VALID_PALETTES = {'neutral', 'ocean', 'sage', 'rose', 'amber', 'lavender'}
VALID_PALETTE_STYLES = {'independent', 'full'}
DEFAULT_APPEARANCE = {'theme': 'system', 'palette': 'neutral', 'palette_style': 'independent'}

def appearance_for(uid):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT theme, palette, palette_style FROM life_appearance WHERE user_id=?', (uid,)
        ).fetchone()
    if not row:
        return dict(DEFAULT_APPEARANCE)
    return {
        'theme': row['theme'] if row['theme'] in VALID_THEMES else 'system',
        'palette': row['palette'] if row['palette'] in VALID_PALETTES else 'neutral',
        'palette_style': row['palette_style'] if row['palette_style'] in VALID_PALETTE_STYLES else 'independent',
    }

@router.get('/appearance')
def read_appearance(request: Request):
    return JSONResponse(appearance_for(user_id(request)), headers={'Cache-Control': 'private, no-store'})

@router.post('/appearance')
async def save_appearance(request: Request):
    uid = user_id(request)
    origin = request.headers.get('origin')
    allowed_hosts = {request.headers.get('host','').lower(), urlparse(os.getenv('MLO_PUBLIC_URL','')).netloc.lower()}
    if origin and urlparse(origin).netloc.lower() not in allowed_hosts:
        raise HTTPException(403, 'Cross-origin update rejected')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Cross-site update rejected')
    if request.headers.get('content-type','').split(';',1)[0] != 'application/json':
        raise HTTPException(415, 'JSON required')
    raw = await request.body()
    if len(raw) > 500:
        raise HTTPException(413, 'Appearance settings are too large')
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise HTTPException(422, 'Invalid JSON')
    if not isinstance(data, dict) or set(data) != set(DEFAULT_APPEARANCE):
        raise HTTPException(422, 'Missing or unexpected appearance settings')
    if (not all(isinstance(data[key], str) for key in DEFAULT_APPEARANCE)
            or data['theme'] not in VALID_THEMES or data['palette'] not in VALID_PALETTES
            or data['palette_style'] not in VALID_PALETTE_STYLES):
        raise HTTPException(422, 'Invalid appearance choice')
    with get_conn() as conn:
        conn.execute(
            '''INSERT INTO life_appearance(user_id, theme, palette, palette_style, updated_at)
            VALUES (?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
              theme=excluded.theme, palette=excluded.palette,
              palette_style=excluded.palette_style, updated_at=excluded.updated_at''',
            (uid, data['theme'], data['palette'], data['palette_style'], datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    return JSONResponse({'ok': True}, headers={'Cache-Control': 'private, no-store'})
