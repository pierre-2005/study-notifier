from fastapi import FastAPI, Request, Form, HTTPException
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
from app.personalize import router as layout_router, init_layout_schema
from app.calendar_links import router as calendar_links_router, init_calendar_links_schema, sync_due_calendars, AUTO_SYNC

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION

@asynccontextmanager
async def lifespan(app: FastAPI):
    pre_v3_backup()
    pre_consolidation_backup()
    pre_v34_backup()
    pre_v36_backup()
    init_db()
    init_auth_schema()
    init_account_security_schema()
    ensure_bootstrap_admin(APP_USERNAME, APP_PASSWORD)
    init_finance_schema()
    init_workspace_schema()
    init_timer_schema()
    init_life_schema()
    init_layout_schema()
    init_calendar_links_schema()
    consolidate_todos()
    init_phone_schema()
    init_import_schema()
    init_file_schema()
    sched = start_scheduler(settings.timezone)
    if AUTO_SYNC and hasattr(sched, "add_job"):
        sched.add_job(sync_due_calendars,trigger='interval',seconds=60,id='calendar_auto_sync',
                      replace_existing=True,max_instances=1,coalesce=True,
                      next_run_time=datetime.now(timezone.utc)+timedelta(seconds=10))
    yield
    sched.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

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
    public_paths = {"/", "/privacy", "/termsofservice", "/login", "/signup", "/logout", "/favicon.ico", "/health", "/forgot-password"}
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
        next_url = path + (("?" + request.url.query) if request.url.query else "")
        return RedirectResponse(url="/login?next=" + urllib.parse.quote(next_url), status_code=303)

    # Password resets invalidate every existing session. A one-time sign-in
    # after upgrading is required for sessions created before v3.6.
    if request.session.get('auth_version') != int(user['auth_version']):
        request.session.clear()
        return RedirectResponse('/login?message=Please+sign+in+again',status_code=303)
    if user['must_change_password'] and path != '/account/password' and path != '/logout':
        return RedirectResponse('/account/password?required=1',status_code=303)
    request.session["user_id"] = int(user["id"])
    request.session["user"] = user["username"]
    request.session["role"] = user["role"]
    request.state.current_user = user
    # POST/JSON endpoints don't render the sidebar: avoid two extra SQL reads.
    needs_shell = request.method == 'GET' and not path.startswith('/life/layout')
    if needs_shell:
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
        return PlainTextResponse('Calendar connections are disabled for this account.',status_code=403)

    # Enforce the administrator's per-user capability restrictions on writes.
    if request.method in ('POST','PUT','PATCH','DELETE') and user['role']!='admin':
        p=path
        needed=(
            'projects_create' if p in ('/life/projects','/life/projects/template') else
            'projects_share' if (p.startswith('/life/projects/') and ('/invite' in p or '/remove/' in p)) or (p.startswith('/sections/') and '/share' in p) else
            'calendar_connect' if p.startswith('/life/calendars/') and (p.endswith('/feed') or p.endswith('/delete')) else
            'files_upload' if p=='/life/files/upload' else
            'import_tasks' if p.startswith('/life/import/') else
            'devices_manage' if p.startswith('/life/devices') else None)
        if needed and not user_capabilities(user)[needed]:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse('Your account does not have permission for this action.',status_code=403)

    # Member accounts are collaboration accounts by default. Personal school,
    # finance, job, and expense data remains private to administrators.
    if user["role"] != "admin":
        member_allowed = ("/life", "/sections", "/timers", "/settings", "/account", "/logout")
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

@app.get('/service-worker.js', include_in_schema=False)
def service_worker():
    return FileResponse(STATIC_DIR / 'sw.js',media_type='application/javascript',
       headers={'Service-Worker-Allowed':'/','Cache-Control':'no-cache'})

app.add_middleware(GZipMiddleware,minimum_size=1200)

@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer' if request.url.path.startswith(('/password-reset/','/verify-email/')) else 'same-origin' 
    response.headers['X-Frame-Options']='DENY'
    if request.url.path.startswith('/static/'):
        if request.query_params.get('v') == APP_VERSION:
            response.headers['Cache-Control']='public, max-age=31536000, immutable'
        else:
            response.headers['Cache-Control']='public, max-age=604800'
    elif request.url.path not in ('/health', '/favicon.ico'):
        response.headers['Cache-Control']='private, no-store'
    return response


# ----------------- helpers -----------------
ITEM_TYPES = {"assignment", "exam", "lab"}
ITEM_STATUSES = {"todo", "doing", "done"}
JOB_STATUSES = {"interested", "applied", "interview", "offer", "rejected"}
EXPENSE_STATUSES = {"unpaid", "paid"}
EXPENSE_RECURRENCES = {"none", "weekly", "monthly", "yearly"}


def _clean_choice(value: str | None, allowed: set[str], default: str) -> str:
    value = (value or "").strip().lower()
    return value if value in allowed else default


def _clamp_int(value, default: int, min_value: int, max_value: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(min_value, min(n, max_value))


def _course_name(conn, course_id: int) -> str:
    row = conn.execute("SELECT name FROM courses WHERE id=?", (course_id,)).fetchone()
    return row["name"] if row else "Unknown Course"


def _weekday_name(n: int) -> str:
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][n]


def _parse_csv_ints(s: str, fallback: list[int]) -> list[int]:
    if not s:
        return fallback
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            pass
    return out if out else fallback


def _get_setting(conn, key: str, default: str) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _set_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _add_months(dt: datetime, months: int) -> datetime:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    dmax = calendar.monthrange(y, m)[1]
    d = min(dt.day, dmax)
    return dt.replace(year=y, month=m, day=d)


def _add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        # Feb 29 -> Feb 28
        return dt.replace(year=dt.year + years, day=28)


def _local_day_bounds_utc() -> tuple[datetime, datetime]:
    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

def _utc_iso_to_local_input(utc_iso: str) -> str:
    dt = datetime.fromisoformat(utc_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ZoneInfo(settings.timezone))
    return local.strftime("%Y-%m-%dT%H:%M")


def _create_default_item_reminders(conn, item_id: int, item_type: str, title: str, due_utc_iso: str) -> int:
    due_dt = datetime.fromisoformat(due_utc_iso)
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)

    if item_type == "exam":
        default_csv = _get_setting(conn, "exam_template_minutes", "10080,4320,1440,120,30")
        minutes_list = _parse_csv_ints(default_csv, [10080, 4320, 1440, 120, 30])

    elif item_type == "lab":
        default_csv = _get_setting(conn, "lab_template_minutes", "4320,1440,180,60")
        minutes_list = _parse_csv_ints(default_csv, [4320, 1440, 180, 60])

    else:  # assignment (default)
        default_csv = _get_setting(conn, "assignment_template_minutes", "10080,4320,1440,180")
        minutes_list = _parse_csv_ints(default_csv, [10080, 4320, 1440, 180])

    created = 0
    now = now_utc()
    for mins in minutes_list:
        remind_dt = due_dt - timedelta(minutes=int(mins))
        if remind_dt <= now:
            continue
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('item', ?, ?, ?, ?)
            """,
            (item_id, remind_dt.isoformat(), f"{item_type.title()} due: {title}", now.isoformat()),
        )
        created += 1

    return created



def _create_default_expense_reminders(conn, expense_id: int, title: str, due_utc_iso: str) -> int:
    due_dt = datetime.fromisoformat(due_utc_iso)
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)

    default_csv = _get_setting(conn, "expense_template_minutes", "4320,1440,180")
    minutes_list = _parse_csv_ints(default_csv, [4320, 1440, 180])

    created = 0
    now = now_utc()

    # before due offsets
    for mins in minutes_list:
        remind_dt = due_dt - timedelta(minutes=int(mins))
        if remind_dt <= now:
            continue
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('expense', ?, ?, ?, ?)
            """,
            (expense_id, remind_dt.isoformat(), f"Upcoming payment: {title}", now.isoformat()),
        )
        created += 1

    # day-of morning reminder
    hhmm = _get_setting(conn, "expense_dayof_local_time", "09:00")
    try:
        hh, mm = [int(x) for x in hhmm.split(":")]
        tz = ZoneInfo(settings.timezone)
        due_local = due_dt.astimezone(tz)
        morning_local = due_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        morning_utc = morning_local.astimezone(timezone.utc)
        if now < morning_utc < due_dt:
            conn.execute(
                """
                INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
                VALUES('expense', ?, ?, ?, ?)
                """,
                (expense_id, morning_utc.isoformat(), f"Pay today: {title}", now.isoformat()),
            )
            created += 1
    except Exception:
        pass

    return created


def _generate_class_reminders(conn, class_id: int, horizon_days: int = 120):
    row = conn.execute("SELECT * FROM class_meetings WHERE id=?", (class_id,)).fetchone()
    if not row or row["active"] != 1:
        return

    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)
    now_u = now_utc()

    hh, mm = [int(x) for x in row["start_time_local"].split(":")]
    weekday = int(row["weekday"])
    lead = int(row["remind_before_minutes"])
    title = row["title"]
    loc = (row["location"] or "").strip()

    for d in range(horizon_days + 1):
        date = (now_local.date() + timedelta(days=d))
        if date.weekday() != weekday:
            continue

        start_local = datetime(date.year, date.month, date.day, hh, mm, tzinfo=tz)
        start_utc = start_local.astimezone(timezone.utc)
        remind_utc = start_utc - timedelta(minutes=lead)

        if remind_utc <= now_u:
            continue

        remind_iso = remind_utc.isoformat()

        exists = conn.execute(
            """
            SELECT 1 FROM reminders
            WHERE entity_type='class' AND entity_id=? AND remind_at_utc=?
            """,
            (class_id, remind_iso),
        ).fetchone()
        if exists:
            continue

        msg = f"Leave for class: {title}" + (f" ({loc})" if loc else "")
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('class', ?, ?, ?, ?)
            """,
            (class_id, remind_iso, msg, now_utc().isoformat()),
        )

def _safe_next_url(next_url: str | None) -> str:
    if not next_url:
        return "/"

    next_url = next_url.strip()

    # Must be a local path
    if not next_url.startswith("/"):
        return "/"

    # Block protocol-relative URLs like //evil.com
    if next_url.startswith("//"):
        return "/"

    parsed = urllib.parse.urlparse(next_url)

    # Block full external URLs
    if parsed.scheme or parsed.netloc:
        return "/"

    return next_url

@app.post("/items/{item_id}/reminders/clear")
def clear_item_reminders(item_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM reminders WHERE entity_type='item' AND entity_id=?",
            (item_id,),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)

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


@app.get('/classic/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    now = now_utc()
    start_today_utc, end_today_utc = _local_day_bounds_utc()
    next7 = now + timedelta(days=7)

    with get_conn() as conn:
        due_today_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE status != 'done' AND due_at_utc >= ? AND due_at_utc < ?
            """,
            (start_today_utc.isoformat(), end_today_utc.isoformat()),
        ).fetchone()["c"]

        overdue_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE status != 'done' AND due_at_utc < ?
            """,
            (now.isoformat(),),
        ).fetchone()["c"]

        next7_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE status != 'done' AND due_at_utc >= ? AND due_at_utc < ?
            """,
            (now.isoformat(), next7.isoformat()),
        ).fetchone()["c"]

        unpaid_expenses_count = conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE status='unpaid'",
        ).fetchone()["c"]

        upcoming = conn.execute(
            """
            SELECT items.*, courses.name as course_name, courses.color as course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.status != 'done'
            ORDER BY items.due_at_utc ASC
            LIMIT 10
            """
        ).fetchall()

        next_reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE sent_at_utc IS NULL
            ORDER BY remind_at_utc ASC
            LIMIT 8
            """
        ).fetchall()

        expenses_rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE status='unpaid'
            ORDER BY due_at_utc ASC
            LIMIT 6
            """
        ).fetchall()

    now_dt = datetime.now(timezone.utc)
    expenses_due = []
    for e in expenses_rows:
        due_dt = datetime.fromisoformat(e["due_at_utc"])
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        d = dict(e)
        d["is_overdue"] = due_dt < now_dt
        expenses_due.append(d)

    return templates.TemplateResponse(request,
        "dashboard.html",
        {
            "request": request,
            "upcoming": upcoming,
            "next_reminders": next_reminders,
            "expenses_due": expenses_due,
            "stats": {
                "due_today": due_today_count,
                "overdue": overdue_count,
                "next7": next7_count,
                "unpaid_expenses": unpaid_expenses_count,
            },
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )


# ----------------- COURSES -----------------
@app.get("/courses", response_class=HTMLResponse)
def courses(request: Request, q: str = ""):
    q = (q or "").strip()
    with get_conn() as conn:
        if q:
            rows = conn.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM items i WHERE i.course_id=c.id AND i.status!='done') AS open_count
                FROM courses c
                WHERE c.name LIKE ?
                ORDER BY c.name ASC
                """,
                (f"%{q}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM items i WHERE i.course_id=c.id AND i.status!='done') AS open_count
                FROM courses c
                ORDER BY c.name ASC
                """
            ).fetchall()
    return templates.TemplateResponse(request,"courses.html", {"request": request, "courses": rows, "q": q})


@app.get("/courses/new", response_class=HTMLResponse)
def new_course(request: Request):
    return templates.TemplateResponse(request,"new_course.html", {"request": request})


@app.post("/courses/new")
def create_course(
    name: str = Form(...),
    term: str = Form(""),
    color: str = Form(""),
):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO courses(name, term, color, created_at_utc) VALUES(?,?,?,?)",
            (name.strip(), term.strip(), color.strip(), now_utc().isoformat()),
        )
        conn.commit()
    return RedirectResponse("/courses", status_code=303)


@app.get("/courses/{course_id}", response_class=HTMLResponse)
def course_detail(request: Request, course_id: int):
    with get_conn() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        # FIX: join courses so templates can use course_name/course_color safely if needed
        items = conn.execute(
            """
            SELECT items.*, courses.name AS course_name, courses.color AS course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.course_id=?
            ORDER BY items.due_at_utc ASC
            """,
            (course_id,),
        ).fetchall()

    return templates.TemplateResponse(request,
        "course_detail.html",
        {
            "request": request,
            "course": course,
            "items": items,
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )


@app.post("/courses/{course_id}/delete")
def delete_course(course_id: int):
    with get_conn() as conn:
        item_ids = [r["id"] for r in conn.execute("SELECT id FROM items WHERE course_id=?", (course_id,)).fetchall()]
        if item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            conn.execute(f"DELETE FROM reminders WHERE entity_type='item' AND entity_id IN ({placeholders})", item_ids)
            conn.execute(f"DELETE FROM items WHERE id IN ({placeholders})", item_ids)

        conn.execute("DELETE FROM courses WHERE id=?", (course_id,))
        conn.commit()
    return RedirectResponse("/courses", status_code=303)


# ----------------- ITEMS -----------------
@app.get("/items", response_class=HTMLResponse)
def items(
    request: Request,
    q: str = "",
    course_id: str | None = None,
    type: str = "all",
    status: str = "open",
    when: str = "all",
    sort: str = "due",
):
    q = (q or "").strip()
    type = (type or "all").strip()
    status = (status or "open").strip()
    when = (when or "all").strip()
    sort = (sort or "due").strip()

    # NEW: safely parse course_id (because GET forms send course_id="" when blank)
    course_id_int = None
    if course_id is not None and str(course_id).strip() != "":
        try:
            course_id_int = int(course_id)
        except ValueError:
            course_id_int = None

    sort_sql = {
        "due": "items.due_at_utc ASC",
        "priority": "items.priority DESC, items.due_at_utc ASC",
        "course": "course_name ASC, items.due_at_utc ASC",
        "created": "items.created_at_utc DESC",
    }.get(sort, "items.due_at_utc ASC")

    now = now_utc()
    start_today_utc, end_today_utc = _local_day_bounds_utc()
    next7 = now + timedelta(days=7)

    where = ["1=1"]
    params = []

    if q:
        # FIX: use courses.name, not course_name alias in WHERE
        where.append("(items.title LIKE ? OR items.notes LIKE ? OR courses.name LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if course_id_int is not None:
        where.append("items.course_id = ?")
        params.append(course_id_int)

    if type in ("assignment", "exam", "lab"):
        where.append("items.type = ?")
        params.append(type)

    if status == "open":
        where.append("items.status != 'done'")
    elif status in ("todo", "doing", "done"):
        where.append("items.status = ?")
        params.append(status)

    if when == "today":
        where.append("items.due_at_utc >= ? AND items.due_at_utc < ?")
        params.extend([start_today_utc.isoformat(), end_today_utc.isoformat()])
    elif when == "next7":
        where.append("items.due_at_utc >= ? AND items.due_at_utc < ?")
        params.extend([now.isoformat(), next7.isoformat()])
    elif when == "overdue":
        where.append("items.due_at_utc < ?")
        params.append(now.isoformat())
        where.append("items.status != 'done'")

    with get_conn() as conn:
        courses = conn.execute("SELECT id, name FROM courses ORDER BY name ASC").fetchall()
        rows = conn.execute(
            f"""
            SELECT items.*, courses.name AS course_name, courses.color AS course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE {' AND '.join(where)}
            ORDER BY {sort_sql}
            """,
            tuple(params),
        ).fetchall()

    return templates.TemplateResponse(request,
        "items.html",
        {
            "request": request,
            "items": rows,
            "courses": courses,
            "filters": {"q": q, "course_id": course_id_int, "type": type, "status": status, "when": when, "sort": sort},
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )


@app.get("/items/new", response_class=HTMLResponse)
def new_item(request: Request):
    with get_conn() as conn:
        courses = conn.execute("SELECT * FROM courses ORDER BY name ASC").fetchall()
    return templates.TemplateResponse(request,"new_item.html", {"request": request, "courses": courses})


@app.post("/items/new")
def create_item(
    course_id: int = Form(...),
    type: str = Form(...),
    title: str = Form(...),
    notes: str = Form(""),
    due_at_local: str = Form(...),
    priority: int = Form(2),
    weight: str = Form(""),
    auto_template: str = Form("on"),
):
    type = _clean_choice(type, ITEM_TYPES, "assignment")
    priority = _clamp_int(priority, 2, 1, 5)
    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    w = None
    if weight.strip():
        try:
            w = float(weight.strip())
        except ValueError:
            w = None

    now = now_utc().isoformat()

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO items(course_id,type,title,notes,due_at_utc,status,priority,weight,created_at_utc,updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (course_id, type, title.strip(), notes.strip(), due_utc.isoformat(), "todo", int(priority), w, now, now),
        )
        item_id = cur.lastrowid

        if auto_template == "on":
            _create_default_item_reminders(conn, item_id, type, title.strip(), due_utc.isoformat())

        conn.commit()

    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.get("/items/{item_id}", response_class=HTMLResponse)
def item_detail(request: Request, item_id: int):
    with get_conn() as conn:
        item = conn.execute(
            """
            SELECT items.*, courses.name AS course_name, courses.color AS course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.id=?
            """,
            (item_id,),
        ).fetchone()

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='item' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (item_id,),
        ).fetchall()

    return templates.TemplateResponse(request,
        "item_detail.html",
        {
            "request": request,
            "item": item,
            "reminders": reminders,
            "due_at_local_value": _utc_iso_to_local_input(item["due_at_utc"]) if item else "",
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )


@app.post("/items/{item_id}/status")
def set_item_status(item_id: int, status: str = Form(...)):
    now = now_utc().isoformat()
    status = _clean_choice(status, ITEM_STATUSES, "todo")
    with get_conn() as conn:
        conn.execute("UPDATE items SET status=?, updated_at_utc=? WHERE id=?", (status, now, item_id))
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)

@app.post("/items/{item_id}/update")
def update_item(
    item_id: int,
    title: str = Form(...),
    due_at_local: str = Form(...),
    rebuild_template: str = Form("off"),
):
    new_title = title.strip()
    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    now = now_utc().isoformat()

    with get_conn() as conn:
        item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            return RedirectResponse("/items", status_code=303)

        old_title = (item["title"] or "").strip()

        # Update the item itself
        conn.execute(
            "UPDATE items SET title=?, due_at_utc=?, updated_at_utc=? WHERE id=?",
            (new_title, due_utc.isoformat(), now, item_id),
        )

        if rebuild_template == "on":
            # Replace pending reminders with a fresh template based on new due/title
            conn.execute(
                """
                DELETE FROM reminders
                WHERE entity_type='item' AND entity_id=? AND sent_at_utc IS NULL
                """,
                (item_id,),
            )
            _create_default_item_reminders(conn, item_id, item["type"], new_title, due_utc.isoformat())
        else:
            # NEW: If title changed, update pending reminder messages to match
            if old_title and old_title != new_title:
                conn.execute(
                    """
                    UPDATE reminders
                    SET message = REPLACE(message, ?, ?)
                    WHERE entity_type='item'
                      AND entity_id=?
                      AND sent_at_utc IS NULL
                      AND message IS NOT NULL
                      AND message LIKE '%' || ? || '%'
                    """,
                    (old_title, new_title, item_id, old_title),
                )

        conn.commit()

    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.post("/items/{item_id}/duplicate")
def duplicate_item(item_id: int):
    now_dt = now_utc()
    now_iso = now_dt.isoformat()

    with get_conn() as conn:
        item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            return RedirectResponse("/items", status_code=303)

        old_title = (item["title"] or "Untitled").strip()
        new_title = old_title + " (copy)"

        cur = conn.execute(
            """
            INSERT INTO items(course_id,type,title,notes,due_at_utc,status,priority,weight,created_at_utc,updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item["course_id"],
                item["type"],
                new_title,
                item["notes"] or "",
                item["due_at_utc"],
                "todo",
                int(item["priority"] or 2),
                item["weight"],
                now_iso,
                now_iso,
            ),
        )
        new_id = cur.lastrowid

        # Copy only pending + future reminders
        reminders = conn.execute(
            """
            SELECT remind_at_utc, message
            FROM reminders
            WHERE entity_type='item'
              AND entity_id=?
              AND sent_at_utc IS NULL
              AND remind_at_utc > ?
            ORDER BY remind_at_utc ASC
            """,
            (item_id, now_iso),
        ).fetchall()

        for r in reminders:
            msg = r["message"] or ""
            # If the old title appears in the message, update it to new title
            if old_title and old_title in msg:
                msg = msg.replace(old_title, new_title)

            conn.execute(
                """
                INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
                VALUES('item', ?, ?, ?, ?)
                """,
                (new_id, r["remind_at_utc"], msg, now_iso),
            )

        conn.commit()

    return RedirectResponse(f"/items/{new_id}", status_code=303)


@app.post("/items/{item_id}/delete")
def delete_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='item' AND entity_id=?", (item_id,))
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit()
    return RedirectResponse("/items", status_code=303)


@app.post("/items/{item_id}/reminders/new")
def add_item_reminder(
    item_id: int,
    remind_at_local: str = Form(...),
    message: str = Form(...),
):
    remind_utc = parse_local_datetime_localinput(remind_at_local, settings.timezone)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('item', ?, ?, ?, ?)
            """,
            (item_id, remind_utc.isoformat(), message.strip(), now_utc().isoformat()),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.post("/items/{item_id}/reminders/template")
def add_item_reminder_template(item_id: int):
    with get_conn() as conn:
        item = conn.execute("SELECT type, title, due_at_utc FROM items WHERE id=?", (item_id,)).fetchone()
        if item:
            _create_default_item_reminders(conn, item_id, item["type"], item["title"], item["due_at_utc"])
            conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.post("/items/{item_id}/reminders/preset")
def add_item_reminder_preset(item_id: int, minutes: int = Form(...)):
    remind_utc = now_utc() + timedelta(minutes=int(minutes))
    with get_conn() as conn:
        item = conn.execute("SELECT title FROM items WHERE id=?", (item_id,)).fetchone()
        title = item["title"] if item else "Assignment/Exam"
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('item', ?, ?, ?, ?)
            """,
            (item_id, remind_utc.isoformat(), f"Reminder: {title}", now_utc().isoformat()),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


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


@app.get("/todos", response_class=HTMLResponse)
def todos(request: Request, q: str = "", status: str = "open", sort: str = "due"):
    q = (q or "").strip()
    status = (status or "open").strip()
    sort = (sort or "due").strip()

    where = ["1=1"]
    params = []

    if q:
        where.append("(title LIKE ? OR notes LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])

    if status == "open":
        where.append("status != 'done'")
    elif status in ("todo", "doing", "done"):
        where.append("status = ?")
        params.append(status)
    # else: "all"

    sort_sql = {
        "due": "(due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC",
        "created": "created_at_utc DESC",
        "updated": "updated_at_utc DESC",
    }.get(sort, "(due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC")

    now = now_utc()

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM todos
            WHERE {' AND '.join(where)}
            ORDER BY {sort_sql}
            """,
            tuple(params),
        ).fetchall()

        enabled = _get_setting(conn, "todo_reminder_enabled", "off").strip().lower() == "on"
        try:
            minutes = int(_get_setting(conn, "todo_reminder_minutes", "60"))
        except Exception:
            minutes = 60

    # compute overdue flag for display
    view = []
    for r in rows:
        d = dict(r)
        d["is_overdue"] = False
        if d.get("due_at_utc") and d.get("status") != "done":
            try:
                due_dt = datetime.fromisoformat(d["due_at_utc"])
                if due_dt.tzinfo is None:
                    due_dt = due_dt.replace(tzinfo=timezone.utc)
                d["is_overdue"] = due_dt < now
            except Exception:
                d["is_overdue"] = False
        view.append(d)

    reminder_options = [{"value": v, "label": lbl} for (v, lbl) in TODO_INTERVAL_OPTIONS]

    return templates.TemplateResponse(request,
        "todos.html",
        {
            "request": request,
            "todos": view,
            "filters": {"q": q, "status": status, "sort": sort},
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
            "reminder": {
                "enabled": enabled,
                "minutes": minutes,
                "human": _todo_interval_human(minutes),
                "options": reminder_options,
            },
        },
    )


@app.get("/todos/new", response_class=HTMLResponse)
def new_todo(request: Request):
    return templates.TemplateResponse(request,"new_todo.html", {"request": request, "tz": settings.timezone})


@app.post("/todos/new")
def create_todo(
    title: str = Form(...),
    notes: str = Form(""),
    due_at_local: str = Form(""),
    status: str = Form("todo"),
):
    status = (status or "todo").strip()
    if status not in ("todo", "doing", "done"):
        status = "todo"

    due_utc_iso = None
    if (due_at_local or "").strip():
        due_utc_iso = parse_local_datetime_localinput(due_at_local, settings.timezone).isoformat()

    now_iso = now_utc().isoformat()

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO todos(title, notes, due_at_utc, status, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?)
            """,
            (title.strip(), notes.strip(), due_utc_iso, status, now_iso, now_iso),
        )
        todo_id = cur.lastrowid
        conn.commit()

    return RedirectResponse(f"/todos/{todo_id}", status_code=303)


@app.get("/todos/{todo_id}", response_class=HTMLResponse)
def todo_detail(request: Request, todo_id: int):
    with get_conn() as conn:
        todo = conn.execute("SELECT * FROM todos WHERE id=?", (todo_id,)).fetchone()

    if not todo:
        raise HTTPException(status_code=404, detail="To-do not found")

    due_local_value = ""
    if todo and todo["due_at_utc"]:
        due_local_value = _utc_iso_to_local_input(todo["due_at_utc"])

    return templates.TemplateResponse(request,
        "todo_detail.html",
        {
            "request": request,
            "todo": todo,
            "due_at_local_value": due_local_value,
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )


@app.post("/todos/{todo_id}/status")
def set_todo_status(todo_id: int, status: str = Form(...)):
    status = (status or "todo").strip()
    if status not in ("todo", "doing", "done"):
        status = "todo"

    now_iso = now_utc().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE todos SET status=?, updated_at_utc=? WHERE id=?", (status, now_iso, todo_id))
        conn.commit()

    return RedirectResponse(f"/todos/{todo_id}", status_code=303)


@app.post("/todos/{todo_id}/update")
def update_todo(
    todo_id: int,
    title: str = Form(...),
    notes: str = Form(""),
    due_at_local: str = Form(""),
):
    due_utc_iso = None
    if (due_at_local or "").strip():
        due_utc_iso = parse_local_datetime_localinput(due_at_local, settings.timezone).isoformat()

    now_iso = now_utc().isoformat()

    with get_conn() as conn:
        conn.execute(
            "UPDATE todos SET title=?, notes=?, due_at_utc=?, updated_at_utc=? WHERE id=?",
            (title.strip(), notes.strip(), due_utc_iso, now_iso, todo_id),
        )
        conn.commit()

    return RedirectResponse(f"/todos/{todo_id}", status_code=303)


@app.post("/todos/{todo_id}/delete")
def delete_todo(todo_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        conn.commit()
    return RedirectResponse("/todos", status_code=303)


@app.post("/todos/reminder/save")
def save_todo_reminder_settings(
    enabled: str = Form("off"),
    minutes: int = Form(60),
):
    allowed = {v for (v, _) in TODO_INTERVAL_OPTIONS}
    if minutes not in allowed:
        minutes = 60

    enabled_norm = "on" if (enabled or "").strip().lower() == "on" else "off"

    with get_conn() as conn:
        _set_setting(conn, "todo_reminder_enabled", enabled_norm)
        _set_setting(conn, "todo_reminder_minutes", str(int(minutes)))

        # Start the clock when enabled so it doesn't instantly ping
        if enabled_norm == "on":
            _set_setting(conn, "todo_reminder_last_sent_utc", now_utc().isoformat())

        conn.commit()

    return RedirectResponse("/todos", status_code=303)


@app.post("/todos/reminder/test")
def test_todo_reminder_now():
    notifier = build_notifier()

    with get_conn() as conn:
        todos = conn.execute(
            """
            SELECT title
            FROM todos
            WHERE status != 'done'
            ORDER BY (due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC
            LIMIT 8
            """
        ).fetchall()

    if not todos:
        notifier.send("To-Do reminder (test)", "No open to-dos 🎉")
        return RedirectResponse("/todos", status_code=303)

    body = "Open to-dos:\n" + "\n".join([f"- {t['title']}" for t in todos])
    notifier.send("To-Do reminder (test)", body)
    return RedirectResponse("/todos", status_code=303)




# ----------------- JOBS -----------------
@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request, q: str = "", status: str = "all"):
    q = (q or "").strip()
    status = (status or "all").strip()

    where = ["1=1"]
    params = []
    if q:
        where.append("(company LIKE ? OR role LIKE ? OR notes LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if status != "all":
        where.append("status = ?")
        params.append(status)

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE {' AND '.join(where)} ORDER BY updated_at_utc DESC",
            tuple(params),
        ).fetchall()

    return templates.TemplateResponse(request,
        "jobs.html",
        {"request": request, "jobs": rows, "filters": {"q": q, "status": status}, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.get("/jobs/new", response_class=HTMLResponse)
def new_job(request: Request):
    return templates.TemplateResponse(request,"new_job.html", {"request": request})


@app.post("/jobs/new")
def create_job(
    company: str = Form(...),
    role: str = Form(...),
    link: str = Form(""),
    status: str = Form("interested"),
    applied_at_local: str = Form(""),
    followup_at_local: str = Form(""),
    notes: str = Form(""),
):
    applied_utc = parse_local_datetime_localinput(applied_at_local, settings.timezone).isoformat() if applied_at_local else None
    followup_utc = parse_local_datetime_localinput(followup_at_local, settings.timezone).isoformat() if followup_at_local else None
    now = now_utc().isoformat()
    status = _clean_choice(status, JOB_STATUSES, "interested")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO jobs(company, role, link, status, applied_at_utc, followup_at_utc, notes, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (company.strip(), role.strip(), link.strip(), status, applied_utc, followup_utc, notes.strip(), now, now),
        )
        job_id = cur.lastrowid

        if followup_utc:
            conn.execute(
                """
                INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
                VALUES('job', ?, ?, ?, ?)
                """,
                (job_id, followup_utc, f"Follow up: {company} — {role}", now),
            )

        conn.commit()

    return RedirectResponse("/jobs", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int):
    with get_conn() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='job' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (job_id,),
        ).fetchall()

    applied_at_local_value = ""
    if job["applied_at_utc"]:
        applied_at_local_value = _utc_iso_to_local_input(job["applied_at_utc"])

    followup_at_local_value = ""
    if job["followup_at_utc"]:
        followup_at_local_value = _utc_iso_to_local_input(job["followup_at_utc"])

    return templates.TemplateResponse(
        request,
        "job_detail.html",
        {
            "request": request,
            "job": job,
            "reminders": reminders,
            "applied_at_local_value": applied_at_local_value,
            "followup_at_local_value": followup_at_local_value,
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )

@app.post("/jobs/{job_id}/update")
def update_job(
    job_id: int,
    company: str = Form(...),
    role: str = Form(...),
    link: str = Form(""),
    status: str = Form("interested"),
    applied_at_local: str = Form(""),
    followup_at_local: str = Form(""),
    notes: str = Form(""),
):
    status = (status or "interested").strip()
    if status not in ("interested", "applied", "interview", "offer", "rejected"):
        status = "interested"

    applied_utc = (
        parse_local_datetime_localinput(applied_at_local, settings.timezone).isoformat()
        if applied_at_local.strip()
        else None
    )

    followup_utc = (
        parse_local_datetime_localinput(followup_at_local, settings.timezone).isoformat()
        if followup_at_local.strip()
        else None
    )

    now_iso = now_utc().isoformat()
    company_clean = company.strip()
    role_clean = role.strip()

    with get_conn() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        old_company = (job["company"] or "").strip()
        old_role = (job["role"] or "").strip()
        old_followup_utc = job["followup_at_utc"]
        old_auto_message = f"Follow up: {old_company} — {old_role}"
        auto_reminder = None
        if old_followup_utc:
            auto_reminder = conn.execute(
                """
                SELECT id
                FROM reminders
                WHERE entity_type='job'
                  AND entity_id=?
                  AND sent_at_utc IS NULL
                  AND remind_at_utc=?
                  AND message=?
                ORDER BY id ASC
                LIMIT 1
                """,
                (job_id, old_followup_utc, old_auto_message),
            ).fetchone()

        conn.execute(
            """
            UPDATE jobs
            SET company=?,
                role=?,
                link=?,
                status=?,
                applied_at_utc=?,
                followup_at_utc=?,
                notes=?,
                updated_at_utc=?
            WHERE id=?
            """,
            (
                company_clean,
                role_clean,
                link.strip(),
                status,
                applied_utc,
                followup_utc,
                notes.strip(),
                now_iso,
                job_id,
            ),
        )

        if old_company and old_company != company_clean:
            conn.execute(
                """
                UPDATE reminders
                SET message = REPLACE(message, ?, ?)
                WHERE entity_type='job'
                  AND entity_id=?
                  AND sent_at_utc IS NULL
                  AND message IS NOT NULL
                """,
                (old_company, company_clean, job_id),
            )

        if old_role and old_role != role_clean:
            conn.execute(
                """
                UPDATE reminders
                SET message = REPLACE(message, ?, ?)
                WHERE entity_type='job'
                  AND entity_id=?
                  AND sent_at_utc IS NULL
                  AND message IS NOT NULL
                """,
                (old_role, role_clean, job_id),
            )

        new_auto_message = f"Follow up: {company_clean} — {role_clean}"
        if auto_reminder:
            if followup_utc:
                conn.execute(
                    "UPDATE reminders SET remind_at_utc=?, message=? WHERE id=?",
                    (followup_utc, new_auto_message, auto_reminder["id"]),
                )
            else:
                conn.execute("DELETE FROM reminders WHERE id=?", (auto_reminder["id"],))
        elif followup_utc and followup_utc != old_followup_utc:
            conn.execute(
                """
                INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
                VALUES('job', ?, ?, ?, ?)
                """,
                (job_id, followup_utc, new_auto_message, now_iso),
            )

        conn.commit()

    return RedirectResponse(f"/jobs/{job_id}", status_code=303)

@app.post("/jobs/{job_id}/reminders/new")
def add_job_reminder(job_id: int, remind_at_local: str = Form(...), message: str = Form(...)):
    remind_utc = parse_local_datetime_localinput(remind_at_local, settings.timezone)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('job', ?, ?, ?, ?)
            """,
            (job_id, remind_utc.isoformat(), message.strip(), now_utc().isoformat()),
        )
        conn.commit()
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/delete")
def delete_job(job_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='job' AND entity_id=?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
    return RedirectResponse("/jobs", status_code=303)


# ----------------- EXPENSES -----------------
@app.get("/expenses", response_class=HTMLResponse)
def expenses(
    request: Request,
    q: str = "",
    status: str = "all",
    when: str = "all",
    sort: str = "due",
):
    q = (q or "").strip()
    status = (status or "all").strip()
    when = (when or "all").strip()
    sort = (sort or "due").strip()

    sort_sql = {
        "due": "due_at_utc ASC",
        "amount": "amount DESC, due_at_utc ASC",
        "status": "status ASC, due_at_utc ASC",
    }.get(sort, "due_at_utc ASC")

    now = now_utc()
    start_today_utc, end_today_utc = _local_day_bounds_utc()
    next7 = now + timedelta(days=7)

    where = ["1=1"]
    params = []

    if q:
        where.append("(title LIKE ? OR category LIKE ? OR notes LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if status != "all":
        where.append("status = ?")
        params.append(status)

    if when == "today":
        where.append("due_at_utc >= ? AND due_at_utc < ?")
        params.extend([start_today_utc.isoformat(), end_today_utc.isoformat()])
    elif when == "next7":
        where.append("due_at_utc >= ? AND due_at_utc < ?")
        params.extend([now.isoformat(), next7.isoformat()])
    elif when == "overdue":
        where.append("due_at_utc < ?")
        params.append(now.isoformat())
        where.append("status = 'unpaid'")

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM expenses WHERE {' AND '.join(where)} ORDER BY {sort_sql}",
            tuple(params),
        ).fetchall()

    return templates.TemplateResponse(request,
        "expenses.html",
        {"request": request, "expenses": rows, "filters": {"q": q, "status": status, "when": when, "sort": sort}, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.get("/expenses/new", response_class=HTMLResponse)
def new_expense(request: Request):
    return templates.TemplateResponse(request,"new_expense.html", {"request": request, "tz": settings.timezone})


@app.post("/expenses/new")
def create_expense(
    title: str = Form(...),
    category: str = Form(""),
    amount: str = Form(...),
    due_at_local: str = Form(...),
    notes: str = Form(""),
    recurrence: str = Form("none"),
    recurrence_interval: int = Form(1),
    auto_template: str = Form("on"),
):
    amount_clean = amount.replace("$", "").replace(",", "").strip()
    try:
        amt = float(amount_clean)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Expense amount must be a valid number.") from exc

    if amt < 0:
        raise HTTPException(status_code=400, detail="Expense amount cannot be negative.")

    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    now = now_utc().isoformat()
    recurrence = _clean_choice(recurrence, EXPENSE_RECURRENCES, "none")
    recurrence_interval = _clamp_int(recurrence_interval, 1, 1, 24)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO expenses(title, category, amount, due_at_utc, status, notes, created_at_utc, updated_at_utc, recurrence, recurrence_interval)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (title.strip(), category.strip(), amt, due_utc.isoformat(), "unpaid", notes.strip(), now, now, recurrence, int(recurrence_interval)),
        )
        expense_id = cur.lastrowid

        if auto_template == "on":
            _create_default_expense_reminders(conn, expense_id, title.strip(), due_utc.isoformat())

        conn.commit()

    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)


@app.get("/expenses/{expense_id}", response_class=HTMLResponse)
def expense_detail(request: Request, expense_id: int):
    with get_conn() as conn:
        expense = conn.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='expense' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (expense_id,),
        ).fetchall()

    return templates.TemplateResponse(request,
        "expense_detail.html",
        {"request": request, "expense": expense, "reminders": reminders, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.post("/expenses/{expense_id}/status")
def set_expense_status(expense_id: int, status: str = Form(...)):
    now = now_utc().isoformat()
    status = _clean_choice(status, EXPENSE_STATUSES, "unpaid")
    with get_conn() as conn:
        exp = conn.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if not exp:
            return RedirectResponse("/expenses", status_code=303)

        conn.execute("UPDATE expenses SET status=?, updated_at_utc=? WHERE id=?", (status, now, expense_id))

        if (
            status == "paid"
            and exp["status"] != "paid"
            and exp["recurrence"]
            and exp["recurrence"] != "none"
        ):
            due_dt = datetime.fromisoformat(exp["due_at_utc"])
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)

            interval = int(exp["recurrence_interval"] or 1)
            rec = exp["recurrence"]

            if rec == "weekly":
                next_due = due_dt + timedelta(days=7 * interval)
            elif rec == "monthly":
                next_due = _add_months(due_dt, interval)
            elif rec == "yearly":
                next_due = _add_years(due_dt, interval)
            else:
                next_due = None

            if next_due:
                next_due_iso = next_due.isoformat()
                existing_next = conn.execute(
                    """
                    SELECT id
                    FROM expenses
                    WHERE id != ?
                      AND title = ?
                      AND amount = ?
                      AND due_at_utc = ?
                      AND recurrence = ?
                      AND recurrence_interval = ?
                    LIMIT 1
                    """,
                    (
                        expense_id,
                        exp["title"],
                        float(exp["amount"]),
                        next_due_iso,
                        exp["recurrence"],
                        interval,
                    ),
                ).fetchone()

                if not existing_next:
                    cur = conn.execute(
                        """
                        INSERT INTO expenses(title, category, amount, due_at_utc, status, notes, created_at_utc, updated_at_utc, recurrence, recurrence_interval)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            exp["title"],
                            exp["category"] or "",
                            float(exp["amount"]),
                            next_due_iso,
                            "unpaid",
                            exp["notes"] or "",
                            now,
                            now,
                            exp["recurrence"],
                            interval,
                        ),
                    )
                    new_id = cur.lastrowid
                    _create_default_expense_reminders(conn, new_id, exp["title"], next_due_iso)

        conn.commit()

    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)


@app.post("/expenses/{expense_id}/delete")
def delete_expense(expense_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='expense' AND entity_id=?", (expense_id,))
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()
    return RedirectResponse("/expenses", status_code=303)


@app.post("/expenses/{expense_id}/reminders/new")
def add_expense_reminder(expense_id: int, remind_at_local: str = Form(...), message: str = Form(...)):
    remind_utc = parse_local_datetime_localinput(remind_at_local, settings.timezone)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('expense', ?, ?, ?, ?)
            """,
            (expense_id, remind_utc.isoformat(), message.strip(), now_utc().isoformat()),
        )
        conn.commit()
    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)


@app.post("/expenses/{expense_id}/reminders/template")
def add_expense_reminder_template(expense_id: int):
    with get_conn() as conn:
        exp = conn.execute("SELECT title, due_at_utc FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if exp:
            _create_default_expense_reminders(conn, expense_id, exp["title"], exp["due_at_utc"])
            conn.commit()
    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)


# ----------------- SCHEDULE -----------------
@app.get("/schedule", response_class=HTMLResponse)
def schedule_home(request: Request):
    with get_conn() as conn:
        class_next = conn.execute(
            """
            SELECT r.remind_at_utc, r.message, cm.title
            FROM reminders r
            JOIN class_meetings cm ON cm.id = r.entity_id
            WHERE r.entity_type='class' AND r.sent_at_utc IS NULL
            ORDER BY r.remind_at_utc ASC
            LIMIT 8
            """
        ).fetchall()

        now_iso = now_utc().isoformat()
        events_next = conn.execute(
            """
            SELECT * FROM events
            WHERE start_at_utc >= ?
            ORDER BY start_at_utc ASC
            LIMIT 8
            """,
            (now_iso,),
        ).fetchall()

    return templates.TemplateResponse(request,
        "schedule.html",
        {"request": request, "class_next": class_next, "events_next": events_next, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.get("/classes", response_class=HTMLResponse)
def classes(request: Request):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM class_meetings WHERE active=1 ORDER BY weekday ASC, start_time_local ASC").fetchall()
    view = []
    for r in rows:
        d = dict(r)
        d["weekday_name"] = _weekday_name(int(r["weekday"]))
        view.append(d)
    return templates.TemplateResponse(request,"classes.html", {"request": request, "classes": view, "tz": settings.timezone})


@app.get("/classes/new", response_class=HTMLResponse)
def new_class(request: Request):
    return templates.TemplateResponse(request,"new_class.html", {"request": request, "tz": settings.timezone})

@app.get("/classes/{class_id}/edit", response_class=HTMLResponse)
def edit_class(request: Request, class_id: int):
    with get_conn() as conn:
        c = conn.execute("SELECT * FROM class_meetings WHERE id=?", (class_id,)).fetchone()

    if not c:
        raise HTTPException(status_code=404, detail="Class not found")

    return templates.TemplateResponse(
        request,
        "edit_class.html",
        {"request": request, "c": c, "tz": settings.timezone},
    )

@app.post("/classes/new")
def create_class(
    title: str = Form(...),
    weekday: int = Form(...),
    start_time_local: str = Form(...),
    duration_minutes: int = Form(50),
    location: str = Form(""),
    remind_before_minutes: int = Form(15),
    notes: str = Form(""),
):
    weekday = _clamp_int(weekday, 0, 0, 6)
    duration_minutes = _clamp_int(duration_minutes, 50, 5, 600)
    remind_before_minutes = _clamp_int(remind_before_minutes, 15, 0, 1440)
    now = now_utc().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO class_meetings(title, weekday, start_time_local, duration_minutes, location,
                                       remind_before_minutes, notes, active, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
        (title.strip(), weekday, start_time_local.strip(), duration_minutes, location.strip(),
         remind_before_minutes, notes.strip(), 1, now, now),
        )
        class_id = cur.lastrowid
        _generate_class_reminders(conn, class_id, horizon_days=120)
        conn.commit()
    return RedirectResponse("/classes", status_code=303)

@app.post("/classes/{class_id}/update")
def update_class(
    class_id: int,
    title: str = Form(...),
    weekday: int = Form(...),
    start_time_local: str = Form(...),
    duration_minutes: int = Form(50),
    location: str = Form(""),
    remind_before_minutes: int = Form(15),
    notes: str = Form(""),
):
    weekday = _clamp_int(weekday, 0, 0, 6)
    duration_minutes = _clamp_int(duration_minutes, 50, 5, 600)
    remind_before_minutes = _clamp_int(remind_before_minutes, 15, 0, 1440)
    
    now_iso = now_utc().isoformat()

    with get_conn() as conn:
        c = conn.execute("SELECT * FROM class_meetings WHERE id=?", (class_id,)).fetchone()

        if not c:
            raise HTTPException(status_code=404, detail="Class not found")

        conn.execute(
            """
            UPDATE class_meetings
            SET title=?,
                weekday=?,
                start_time_local=?,
                duration_minutes=?,
                location=?,
                remind_before_minutes=?,
                notes=?,
                updated_at_utc=?
            WHERE id=?
            """,
            (
                title.strip(),
                weekday,
                start_time_local.strip(),
                duration_minutes,
                location.strip(),
                remind_before_minutes,
                notes.strip(),
                now_iso,
                class_id,
            ),
        )

        conn.execute(
            """
            DELETE FROM reminders
            WHERE entity_type='class'
              AND entity_id=?
              AND sent_at_utc IS NULL
            """,
            (class_id,),
        )

        _generate_class_reminders(conn, class_id, horizon_days=120)
        conn.commit()

    return RedirectResponse("/classes", status_code=303)

@app.post("/classes/{class_id}/regen")
def regen_class_reminders(class_id: int):
    with get_conn() as conn:
        class_row = conn.execute(
            "SELECT id FROM class_meetings WHERE id=? AND active=1",
            (class_id,),
        ).fetchone()

        if not class_row:
            return RedirectResponse("/classes", status_code=303)

        conn.execute(
            """
            DELETE FROM reminders
            WHERE entity_type='class'
              AND entity_id=?
              AND sent_at_utc IS NULL
            """,
            (class_id,),
        )

        _generate_class_reminders(conn, class_id, horizon_days=120)
        conn.commit()

    return RedirectResponse("/classes", status_code=303)

@app.post("/classes/{class_id}/delete")
def delete_class(class_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='class' AND entity_id=?", (class_id,))
        conn.execute("DELETE FROM class_meetings WHERE id=?", (class_id,))
        conn.commit()
    return RedirectResponse("/classes", status_code=303)


@app.get("/events", response_class=HTMLResponse)
def events(request: Request):
    with get_conn() as conn:
        now_iso = now_utc().isoformat()
        rows = conn.execute(
            """
            SELECT * FROM events
            WHERE start_at_utc >= ?
            ORDER BY start_at_utc ASC
            """,
            (now_iso,),
        ).fetchall()
    return templates.TemplateResponse(request,"events.html", {"request": request, "events": rows, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str})


@app.get("/events/new", response_class=HTMLResponse)
def new_event(request: Request):
    return RedirectResponse("/life/calendars/new", status_code=303)


@app.post("/events/new")
def create_event(
    request: Request,
    title: str = Form(...),
    kind: str = Form("meeting"),
    location: str = Form(""),
    start_at_local: str = Form(...),
    end_at_local: str = Form(""),
    notes: str = Form(""),
):
    if request.state.current_user["role"] != "admin":
        raise HTTPException(403, "Legacy shared events require administrator access")
    start_utc = parse_local_datetime_localinput(start_at_local, settings.timezone).isoformat()
    end_utc = parse_local_datetime_localinput(end_at_local, settings.timezone).isoformat() if end_at_local else None
    now = now_utc().isoformat()

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO events(title, kind, location, start_at_utc, end_at_utc, notes, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (title.strip(), kind.strip(), location.strip(), start_utc, end_utc, notes.strip(), now, now),
        )
        event_id = cur.lastrowid
        conn.commit()

    return RedirectResponse(f"/events/{event_id}", status_code=303)


@app.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail(request: Request, event_id: int):
    with get_conn() as conn:
        event = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='event' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (event_id,),
        ).fetchall()
    return templates.TemplateResponse(request,"event_detail.html", {"request": request, "event": event, "reminders": reminders, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str})


@app.post("/events/{event_id}/delete")
def delete_event(event_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='event' AND entity_id=?", (event_id,))
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
    return RedirectResponse("/events", status_code=303)


@app.post("/events/{event_id}/reminders/before")
def add_event_reminder_before(event_id: int, minutes_before: int = Form(...)):
    with get_conn() as conn:
        ev = conn.execute("SELECT title, start_at_utc FROM events WHERE id=?", (event_id,)).fetchone()
        if not ev:
            return RedirectResponse("/events", status_code=303)

        start_dt = datetime.fromisoformat(ev["start_at_utc"])
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        remind_dt = start_dt - timedelta(minutes=int(minutes_before))
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('event', ?, ?, ?, ?)
            """,
            (event_id, remind_dt.isoformat(), f"Reminder: {ev['title']}", now_utc().isoformat()),
        )
        conn.commit()

    return RedirectResponse(f"/events/{event_id}", status_code=303)


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
    return templates.TemplateResponse(request,"settings.html", {"request": request, "s": data, "tz": settings.timezone})


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
    user = get_user_by_username(username)
    error = "Invalid username or password."
    if user and verify_password(password, user["password_hash"]):
        if not user["active"]:
            error = "This account has been disabled by an administrator."
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
    return templates.TemplateResponse(request, "signup.html", {"request": request, "error": "", "message": ""})


@app.post("/signup", response_class=HTMLResponse)
def signup_submit(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
    email: str = Form(""),
):
    if password != password_confirm:
        return templates.TemplateResponse(request, "signup.html", {"request": request, "error": "Passwords do not match.", "message": ""})
    ok, message = create_pending_user(username, display_name, password, email)
    if not ok:
        return templates.TemplateResponse(request, "signup.html", {"request": request, "error": message, "message": ""})
    return templates.TemplateResponse(request, "signup.html", {"request": request, "error": "", "message": message})


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

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)