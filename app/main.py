from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
import calendar
import os
import secrets
import urllib.parse
from starlette.middleware.sessions import SessionMiddleware
from app.finance.routes import router as finance_router
from app.finance.db import init_finance_schema
from app.auth import (
    init_auth_schema, ensure_bootstrap_admin, get_user_by_username, get_user_by_id,
    verify_password, create_pending_user, list_users, set_user_approval, set_user_active, user_capabilities, PERMISSION_LABELS,
)
from app.workspace import router as workspace_router, init_workspace_schema, list_sections_for_user
from app.timers import router as timers_router, init_timer_schema, active_timer_for_user


from app.account_security import router as accounts_router, init_account_security_schema
from app.config import settings
from app.db import init_db, get_conn
from app.scheduler import start_scheduler
from app.timeutil import now_utc, parse_local_datetime_localinput, utc_to_local_str
from app.notifier import build_notifier
from app.meta import APP_VERSION
from app.lifeos import router as life_router, init_life_schema
from app.phones import router as phone_router, init_phone_schema
from app.life_import import router as import_router, init_import_schema
from app.life_files import router as files_router, init_file_schema
from app.backup import pre_v3_backup, pre_consolidation_backup, pre_v34_backup, pre_v36_backup
from app.consolidation import consolidate_todos
from app.life_hubs import router as hubs_router
from app.personalize import router as layout_router, init_layout_schema, appearance_for
from app.calendar_links import router as calendar_links_router, init_calendar_links_schema, sync_due_calendars, AUTO_SYNC
from app.course_import import router as course_router, init_course_schema
from app.note_reminders import router as note_reminder_router
from app.study_planner import router as study_planner_router
from app.v37 import router as v37_router, init_v37_schema, save_user_setup, _validate_preferences, _validate_reminders

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
from app.ui import templates

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.bootstrap import initialize_database
    initialize_database(APP_USERNAME,APP_PASSWORD)
    sched = start_scheduler(settings.timezone)
    if AUTO_SYNC and hasattr(sched, "add_job"):
        sched.add_job(sync_due_calendars,trigger='interval',seconds=60,id='calendar_auto_sync',
                      replace_existing=True,max_instances=1,coalesce=True,
                      next_run_time=datetime.now(timezone.utc)+timedelta(seconds=10))
    yield
    sched.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)
from app.errors import install_error_handlers, error_response
install_error_handlers(app)

# --- Simple login/session auth ---
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
APP_USERNAME = os.getenv("APP_USERNAME", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() in ("1", "true", "yes", "on")



# Reject cross-site form/API writes. This guards session-authenticated POST routes
# without requiring JavaScript or changing the existing HTML form workflow.
@app.middleware("http")
async def reject_cross_site_writes(request: Request, call_next):
    if request.method in ('POST','PUT','PATCH','DELETE'):
        origin=request.headers.get('origin','')
        from urllib.parse import urlparse
        public_host=urlparse(os.getenv('MLO_PUBLIC_URL','')).netloc.lower()
        current=request.headers.get('host','').lower()
        allowed={current}
        if public_host: allowed.add(public_host)
        if origin and urlparse(origin).netloc.lower() not in allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Cross-origin write blocked'},status_code=403)
        if request.headers.get('sec-fetch-site','').lower() == 'cross-site':
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Cross-site write blocked'},status_code=403)
    return await call_next(request)

# Resolve the signed-in database user and protect private routes.
@app.middleware("http")
async def require_auth(request: Request, call_next):
    path = request.url.path
    if request.method == 'GET' and path in ('/classic/dashboard','/todos','/todos/new','/schedule','/timers'):
        return RedirectResponse('/life/tasks' if path.startswith('/todos') else '/life/calendar' if path == '/schedule' else '/life/focus' if path == '/timers' else '/life',status_code=303)
    public_paths = {"/", "/privacy", "/termsofservice", "/login", "/signup", "/logout", "/favicon.ico", "/health", "/forgot-password", "/reset-code", "/verify-email/resend", "/service-worker.js", "/manifest.webmanifest"}
    if path.startswith(("/password-reset/", "/verify-email/")):
        return await call_next(request)
    if path.startswith("/static") or path in public_paths:
        return await call_next(request)

    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = get_user_by_id(int(user_id))
    elif request.session.get("user"):
        # Upgrade sessions created by the pre-1.4 login system.
        user = get_user_by_username(str(request.session.get("user")))

    if not user or not user["approved"] or not user["active"]:
        request.session.clear()
        if path.startswith('/api/') or 'application/json' in request.headers.get('accept',''):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Sign in required'},status_code=401)
        next_url = path + (("?" + request.url.query) if request.url.query else "")
        return RedirectResponse(url="/login?next=" + urllib.parse.quote(next_url), status_code=303)

    # Password resets invalidate every existing session. A one-time sign-in
    # after upgrading is required for sessions created before v3.6.
    if request.session.get('auth_version') != int(user['auth_version']):
        request.session.clear()
        if request.method != 'GET' or path.startswith('/api/'): return error_response(request,401,'Your session expired. Sign in in another tab, then retry your save.')
        return RedirectResponse('/login?message=Please+sign+in+again',status_code=303)
    if user['requires_email_verification'] and not user['email_verified']:
        request.session.clear()
        return RedirectResponse('/login?message=Verify+your+email+to+sign+in.',status_code=303)
    if user['must_change_password'] and path != '/account/password' and path != '/logout':
        return RedirectResponse('/account/password?required=1',status_code=303)
    request.session["user_id"] = int(user["id"])
    request.session["user"] = user["username"]
    request.session["role"] = user["role"]
    request.state.current_user = user
    from app.legacy_access import owns_legacy_data
    with get_conn() as conn:
        request.state.legacy_owner = owns_legacy_data(conn,int(user['id']))
    legacy_paths=('/courses','/items','/classes','/events','/expenses','/jobs','/todos','/finance','/classic')
    if path.startswith(legacy_paths) and user['role']=='admin' and not request.state.legacy_owner:
        from fastapi.responses import JSONResponse
        return error_response(request,403,'This record belongs to a different account.')
    # POST/JSON endpoints don't render the sidebar: avoid two extra SQL reads.
    needs_shell = request.method == 'GET' and not path.startswith(('/life/layout','/api/'))
    if needs_shell:
        titles={'/life/study/planner':'Study planner','/life/study/import':'Course import','/life':'Today','/life/tasks':'Tasks','/life/projects':'Projects','/life/study':'Study','/life/calendar':'Calendar',
                '/life/calendars':'Connected calendars','/life/notes':'Notes','/life/focus':'Focus','/life/insights':'Insights',
                '/life/goals':'Goals & habits','/life/work':'Work','/life/spaces':'Spaces','/life/import':'Import',
                '/life/search':'Search','/life/devices':'Notifications','/settings':'Settings','/account':'Account','/finance':'Finance','/admin':'Administration'}
        request.state.page_title=next((label for prefix,label in sorted(titles.items(),key=lambda item:-len(item[0])) if path==prefix or path.startswith(prefix+'/')),'Workspace')
        with get_conn() as conn:
            request.state.workspace_density=(conn.execute('SELECT density FROM v37_workspace_preferences WHERE user_id=?',(user['id'],)).fetchone() or {'density':'comfortable'})['density']
        request.state.appearance = appearance_for(int(user['id']))
        request.state.custom_sections = list_sections_for_user(int(user["id"]), sidebar_only=True)
        request.state.active_timer = active_timer_for_user(int(user["id"]))
    else:
        request.state.custom_sections = []
        request.state.active_timer = None

    # Connection authorization itself uses GET redirects. Deny new OAuth
    # connection attempts when the capability has been revoked.
    if (user['role']!='admin' and path.startswith('/life/calendars/connect/')
            and not user_capabilities(user)['calendar_connect']):
        from fastapi.responses import PlainTextResponse
        return error_response(request,403,'Calendar connections are disabled for this account.')

    # Enforce the administrator's per-user capability restrictions on writes.
    if request.method in ('POST','PUT','PATCH','DELETE') and user['role']!='admin':
        p=path
        needed=(
            'projects_create' if p in ('/life/projects','/life/projects/template') else
            'projects_share' if (p.startswith('/life/projects/') and ('/invite' in p or '/remove/' in p)) or (p.startswith('/sections/') and '/share' in p) else
            'calendar_connect' if p.startswith('/life/calendars/') and (p.endswith('/feed') or p.endswith('/delete')) else
            'files_upload' if p=='/life/files/upload' else
            'import_tasks' if p.startswith(('/life/import/','/life/study/import')) else
            'devices_manage' if p.startswith('/life/devices') else None)
        if needed and not user_capabilities(user)[needed]:
            from fastapi.responses import PlainTextResponse
            return error_response(request,403,'Your account does not have permission for this action.')

    # Member accounts are collaboration accounts by default. Personal school,
    # finance, job, and expense data remains private to administrators.
    if user["role"] != "admin":
        member_allowed = ("/life", "/api/v37/", "/api/v4/", "/sections", "/timers", "/settings", "/account", "/logout")
        if path == "/" or not path.startswith(member_allowed):
            return RedirectResponse("/life", status_code=303)

    return await call_next(request)

# Signed cookie sessions (MUST be added after require_auth so it runs first)
if not SESSION_SECRET:
    # optional but recommended: fail fast so you don't accidentally expose with dev key
    raise RuntimeError("SESSION_SECRET is not set")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE,
)



STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Root-level manifest is reliably discoverable by PWA packaging scanners.
# Static manifest remains available to existing installed clients.
@app.get('/manifest.webmanifest', include_in_schema=False)
def root_manifest():
    return FileResponse(STATIC_DIR / 'manifest.webmanifest',
                        media_type='application/manifest+json',
                        headers={'Cache-Control':'public, max-age=300'})

@app.get('/service-worker.js', include_in_schema=False)
def service_worker():
    return FileResponse(STATIC_DIR / 'sw.js',media_type='application/javascript',
       headers={'Service-Worker-Allowed':'/','Cache-Control':'no-cache'})

app.add_middleware(GZipMiddleware,minimum_size=1200)

@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer' if request.url.path.startswith(('/password-reset/','/verify-email/','/life/devices/')) else 'same-origin' 
    response.headers['X-Frame-Options']='DENY'
    if request.url.path.startswith('/static/'):
        if request.query_params.get('v') == APP_VERSION:
            response.headers['Cache-Control']='public, max-age=31536000, immutable'
        else:
            response.headers['Cache-Control']='public, max-age=604800'
    elif request.url.path == '/manifest.webmanifest':
        response.headers['Cache-Control']='public, max-age=300'
    elif request.url.path not in ('/health', '/favicon.ico'):
        response.headers['Cache-Control']='private, no-store'
    return response


from app.record_helpers import _safe_next_url, _get_setting, _set_setting, _clean_choice, _clamp_int, _parse_csv_ints

@app.get("/health")
def health():
    return {"ok": True}

# ----------------- DASHBOARD -----------------
@app.get('/', response_class=HTMLResponse)
def public_or_today(request: Request):
    # Existing users continue into their dashboard; visitors see an OAuth-compliant public home.
    if request.session.get('user_id') or request.session.get('user'):
        return RedirectResponse('/life', status_code=303)
    return templates.TemplateResponse(request, 'public_home.html', {
        'request': request,
        'title': 'My Life Organized | Your personal workspace',
    })


@app.get('/privacy', response_class=HTMLResponse, include_in_schema=False)
def privacy_page(request: Request):
    return templates.TemplateResponse(request, 'public_privacy.html', {
        'request': request,
        'title': 'Privacy Policy | My Life Organized',
        'legal_contact': os.getenv('MLO_LEGAL_CONTACT_EMAIL', '').strip(),
    }, headers={'Cache-Control': 'public, max-age=300'})


@app.get('/termsofservice', response_class=HTMLResponse, include_in_schema=False)
def terms_of_service_page(request: Request):
    return templates.TemplateResponse(request, 'public_terms.html', {
        'request': request,
        'title': 'Terms of Service | My Life Organized',
        'legal_contact': os.getenv('MLO_LEGAL_CONTACT_EMAIL', '').strip(),
    }, headers={'Cache-Control': 'public, max-age=300'})




# ----------------- COURSES -----------------










# ----------------- ITEMS -----------------





















# ----------------- TODOS -----------------
TODO_INTERVAL_OPTIONS = [
    (60, "Every 1 hour"),
    (120, "Every 2 hours"),
    (180, "Every 3 hours"),
    (240, "Every 4 hours"),
    (300, "Every 5 hours"),
    (360, "Every 6 hours"),
    (720, "Every 12 hours"),
    (1440, "Every 1 day"),
]

def _todo_interval_human(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    if minutes % 1440 == 0:
        d = minutes // 1440
        return "1 day" if d == 1 else f"{d} days"
    if minutes % 60 == 0:
        h = minutes // 60
        return "1 hour" if h == 1 else f"{h} hours"
    return f"{minutes} min"






















# ----------------- JOBS -----------------












# ----------------- EXPENSES -----------------
















# ----------------- SCHEDULE -----------------























# ----------------- SETTINGS -----------------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    with get_conn() as conn:
        data = {
            "assignment_template_minutes": _get_setting(conn, "assignment_template_minutes", "10080,4320,1440,180"),
            "exam_template_minutes": _get_setting(conn, "exam_template_minutes", "10080,4320,1440,120,30"),
            "lab_template_minutes": _get_setting(conn, "lab_template_minutes", "4320,1440,180,60"),
            "expense_template_minutes": _get_setting(conn, "expense_template_minutes", "4320,1440,180"),
            "expense_dayof_local_time": _get_setting(conn, "expense_dayof_local_time", "09:00"),
            "quiet_start": _get_setting(conn, "quiet_start", "23:00"),
            "quiet_end": _get_setting(conn, "quiet_end", "07:00"),
        }
    return templates.TemplateResponse(request,"settings.html", {"request": request, "s": data, "tz": settings.timezone, "legacy_notifications":getattr(request.state,"legacy_owner",False) and os.getenv("MLO_ENABLE_LEGACY_GLOBAL_NTFY","false").lower() in ("true","1","yes","on")})


@app.post("/settings/save")
def settings_save(
    request: Request,
    assignment_template_minutes: str = Form(...),
    exam_template_minutes: str = Form(...),
    lab_template_minutes: str = Form(...),
    expense_template_minutes: str = Form(...),
    expense_dayof_local_time: str = Form(...),
    quiet_start: str = Form(...),
    quiet_end: str = Form(...),
):
    _require_admin(request)
    with get_conn() as conn:
        _set_setting(conn, "assignment_template_minutes", assignment_template_minutes.strip())
        _set_setting(conn, "exam_template_minutes", exam_template_minutes.strip())
        _set_setting(conn, "lab_template_minutes", lab_template_minutes.strip())
        _set_setting(conn, "expense_template_minutes", expense_template_minutes.strip())
        _set_setting(conn, "expense_dayof_local_time", expense_dayof_local_time.strip())
        _set_setting(conn, "quiet_start", quiet_start.strip())
        _set_setting(conn, "quiet_end", quiet_end.strip())
        conn.commit()
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/test")
def settings_test_notification(request: Request):
    _require_admin(request)
    from app.scheduler import legacy_global_notifications_allowed
    if not legacy_global_notifications_allowed():
        return RedirectResponse('/life/devices?notice=no_global', status_code=303)
    notifier = build_notifier()
    notifier.send("Test notification", "✅ Your notifier is working.")
    return RedirectResponse("/settings", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/life", message: str = ""):
    next = _safe_next_url(next)
    return templates.TemplateResponse(request, "login.html", {"request": request, "next": next, "error": "", "message": message})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/life"),
):
    next = _safe_next_url(next)
    from app.auth_delivery import allow
    address=request.client.host if request.client else 'unknown'
    if len(password)>256 or not allow('login-ip:'+address,60,15) or not allow('login:'+username.strip().lower(),15,15):
        return templates.TemplateResponse(request,'login.html',{'request':request,'next':next,'error':'Too many attempts. Try again in 15 minutes.','message':''},status_code=429)
    user = get_user_by_username(username)
    error = "Invalid username or password."
    if user and verify_password(password, user["password_hash"]):
        if not user["active"]:
            error = "This account has been disabled by an administrator."
        elif user['requires_email_verification'] and not user['email_verified']:
            error = 'Verify your email before signing in. Use Resend verification if you need a new link.'
        elif not user["approved"]:
            error = "Your account is waiting for administrator approval."
        else:
            request.session.clear()
            request.session["user_id"] = int(user["id"])
            request.session["user"] = user["username"]
            request.session["role"] = user["role"]
            request.session["auth_version"] = int(user['auth_version'])
            destination = next if next != "/" else "/life"
            if user["role"] != "admin" and destination == "/":
                destination = "/life"
            return RedirectResponse(destination, status_code=303)

    return templates.TemplateResponse(request, "login.html", {"request": request, "next": next, "error": error, "message": ""})


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(request, "onboarding.html", {"request": request, "error": "", "message": "", "mode":"signup"})


@app.post("/signup", response_class=HTMLResponse)
def signup_submit(request:Request,background_tasks:BackgroundTasks,username:str=Form(...),
                  display_name:str=Form(""),password:str=Form(...),password_confirm:str=Form(...),
                  email:str=Form(""),v37_setup:str=Form("")):
    import json, re, sqlite3, hashlib
    from app.auth import hash_password
    from app.auth_delivery import allow,queue_email,deliver_mail
    context={'request':request,'error':'','message':'','mode':'signup',
             'form_values':{'username':username[:40],'display_name':display_name[:80],'email':email[:254]}}
    data={}
    def fail(message):
        context['error']=message
        context['initial_setup']=data
        return templates.TemplateResponse(request,'onboarding.html',context,status_code=422)
    try:
        if len(v37_setup)>6000: raise ValueError()
        data=json.loads(v37_setup) if v37_setup else {}
        _validate_preferences(data)
        _validate_reminders(data.get('reminders',{}))
        if data.get('theme','system') not in ('light','dark','system'): raise ValueError()
    except (ValueError,TypeError,KeyError,HTTPException):
        data={}
        return fail('Check your workspace preferences and try again.')
    if password!=password_confirm or not 12<=len(password)<=256:
        return fail('Use matching passwords with 12 to 256 characters.')
    username=username.strip(); email=email.strip().lower()
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,40}',username):
        return fail('Use 3 to 40 letters, numbers, periods, underscores or hyphens for your username.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254:
        return fail('Enter a valid email address.')
    if not allow('signup:'+str(request.client.host if request.client else 'unknown'),10,60):
        return fail('Too many signup attempts. Please try again later.')
    # Account, preferences and outgoing verification email commit together.
    at=datetime.now(timezone.utc)
    token=secrets.token_urlsafe(36)
    try:
        with get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            user=conn.execute('''INSERT INTO users(username,display_name,password_hash,role,approved,active,
                created_at_utc,email,requires_email_verification) VALUES(?,?,?,'member',0,1,?,?,1)''',
                (username,display_name.strip()[:80] or username,hash_password(password),at.isoformat(),email))
            uid=user.lastrowid
            save_user_setup(conn,uid,data)
            conn.execute('''INSERT INTO auth_email_tokens(user_id,purpose,token_hash,candidate_email,created_at,expires_at)
                VALUES(?,'verify_email',?,?,?,?)''',(uid,hashlib.sha256(token.encode()).hexdigest(),email,at.isoformat(),(at+timedelta(hours=1)).isoformat()))
            url=os.getenv('MLO_PUBLIC_URL','').rstrip('/')+'/verify-email/'+token
            queue_email(uid,email,'Verify your MLO account',
                'Confirm your email address:\n\n'+url+'\n\nThis link expires in one hour. Administrator approval is also required.',db=conn)
            conn.commit()
    except sqlite3.IntegrityError:
        return fail('That username or email is already registered. Sign in or recover your account.')
    background_tasks.add_task(deliver_mail)
    context['message']='Account created. Verify your email using the link in your inbox. Administrator approval is also required. If no email arrives, request a new link or contact the administrator.'
    return templates.TemplateResponse(request,'onboarding.html',context,status_code=201)


@app.get("/life/onboarding",response_class=HTMLResponse)
def v37_onboarding(request:Request):
    return templates.TemplateResponse(request,"onboarding.html",{"request":request,"mode":"profile"})


def _require_admin(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request):
    _require_admin(request)
    return templates.TemplateResponse(request, "admin_users.html", {"request": request, "users": list_users(), "capability_labels": PERMISSION_LABELS, "user_capabilities": user_capabilities})


@app.post("/admin/users/{user_id}/approval")
def admin_user_approval(request: Request, user_id: int, approved: str = Form("0")):
    admin = _require_admin(request)
    set_user_approval(user_id, approved == "1", int(admin["id"]))
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/active")
def admin_user_active(request: Request, user_id: int, active: str = Form("0")):
    _require_admin(request)
    set_user_active(user_id, active == "1")
    return RedirectResponse("/admin/users", status_code=303)


from app.school import router as school_router
from app.career import router as career_router
from app.bills import router as bills_router
from app.event_records import router as event_records_router
from app.compat import router as compat_router
app.include_router(school_router)
app.include_router(career_router)
app.include_router(bills_router)
app.include_router(event_records_router)
app.include_router(compat_router)
app.include_router(accounts_router)
app.include_router(life_router)
app.include_router(layout_router)
app.include_router(calendar_links_router)
app.include_router(hubs_router)
app.include_router(phone_router)
app.include_router(import_router)
app.include_router(files_router)
app.include_router(finance_router)
app.include_router(workspace_router)
app.include_router(timers_router)
app.include_router(v37_router)
from fastapi import APIRouter
compat_api=APIRouter(prefix='/api/v37')
for route in v37_router.routes:
    compat_api.add_api_route(route.path.removeprefix('/api/v4'),route.endpoint,methods=route.methods,include_in_schema=False)
app.include_router(compat_api)
app.include_router(course_router)
app.include_router(note_reminder_router)
app.include_router(study_planner_router)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
