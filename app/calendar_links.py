"""User-owned, encrypted calendar connections and event synchronization.
Google / Microsoft via OAuth2; Apple and others via trusted private ICS URLs.
An explicit sync request populates a local event cache; external APIs are never
called during ordinary dashboard/calendar rendering.
"""
from __future__ import annotations
import os, secrets, urllib.parse, ipaddress, socket
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from pathlib import Path
import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.lifeos import user_id
from app.meta import APP_VERSION

router = APIRouter(prefix='/life/calendars',tags=['calendar connections'])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent/'templates'))
templates.env.globals['APP_VERSION']=APP_VERSION
PUBLIC_URL=os.environ.get('MLO_PUBLIC_URL','').rstrip('/')
KEY=os.environ.get('MLO_CREDENTIAL_KEY','').strip()
AUTO_SYNC = os.environ.get('MLO_CALENDAR_AUTO_SYNC','true').lower() in ('1','yes','on','true')
def _bounded_int(name, default, low, high):
    try: return max(low,min(high,int(os.environ.get(name,str(default)))))
    except ValueError: return default
SYNC_MINUTES = _bounded_int('MLO_CALENDAR_SYNC_MINUTES',10,5,120)
SYNC_BATCH_SIZE = _bounded_int('MLO_CALENDAR_SYNC_BATCH_SIZE',3,1,10)
GOOGLE_ID=os.environ.get('MLO_GOOGLE_CLIENT_ID','').strip()
GOOGLE_SECRET=os.environ.get('MLO_GOOGLE_CLIENT_SECRET','').strip()
MS_ID=os.environ.get('MLO_MS_CLIENT_ID','').strip()
MS_SECRET=os.environ.get('MLO_MS_CLIENT_SECRET','').strip()
PROVIDERS={
 'google': ('https://accounts.google.com/o/oauth2/v2/auth','https://oauth2.googleapis.com/token','https://www.googleapis.com/oauth2/v3/userinfo','openid email https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events'),
 'microsoft': ('https://login.microsoftonline.com/common/oauth2/v2.0/authorize','https://login.microsoftonline.com/common/oauth2/v2.0/token','https://graph.microsoft.com/v1.0/me','openid profile email offline_access User.Read Calendars.ReadWrite')
}

def _fernet():
    if not KEY: raise HTTPException(503,'Set MLO_CREDENTIAL_KEY to enable calendar connections')
    try:return Fernet(KEY.encode())
    except (ValueError,TypeError):raise HTTPException(503,'Invalid MLO_CREDENTIAL_KEY')

def _encrypt(value):return _fernet().encrypt(value.encode()).decode()
def _decrypt(value):
    try:return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:raise HTTPException(503,'Calendar encryption key has changed; restore the original key')

def init_calendar_links_schema():
    with get_conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS life_calendar_connections (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider TEXT NOT NULL CHECK(provider IN ('google','microsoft','apple','ical')),
          label TEXT NOT NULL, external_id TEXT NOT NULL DEFAULT '',
          secret_blob TEXT NOT NULL, last_synced_at TEXT, last_error TEXT,
          created_at TEXT NOT NULL, UNIQUE(user_id,provider,external_id)
        );
        CREATE INDEX IF NOT EXISTS life_cal_connections_user ON life_calendar_connections(user_id);
        CREATE TABLE IF NOT EXISTS life_local_events (
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'meeting',
          location TEXT NOT NULL DEFAULT '', start_at_utc TEXT NOT NULL,
          end_at_utc TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
          created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS life_local_events_user_start ON life_local_events(user_id,start_at_utc);
        CREATE TABLE IF NOT EXISTS life_external_events (
          connection_id INTEGER NOT NULL REFERENCES life_calendar_connections(id) ON DELETE CASCADE,
          uid TEXT NOT NULL, title TEXT NOT NULL, starts_on TEXT NOT NULL,
          starts_at TEXT, href TEXT, calendar_name TEXT,
          PRIMARY KEY(connection_id,uid)
        );
        CREATE INDEX IF NOT EXISTS life_external_events_day ON life_external_events(starts_on);
        ''')
        columns={r[1] for r in db.execute('PRAGMA table_info(life_calendar_connections)')}
        if 'last_sync_attempt_at' not in columns:
            db.execute('ALTER TABLE life_calendar_connections ADD COLUMN last_sync_attempt_at TEXT')
        event_columns={r[1] for r in db.execute('PRAGMA table_info(life_external_events)')}
        for name,definition in (('ends_at','TEXT'),('is_all_day','INTEGER NOT NULL DEFAULT 0'),('is_busy','INTEGER NOT NULL DEFAULT 1')):
            if name not in event_columns:db.execute(f'ALTER TABLE life_external_events ADD COLUMN {name} {definition}')
        db.commit()

def _safe_ics_url(url):
    """Allowlist major provider HTTPS hosts and block direct/private IP URLs."""
    try: parts=urlparse(url)
    except ValueError:raise HTTPException(422,'Invalid subscription URL')
    host=(parts.hostname or '').lower().rstrip('.')
    safe=(host in {'calendar.google.com','outlook.live.com','outlook.office365.com','outlook.office.com',
                   'outlook.office365.us','calendar.yahoo.com','www.icloud.com'} or
          host.endswith('.icloud.com') or host.endswith('.calendar.google.com'))
    if parts.scheme!='https' or not safe or parts.username or parts.password or parts.port not in (None,443):
        raise HTTPException(422,'Use a private HTTPS iCalendar link from Google, Outlook or iCloud')
    return url

def _safe_origin(request: Request):
    if not PUBLIC_URL.startswith('https://'):
        raise HTTPException(503,'Set MLO_PUBLIC_URL to your public HTTPS address')
    return PUBLIC_URL+'/life/calendars/callback'

def _client(provider):
    cid,secret=(GOOGLE_ID,GOOGLE_SECRET) if provider=='google' else (MS_ID,MS_SECRET)
    if not cid or not secret:raise HTTPException(503,f'{provider.title()} OAuth is not configured')
    _fernet()
    return cid,secret

def _request(method,url,**kwargs):
    try:
        response=requests.request(method,url,timeout=15,allow_redirects=False,**kwargs)
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        raise RuntimeError(f'Provider request failed: {type(exc).__name__}') from exc

def _oauth_exchange(provider, data):
    r=_request('POST',PROVIDERS[provider][1],data=data).json()
    if 'access_token' not in r:raise RuntimeError('Provider did not return an access token')
    return r

@router.get('',response_class=HTMLResponse)
def connections_page(request: Request, notice: str=''):
    uid=user_id(request)
    with get_conn() as db:
        rows=[dict(row) for row in db.execute('SELECT id,provider,label,last_synced_at,last_error,secret_blob FROM life_calendar_connections WHERE user_id=? ORDER BY id DESC',(uid,)).fetchall()]
    for row in rows:
        row['can_edit']=False
        if row['provider'] in ('google','microsoft'):
            try:
                scopes=json_load(_decrypt(row['secret_blob'])).get('scope','').split()
                needed='https://www.googleapis.com/auth/calendar.events' if row['provider']=='google' else 'Calendars.ReadWrite'
                row['can_edit']=needed in scopes
            except (HTTPException,ValueError,KeyError): pass
        # Never pass encrypted credentials to the rendered template.
        del row['secret_blob']
    origin_ready=PUBLIC_URL.startswith('https://')
    google_missing=[key for key,present in [('MLO_PUBLIC_URL (public HTTPS address)',origin_ready),('MLO_CREDENTIAL_KEY',bool(KEY)),('MLO_GOOGLE_CLIENT_ID',bool(GOOGLE_ID)),('MLO_GOOGLE_CLIENT_SECRET',bool(GOOGLE_SECRET))] if not present]
    ms_missing=[key for key,present in [('MLO_PUBLIC_URL (public HTTPS address)',origin_ready),('MLO_CREDENTIAL_KEY',bool(KEY)),('MLO_MS_CLIENT_ID',bool(MS_ID)),('MLO_MS_CLIENT_SECRET',bool(MS_SECRET))] if not present]
    # This flag controls help text only, not any authorization decision.
    is_admin=request.state.current_user['role']=='admin'
    return templates.TemplateResponse(request,'life_calendar_connections.html',{'request':request,'connections':rows,'notice':notice,'google_ready':not google_missing,'microsoft_ready':not ms_missing,'feed_ready':bool(KEY),'google_missing':google_missing,'microsoft_missing':ms_missing,'is_admin':is_admin,'auto_sync':AUTO_SYNC,'sync_minutes':SYNC_MINUTES})

@router.get('/connect/{provider}')
def connect(request: Request, provider: str):
    user_id(request)
    if provider not in PROVIDERS:raise HTTPException(404)
    redirect_uri=_safe_origin(request)
    cid,_=_client(provider)
    state=secrets.token_urlsafe(32)
    request.session['calendar_oauth']={'state':state,'provider':provider,'uid':user_id(request)}
    args={'client_id':cid,'redirect_uri':redirect_uri,'response_type':'code',
          'scope':PROVIDERS[provider][3],'state':state,'access_type':'offline'}
    if provider=='google':args.update({'prompt':'consent select_account','include_granted_scopes':'true'})
    else:args.update({'prompt':'select_account'})
    return RedirectResponse(PROVIDERS[provider][0]+'?'+urllib.parse.urlencode(args),status_code=303)

@router.get('/callback')
def callback(request:Request,state:str='',code:str='',error:str=''):
    uid=user_id(request)
    pending=request.session.pop('calendar_oauth',None)
    if error:raise HTTPException(400,'Calendar permission was declined')
    if not pending or pending['uid']!=uid or not secrets.compare_digest(str(pending['state']),state) or not code:
        raise HTTPException(403,'Invalid or expired calendar authorization')
    provider=pending['provider']
    cid,client_secret=_client(provider)
    token=_oauth_exchange(provider,{'code':code,'client_id':cid,'client_secret':client_secret,
                                     'redirect_uri':_safe_origin(request),'grant_type':'authorization_code'})
    token['_expires_at']=datetime.now(timezone.utc).timestamp()+int(token.get('expires_in',3600))
    info=_request('GET',PROVIDERS[provider][2],headers={'Authorization':'Bearer '+token['access_token']}).json()
    identity=str(info.get('email') or info.get('mail') or info.get('userPrincipalName') or info.get('id') or '').lower()[:200]
    if not identity:raise HTTPException(502,'Calendar account identity was not returned')
    with get_conn() as db:
        existing=db.execute('SELECT id,secret_blob FROM life_calendar_connections WHERE user_id=? AND provider=? AND external_id=?',(uid,provider,identity)).fetchone()
        if existing and 'refresh_token' not in token:
            old=json_load(_decrypt(existing['secret_blob']))
            token['refresh_token']=old.get('refresh_token','')
        blob=_encrypt(json_dump(token))
        db.execute('''INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at)
           VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,provider,external_id) DO UPDATE SET secret_blob=excluded.secret_blob,label=excluded.label,last_error=NULL''',
          (uid,provider,identity,identity,blob,datetime.now(timezone.utc).isoformat()))
        db.commit()
    return RedirectResponse('/life/calendars?notice=connected',status_code=303)

def json_dump(x):
    import json
    return json.dumps(x)
def json_load(x):
    import json
    return json.loads(x)

@router.post('/feed')
def add_feed(request:Request,provider:str=Form('ical'),label:str=Form(...),url:str=Form(...)):
    uid=user_id(request)
    if provider not in ('apple','ical'):raise HTTPException(422,'Choose Apple or iCalendar')
    url=_safe_ics_url(url.strip())
    label=label.strip()[:90]
    if not label:raise HTTPException(422,'A calendar name is required')
    with get_conn() as db:
        cur=db.execute('INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at) VALUES(?,?,?,?,?,?)',
          (uid,provider,label,secrets.token_hex(10),_encrypt(json_dump({'url':url})),datetime.now(timezone.utc).isoformat()))
        added_id=cur.lastrowid
        db.commit()
    return RedirectResponse('/life/calendars?notice=added',status_code=303)

def _token(provider,token,connection_id):
    if not token.get('refresh_token'):
        return token['access_token']
    if datetime.now(timezone.utc).timestamp() < token.get('_expires_at',0)-90:
        return token['access_token']
    cid,secret=_client(provider)
    fresh=_oauth_exchange(provider,{'client_id':cid,'client_secret':secret,'grant_type':'refresh_token','refresh_token':token['refresh_token'],'scope':PROVIDERS[provider][3]})
    token.update(fresh)
    token['_expires_at']=datetime.now(timezone.utc).timestamp()+int(fresh.get('expires_in',3600))
    with get_conn() as db:
        db.execute('UPDATE life_calendar_connections SET secret_blob=? WHERE id=?',(_encrypt(json_dump(token)),connection_id))
        db.commit()
    return token['access_token']

def _date(value):
    if not value:return None
    return str(value)[:10]

def _get_events(provider, token, connection_id):
    access=_token(provider,token,connection_id)
    head={'Authorization':'Bearer '+access}
    start=(date.today()-timedelta(days=35)).isoformat()+'T00:00:00Z'
    end=(date.today()+timedelta(days=185)).isoformat()+'T23:59:59Z'
    result=[]
    def pages(url,params,key,headers):
        for _ in range(40):
            data=_request('GET',url,headers=headers,params=params).json()
            yield data.get(key,[])
            token=data.get('nextPageToken') if provider=='google' else data.get('@odata.nextLink')
            if not token:return
            if provider=='google':params={**params,'pageToken':token}
            else:
                target=urllib.parse.urlsplit(token)
                if target.scheme!='https' or target.netloc!='graph.microsoft.com':raise RuntimeError('Invalid calendar pagination URL')
                url=token;params={}
        raise RuntimeError('Calendar has too many pages to synchronize safely')
    if provider=='google':
        lists=pages('https://www.googleapis.com/calendar/v3/users/me/calendarList',{'maxResults':80},'items',head)
    else:
        lists=pages('https://graph.microsoft.com/v1.0/me/calendars',{'$top':60},'value',head)
    count=0
    for group in lists:
        for cal in group:
            calid=cal.get('id')
            if not calid:continue
            count+=1
            if count>60:raise RuntimeError('Connect an account with at most 60 calendars')
            if provider=='google':
                url='https://www.googleapis.com/calendar/v3/calendars/'+urllib.parse.quote(calid,safe='')+'/events'
                batches=pages(url,{'timeMin':start,'timeMax':end,'maxResults':250,'singleEvents':'true','orderBy':'startTime'},'items',head)
            else:
                url='https://graph.microsoft.com/v1.0/me/calendars/'+urllib.parse.quote(calid,safe='')+'/calendarView'
                batches=pages(url,{'startDateTime':start,'endDateTime':end,'$top':200},'value',{**head,'Prefer':'outlook.timezone="UTC"'})
            for batch in batches:
                for x in batch:
                    if x.get('status')=='cancelled' or x.get('isCancelled'):continue
                    d=x.get('start',{});finish=x.get('end',{});all_day=False
                    if provider=='google':
                        stamp=d.get('dateTime') or d.get('date');end_stamp=finish.get('dateTime') or finish.get('date')
                        all_day='date' in d;busy=x.get('transparency')!='transparent'
                    else:
                        stamp=d.get('dateTime','');end_stamp=finish.get('dateTime');all_day=bool(x.get('isAllDay'));busy=x.get('showAs')!='free'
                        # Graph returns UTC as requested, commonly without a suffix.
                        if stamp and datetime.fromisoformat(stamp.replace('Z','+00:00')).tzinfo is None:stamp+='Z'
                        if end_stamp and datetime.fromisoformat(end_stamp.replace('Z','+00:00')).tzinfo is None:end_stamp+='Z'
                    if stamp:result.append((str(calid)+':'+x['id'],x.get('summary',x.get('subject','Untitled event'))[:220],_date(stamp),stamp,x.get('htmlLink',x.get('webLink','')),cal.get('summary',cal.get('name','Calendar'))[:90],end_stamp,int(all_day),int(busy)))
                    if len(result)>10000:raise RuntimeError('Too many calendar events to synchronize safely')
    return result

def _get_ics_events(encrypted):
    from icalendar import Calendar
    from app.calendar_recurrence import expand_feed
    info=json_load(_decrypt(encrypted))
    url=_safe_ics_url(info['url'])
    resp=_request('GET',url,headers={'User-Agent':'MLO Calendar/3.7','Accept':'text/calendar'})
    if len(resp.content)>3_000_000:raise RuntimeError('Calendar feed is too large')
    return expand_feed(Calendar.from_ical(resp.content),datetime.now(timezone.utc))

def sync_one_connection(connection_id:int):
    # Refresh credentials privately without deleting valid cached events on failure.
    attempt=datetime.now(timezone.utc).isoformat()
    with get_conn() as db:
        conn=db.execute('SELECT * FROM life_calendar_connections WHERE id=?',(connection_id,)).fetchone()
        if conn:
            db.execute('UPDATE life_calendar_connections SET last_sync_attempt_at=? WHERE id=?',(attempt,connection_id))
            db.commit()
    if not conn:return False
    try:
        if conn['provider'] in ('google','microsoft'):
            events=_get_events(conn['provider'],json_load(_decrypt(conn['secret_blob'])),connection_id)
        else:
            events=_get_ics_events(conn['secret_blob'])
        with get_conn() as db:
            # A user can disconnect an account while the API call is in progress.
            if not db.execute('SELECT id FROM life_calendar_connections WHERE id=?',(connection_id,)).fetchone():return False
            db.execute('DELETE FROM life_external_events WHERE connection_id=?',(connection_id,))
            db.executemany('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at,href,calendar_name,ends_at,is_all_day,is_busy) VALUES(?,?,?,?,?,?,?,?,?,?)',
                           ((connection_id,*e,*( (None,0,1) if len(e)==6 else () )) for e in events if e[2]))
            db.execute('UPDATE life_calendar_connections SET last_synced_at=?,last_error=NULL WHERE id=?',
                       (datetime.now(timezone.utc).isoformat(),connection_id))
            db.commit()
        return True
    except (RuntimeError,ValueError,KeyError,ImportError,HTTPException,requests.RequestException) as exc:
        with get_conn() as db:
            db.execute('UPDATE life_calendar_connections SET last_error=? WHERE id=?',
                       (('Reauthorize account' if isinstance(exc,HTTPException) and exc.status_code in (401,403) else str(exc))[:150],connection_id))
            db.commit()
        return False


def sync_due_calendars():
    # Rate-limit automatic provider refreshes and bound background workload.
    if not AUTO_SYNC or not KEY:return 0
    threshold=(datetime.now(timezone.utc)-timedelta(minutes=SYNC_MINUTES)).isoformat()
    with get_conn() as db:
        due=db.execute('''SELECT id FROM life_calendar_connections
             WHERE last_sync_attempt_at IS NULL OR last_sync_attempt_at < ?
             ORDER BY COALESCE(last_sync_attempt_at,'') ASC LIMIT ?''',(threshold,SYNC_BATCH_SIZE)).fetchall()
    for row in due:
        sync_one_connection(row['id'])
    return len(due)


@router.post('/{connection_id}/sync')
def sync_connection(request:Request,connection_id:int):
    # Retained for backwards compatibility, not needed for routine use.
    uid=user_id(request)
    _owned_connection(uid,connection_id)
    ok=sync_one_connection(connection_id)
    return RedirectResponse('/life/calendars?notice='+('synced' if ok else 'error'),status_code=303)

@router.post('/{connection_id}/delete')
def disconnect(request:Request,connection_id:int):
    uid=user_id(request)
    with get_conn() as db:
        db.execute('DELETE FROM life_calendar_connections WHERE id=? AND user_id=?',(connection_id,uid))
        db.commit()
    return RedirectResponse('/life/calendars?notice=disconnected',status_code=303)

# External changes are explicit user actions. Ordinary calendar page loads only
# read the local cache, never write to or fetch from provider APIs.
def _owned_connection(uid, connection_id, *, writable=False):
    with get_conn() as db:
        connection=db.execute('SELECT * FROM life_calendar_connections WHERE id=? AND user_id=?',
                              (connection_id,uid)).fetchone()
    if not connection:raise HTTPException(404,'Calendar connection not found')
    if writable and connection['provider'] not in ('google','microsoft'):
        raise HTTPException(403,'This calendar is a read-only subscription')
    return connection

def _provider_headers(connection):
    provider=connection['provider']
    token=json_load(_decrypt(connection['secret_blob']))
    scopes=token.get('scope','').split()
    # Older connections were created with read-only permissions. Require an
    # explicit re-authorization, not a surprising permission escalation.
    needed='https://www.googleapis.com/auth/calendar.events' if provider=='google' else 'Calendars.ReadWrite'
    if needed not in scopes:
        raise HTTPException(409,'Reconnect this calendar account to grant event editing permission')
    return {'Authorization':'Bearer '+_token(provider,token,connection['id'])}

def _available_calendars(connection):
    headers=_provider_headers(connection)
    if connection['provider']=='google':
        calendars=_request('GET','https://www.googleapis.com/calendar/v3/users/me/calendarList',
                           headers=headers,params={'maxResults':100}).json().get('items',[])
        return [{'id':c['id'],'name':c.get('summary','Calendar')} for c in calendars
                if c.get('id') and c.get('accessRole') in ('owner','writer')]
    calendars=_request('GET','https://graph.microsoft.com/v1.0/me/calendars',
                        headers=headers,params={'$top':100}).json().get('value',[])
    return [{'id':c['id'],'name':c.get('name','Calendar')} for c in calendars
            if c.get('id') and c.get('canEdit',True)]

def _user_zone(uid):
    with get_conn() as db:
        prefs=db.execute('SELECT timezone FROM v37_workspace_preferences WHERE user_id=?',(uid,)).fetchone()
    from app.config import settings
    return ZoneInfo(prefs['timezone'] if prefs else settings.timezone)


def _validate_event(title,start,end,zone=None):
    title=title.strip()
    if not title or len(title)>220:raise HTTPException(422,'Enter a title (up to 220 characters)')
    try:
        zone=zone or ZoneInfo(os.environ.get('TIMEZONE','UTC'))
        start_dt=datetime.fromisoformat(start)
        end_dt=datetime.fromisoformat(end)
        def local(value):
            if value.tzinfo is not None:return value
            aware=value.replace(tzinfo=zone)
            if (aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=value
                    or aware.replace(fold=0).utcoffset()!=aware.replace(fold=1).utcoffset()):raise ValueError()
            return aware
        start_dt,end_dt=local(start_dt),local(end_dt)
        if end_dt<=start_dt:raise ValueError()
        if (end_dt-start_dt)>timedelta(days=14):raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise HTTPException(422,'Check the start/end dates and make sure end is after start')
    return title,start_dt,end_dt

def _event_payload(provider,title,start,end):
    if provider=='google':
        return {'summary':title,'start':{'dateTime':start.isoformat()},
                'end':{'dateTime':end.isoformat()}}
    start_utc=start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    end_utc=end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    return {'subject':title,'start':{'dateTime':start_utc,'timeZone':'UTC'},
            'end':{'dateTime':end_utc,'timeZone':'UTC'}}

def _api_event_url(provider,calendar_id,event_id=None):
    cal=urllib.parse.quote(calendar_id,safe='')
    if provider=='google':
        result='https://www.googleapis.com/calendar/v3/calendars/'+cal+'/events'
    else:
        result='https://graph.microsoft.com/v1.0/me/calendars/'+cal+'/events'
    return result+('/'+urllib.parse.quote(event_id,safe='') if event_id else '')

def _existing_event(uid, connection, event_uid):
    with get_conn() as db:
        event=db.execute('SELECT * FROM life_external_events WHERE connection_id=? AND uid=?',
                         (connection['id'],event_uid)).fetchone()
    if not event:raise HTTPException(404,'Synchronized event not found')
    if ':' not in event_uid:raise HTTPException(422,'This event cannot be edited')
    return event,event_uid.rsplit(':',1)

def _cache_changed(connection,calendar_id,event_data):
    provider=connection['provider']
    event_id=event_data.get('id')
    if not event_id:return
    stamp=(event_data.get('start',{}).get('dateTime') if provider=='google' else
           event_data.get('start',{}).get('dateTime'))
    if not stamp:return
    # Graph timestamps are UTC because writes explicitly use UTC.
    if provider=='microsoft' and datetime.fromisoformat(stamp.replace('Z','+00:00')).tzinfo is None:stamp+='Z'
    finish=event_data.get('end',{}).get('dateTime')
    if provider=='microsoft' and finish and datetime.fromisoformat(finish.replace('Z','+00:00')).tzinfo is None:finish+='Z'
    title=event_data.get('summary' if provider=='google' else 'subject','Untitled')[:220]
    with get_conn() as db:
        db.execute('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at,href,calendar_name,ends_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(connection_id,uid) DO UPDATE SET title=excluded.title,starts_on=excluded.starts_on,starts_at=excluded.starts_at,href=excluded.href,ends_at=excluded.ends_at',
                   (connection['id'],calendar_id+':'+event_id,title,_date(stamp),stamp,
                    event_data.get('htmlLink' if provider=='google' else 'webLink',''),connection['label'],finish))
        db.commit()

def _my_writable_accounts(uid):
    with get_conn() as db:
        records=db.execute("SELECT id,provider,label,secret_blob FROM life_calendar_connections WHERE user_id=? AND provider IN ('google','microsoft') ORDER BY provider,label",(uid,)).fetchall()
    result=[]
    for r in records:
        scopes=set()
        try:scopes=set(json_load(_decrypt(r['secret_blob'])).get('scope','').split())
        except (HTTPException,ValueError,KeyError):pass
        allowed=('https://www.googleapis.com/auth/calendar.events' if r['provider']=='google' else 'Calendars.ReadWrite') in scopes
        result.append({'id':r['id'],'provider':r['provider'],'label':r['label'],'can_edit':allowed})
    return result


@router.get('/new', response_class=HTMLResponse)
def choose_event_destination(request: Request):
    uid=user_id(request)
    return templates.TemplateResponse(request,'life_event_destination.html',
       {'request':request,'connections':_my_writable_accounts(uid),
        'is_admin':request.state.current_user['role']=='admin',
        'tz':str(_user_zone(uid))})


@router.get('/{connection_id}/calendars.json')
def account_calendars(request:Request,connection_id:int):
    connection=_owned_connection(user_id(request),connection_id,writable=True)
    try:return {'calendars':_available_calendars(connection)}
    except (RuntimeError,KeyError,ValueError) as exc:
        raise HTTPException(502,'Calendar provider unavailable; retry in a moment') from exc


@router.post('/new')
def create_unified_event(request:Request,destination:str=Form(...),calendar_id:str=Form(''),
                         title:str=Form(...),start:str=Form(...),end:str=Form(...),
                         kind:str=Form('meeting'),location:str=Form(''),notes:str=Form('')):
    uid=user_id(request)
    title,start_dt,end_dt=_validate_event(title,start,end,_user_zone(uid))
    if destination=='mlo':
        now=datetime.now(timezone.utc).isoformat()
        with get_conn() as db:
            db.execute('''INSERT INTO life_local_events(user_id,title,kind,location,start_at_utc,end_at_utc,notes,created_at_utc,updated_at_utc)
                       VALUES(?,?,?,?,?,?,?,?,?)''',(uid,title,kind[:40],location[:240],start_dt.astimezone(timezone.utc).isoformat(),
                                                  end_dt.astimezone(timezone.utc).isoformat(),notes[:4000],now,now))
            db.commit()
        return RedirectResponse('/life/calendar?notice=event-created',status_code=303)
    if not destination.startswith('external:'):raise HTTPException(422,'Choose a destination')
    try:connection_id=int(destination.split(':',1)[1])
    except ValueError:raise HTTPException(422,'Choose a valid calendar account')
    connection=_owned_connection(uid,connection_id,writable=True)
    calendars=_available_calendars(connection)
    if not calendar_id or calendar_id not in {c['id'] for c in calendars}:
        raise HTTPException(422,'Choose a writable calendar')
    payload=_event_payload(connection['provider'],title,start_dt,end_dt)
    data=_request('POST',_api_event_url(connection['provider'],calendar_id),
                  headers={**_provider_headers(connection),'Content-Type':'application/json'},json=payload).json()
    _cache_changed(connection,calendar_id,data)
    # If provider accepted creation but omitted start in response, update through
    # the next background refresh. Do not create a duplicate local event.
    return RedirectResponse('/life/calendar?notice=event-created',status_code=303)


@router.get('/local/{event_id}/edit',response_class=HTMLResponse)
def edit_local_event_page(request:Request,event_id:int):
    uid=user_id(request)
    with get_conn() as db:
        event=db.execute('SELECT * FROM life_local_events WHERE id=? AND user_id=?',(event_id,uid)).fetchone()
    if not event:raise HTTPException(404,'Event not found')
    zone=_user_zone(uid)
    def local(stamp):return datetime.fromisoformat(stamp).astimezone(zone).strftime('%Y-%m-%dT%H:%M')
    return templates.TemplateResponse(request,'life_local_event_form.html',{
        'request':request,'event':event,'local_start':local(event['start_at_utc']),
        'local_end':local(event['end_at_utc'])})


@router.post('/local/{event_id}/edit')
def update_local_event(request:Request,event_id:int,title:str=Form(...),start:str=Form(...),end:str=Form(...),
                       kind:str=Form('meeting'),location:str=Form(''),notes:str=Form('')):
    uid=user_id(request)
    title,start_dt,end_dt=_validate_event(title,start,end,_user_zone(user_id(request)))
    with get_conn() as db:
        cur=db.execute('''UPDATE life_local_events SET title=?,kind=?,location=?,start_at_utc=?,end_at_utc=?,notes=?,updated_at_utc=?
                          WHERE id=? AND user_id=?''',(title,kind[:40],location[:240],start_dt.astimezone(timezone.utc).isoformat(),
                          end_dt.astimezone(timezone.utc).isoformat(),notes[:4000],datetime.now(timezone.utc).isoformat(),event_id,uid))
        if cur.rowcount!=1:raise HTTPException(404,'Event not found')
        db.commit()
    return RedirectResponse('/life/calendar?notice=event-updated',status_code=303)


@router.post('/local/{event_id}/delete')
def delete_local_event(request:Request,event_id:int,confirm:str=Form(...)):
    uid=user_id(request)
    if confirm!='DELETE':raise HTTPException(422,'Type DELETE to confirm')
    with get_conn() as db:
        cur=db.execute('DELETE FROM life_local_events WHERE id=? AND user_id=?',(event_id,uid))
        if cur.rowcount!=1:raise HTTPException(404,'Event not found')
        db.commit()
    return RedirectResponse('/life/calendar?notice=event-deleted',status_code=303)


@router.get('/{connection_id}/events/new',response_class=HTMLResponse)
def new_event_page(request:Request,connection_id:int):
    connection=_owned_connection(user_id(request),connection_id,writable=True)
    calendars=_available_calendars(connection)
    return templates.TemplateResponse(request,'life_external_event_form.html',
        {'connection':connection,'calendars':calendars,'event':None,'event_uid':None})

@router.post('/{connection_id}/events/new')
def new_event(request:Request,connection_id:int,calendar_id:str=Form(...),title:str=Form(...),
              start:str=Form(...),end:str=Form(...)):
    connection=_owned_connection(user_id(request),connection_id,writable=True)
    calendars=_available_calendars(connection)
    if calendar_id not in {c['id'] for c in calendars}:
        raise HTTPException(422,'Select a writable calendar')
    title,start_dt,end_dt=_validate_event(title,start,end,_user_zone(user_id(request)))
    body=_event_payload(connection['provider'],title,start_dt,end_dt)
    data=_request('POST',_api_event_url(connection['provider'],calendar_id),
                  headers={**_provider_headers(connection),'Content-Type':'application/json'},json=body).json()
    _cache_changed(connection,calendar_id,data)
    return RedirectResponse('/life/calendars?notice=event-created',status_code=303)

@router.get('/{connection_id}/events/{event_uid}/edit',response_class=HTMLResponse)
def edit_event_page(request:Request,connection_id:int,event_uid:str):
    connection=_owned_connection(user_id(request),connection_id,writable=True)
    cached,(calendar_id,event_id)=_existing_event(user_id(request),connection,event_uid)
    headers=_provider_headers(connection)
    event=_request('GET',_api_event_url(connection['provider'],calendar_id,event_id),headers=({**headers,'Prefer':'outlook.timezone="UTC"'} if connection['provider']=='microsoft' else headers)).json()
    start_obj=event.get('start',{})
    end_obj=event.get('end',{})
    if not start_obj.get('dateTime') or not end_obj.get('dateTime'):
        raise HTTPException(422,'All-day events are not editable in MLO yet; edit this event in its source calendar')
    zone=_user_zone(user_id(request))
    def local_datetime(v):
        raw=v.get('dateTime','')
        if raw.endswith('Z'):raw=raw[:-1]+'+00:00'
        d=datetime.fromisoformat(raw)
        if d.tzinfo is None:
            # Graph calendar data is requested with the UTC preference below.
            d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(zone).strftime('%Y-%m-%dT%H:%M')
    return templates.TemplateResponse(request,'life_external_event_form.html',
         {'connection':connection,'calendars':[], 'event':{'title':event.get('summary' if connection['provider']=='google' else 'subject',''),
          'start':local_datetime(start_obj),'end':local_datetime(end_obj),'calendar_id':calendar_id},'event_uid':event_uid})

@router.post('/{connection_id}/events/{event_uid}/edit')
def edit_event(request:Request,connection_id:int,event_uid:str,title:str=Form(...),start:str=Form(...),end:str=Form(...)):
    connection=_owned_connection(user_id(request),connection_id,writable=True)
    cached,(calendar_id,event_id)=_existing_event(user_id(request),connection,event_uid)
    title,start_dt,end_dt=_validate_event(title,start,end,_user_zone(user_id(request)))
    data=_request('PATCH',_api_event_url(connection['provider'],calendar_id,event_id),
                  headers={**_provider_headers(connection),'Content-Type':'application/json'},
                  json=_event_payload(connection['provider'],title,start_dt,end_dt)).json()
    _cache_changed(connection,calendar_id,data)
    return RedirectResponse('/life/calendar?notice=event-updated',status_code=303)

@router.post('/{connection_id}/events/{event_uid}/delete')
def delete_event(request:Request,connection_id:int,event_uid:str,confirm:str=Form(...)):
    connection=_owned_connection(user_id(request),connection_id,writable=True)
    cached,(calendar_id,event_id)=_existing_event(user_id(request),connection,event_uid)
    if confirm!='DELETE':raise HTTPException(422,'Type DELETE to confirm')
    _request('DELETE',_api_event_url(connection['provider'],calendar_id,event_id),
             headers=_provider_headers(connection))
    with get_conn() as db:
        db.execute('DELETE FROM life_external_events WHERE connection_id=? AND uid=?',(connection_id,event_uid))
        db.commit()
    return RedirectResponse('/life/calendar?notice=event-deleted',status_code=303)
