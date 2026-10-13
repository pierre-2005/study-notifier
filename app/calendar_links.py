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
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.lifeos import user_id
from app.meta import APP_VERSION

router = APIRouter(prefix='/life/calendars',tags=['calendar connections'])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent/'templates'))
templates.env.globals['APP_VERSION']=APP_VERSION
PUBLIC_URL=os.environ.get('MLO_PUBLIC_URL','').rstrip('/')
KEY=os.environ.get('MLO_CREDENTIAL_KEY','').strip()
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
        CREATE TABLE IF NOT EXISTS life_external_events (
          connection_id INTEGER NOT NULL REFERENCES life_calendar_connections(id) ON DELETE CASCADE,
          uid TEXT NOT NULL, title TEXT NOT NULL, starts_on TEXT NOT NULL,
          starts_at TEXT, href TEXT, calendar_name TEXT,
          PRIMARY KEY(connection_id,uid)
        );
        CREATE INDEX IF NOT EXISTS life_external_events_day ON life_external_events(starts_on);
        ''')
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
    return templates.TemplateResponse(request,'life_calendar_connections.html',{'request':request,'connections':rows,'notice':notice,'google_ready':not google_missing,'microsoft_ready':not ms_missing,'feed_ready':bool(KEY),'google_missing':google_missing,'microsoft_missing':ms_missing,'is_admin':is_admin})

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
        db.execute('INSERT INTO life_calendar_connections(user_id,provider,label,external_id,secret_blob,created_at) VALUES(?,?,?,?,?,?)',
          (uid,provider,label,secrets.token_hex(10),_encrypt(json_dump({'url':url})),datetime.now(timezone.utc).isoformat()))
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
    if provider=='google':
        lists=_request('GET','https://www.googleapis.com/calendar/v3/users/me/calendarList',headers=head,params={'maxResults':80}).json().get('items',[])
        for cal in lists[:30]:
            calid=cal.get('id')
            if not calid:continue
            url='https://www.googleapis.com/calendar/v3/calendars/'+urllib.parse.quote(calid,safe='')+'/events'
            items=_request('GET',url,headers=head,params={'timeMin':start,'timeMax':end,'maxResults':250,'singleEvents':'true','orderBy':'startTime'}).json().get('items',[])
            for x in items:
                d=x.get('start',{})
                stamp=d.get('dateTime') or d.get('date')
                if stamp:result.append((str(calid)+':'+x['id'],x.get('summary','Untitled event')[:220],_date(stamp),stamp,x.get('htmlLink',''),cal.get('summary','Calendar')[:90]))
    else:
        lists=_request('GET','https://graph.microsoft.com/v1.0/me/calendars',headers=head,params={'$top':60}).json().get('value',[])
        for cal in lists[:30]:
            calid=cal.get('id')
            if not calid:continue
            url='https://graph.microsoft.com/v1.0/me/calendars/'+urllib.parse.quote(calid,safe='')+'/calendarView'
            items=_request('GET',url,headers={**head,'Prefer':'outlook.timezone="UTC"'},params={'startDateTime':start,'endDateTime':end,'$top':200}).json().get('value',[])
            for x in items:
                stamp=x.get('start',{}).get('dateTime','')
                if stamp:result.append((str(calid)+':'+x['id'],x.get('subject','Untitled event')[:220],_date(stamp),stamp,x.get('webLink',''),cal.get('name','Calendar')[:90]))
    return result

def _get_ics_events(encrypted):
    from icalendar import Calendar
    info=json_load(_decrypt(encrypted))
    url=_safe_ics_url(info['url'])
    resp=_request('GET',url,headers={'User-Agent':'MLO Calendar/3.2','Accept':'text/calendar'})
    if len(resp.content)>3_000_000:raise RuntimeError('Calendar feed is too large')
    cal=Calendar.from_ical(resp.content)
    result=[]
    for component in cal.walk('VEVENT'):
        event_id=str(component.get('UID',secrets.token_hex(8)))
        raw=component.get('DTSTART')
        if raw is None:continue
        dt=raw.dt
        stamp=dt.isoformat()
        day=_date(stamp)
        if day:
            result.append((event_id,str(component.get('SUMMARY','Untitled event'))[:220],day,stamp,'','Subscribed calendar'))
        if len(result)>=1000:break
    return result

@router.post('/{connection_id}/sync')
def sync_connection(request:Request,connection_id:int):
    uid=user_id(request)
    with get_conn() as db:
        connection=db.execute('SELECT * FROM life_calendar_connections WHERE id=? AND user_id=?',(connection_id,uid)).fetchone()
    if not connection:raise HTTPException(404,'Calendar connection not found')
    try:
        token=json_load(_decrypt(connection['secret_blob']))
        if connection['provider'] in ('google','microsoft'):
            events=_get_events(connection['provider'],token,connection_id)
        else:
            events=_get_ics_events(connection['secret_blob'])
        with get_conn() as db:
            db.execute('DELETE FROM life_external_events WHERE connection_id=?',(connection_id,))
            db.executemany('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at,href,calendar_name) VALUES(?,?,?,?,?,?,?)',
                  ((connection_id,*event) for event in events if event[2]))
            db.execute('UPDATE life_calendar_connections SET last_synced_at=?,last_error=NULL WHERE id=?',(datetime.now(timezone.utc).isoformat(),connection_id))
            db.commit()
        return RedirectResponse('/life/calendars?notice=synced',status_code=303)
    except (RuntimeError,ValueError,KeyError,HTTPException) as exc:
        with get_conn() as db:
            db.execute('UPDATE life_calendar_connections SET last_error=? WHERE id=?',(str(exc)[:150],connection_id))
            db.commit()
        return RedirectResponse('/life/calendars?notice=error',status_code=303)

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

def _validate_event(title,start,end):
    title=title.strip()
    if not title or len(title)>220:raise HTTPException(422,'Enter a title (up to 220 characters)')
    try:
        zone=ZoneInfo(os.environ.get('TIMEZONE','UTC'))
        start_dt=datetime.fromisoformat(start)
        end_dt=datetime.fromisoformat(end)
        if start_dt.tzinfo is None:start_dt=start_dt.replace(tzinfo=zone)
        if end_dt.tzinfo is None:end_dt=end_dt.replace(tzinfo=zone)
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
    if provider=='microsoft' and not stamp.endswith('Z'):stamp+='Z'
    title=event_data.get('summary' if provider=='google' else 'subject','Untitled')[:220]
    with get_conn() as db:
        db.execute('INSERT INTO life_external_events(connection_id,uid,title,starts_on,starts_at,href,calendar_name) VALUES(?,?,?,?,?,?,?) ON CONFLICT(connection_id,uid) DO UPDATE SET title=excluded.title,starts_on=excluded.starts_on,starts_at=excluded.starts_at,href=excluded.href',
                   (connection['id'],calendar_id+':'+event_id,title,_date(stamp),stamp,
                    event_data.get('htmlLink' if provider=='google' else 'webLink',''),connection['label']))
        db.commit()

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
    title,start_dt,end_dt=_validate_event(title,start,end)
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
    zone=ZoneInfo(os.environ.get('TIMEZONE','UTC'))
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
    title,start_dt,end_dt=_validate_event(title,start,end)
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
