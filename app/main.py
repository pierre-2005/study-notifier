from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi.staticfiles import StaticFiles
import calendar
import json
import os
import secrets
import urllib.parse
from starlette.middleware.sessions import SessionMiddleware
from app.finance.routes import router as finance_router
from app.finance.db import init_finance_schema, ensure_finance_defaults
from app.auth import (
    init_auth_schema, ensure_bootstrap_admin, get_user_by_username, get_user_by_id,
    verify_password, create_pending_user, list_users, set_user_approval, set_user_active,
    update_user_password, update_user_profile,
)
from app.workspace import router as workspace_router, init_workspace_schema, list_sections_for_user, ensure_starter_sections
from app.timers import router as timers_router, init_timer_schema, active_timer_for_user
from app.projects import router as projects_router, init_project_schema, project_summary_for_user
from app.tenancy import (
    init_tenancy_schema, claim_legacy_data, request_user_id, get_user_setting, set_user_setting,
    list_notification_devices, create_notification_device, delete_notification_device,
    set_notification_device_enabled, get_notification_device, require_owned_row,
)
from app.notifications import send_user_notification
from app.data_export import build_user_export


from app.config import settings
from app.db import init_db, get_conn
from app.scheduler import start_scheduler
from app.timeutil import now_utc, parse_local_datetime_localinput, utc_to_local_str
from app.notifier.ntfy import NtfyNotifier
from app.meta import APP_VERSION
from app.backup import create_startup_backup

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_startup_backup(APP_VERSION)
    init_db()
    init_auth_schema()
    ensure_bootstrap_admin(APP_USERNAME, APP_PASSWORD)
    init_tenancy_schema()
    bootstrap = get_user_by_username(APP_USERNAME) if APP_USERNAME else None
    bootstrap_id = int(bootstrap["id"]) if bootstrap else None
    if bootstrap_id:
        claim_legacy_data(bootstrap_id)
    init_finance_schema(bootstrap_id)
    init_workspace_schema()
    init_project_schema()
    init_timer_schema()
    sched = start_scheduler(settings.timezone)
    yield
    sched.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

# --- Simple login/session auth ---
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
APP_USERNAME = os.getenv("APP_USERNAME", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() in ("1", "true", "yes", "on")



# Resolve the signed-in database user and protect private routes.
@app.middleware("http")
async def require_auth(request: Request, call_next):
    path = request.url.path
    public_paths = {"/login", "/signup", "/logout", "/favicon.ico", "/health"}
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

    request.session["user_id"] = int(user["id"])
    request.session["user"] = user["username"]
    request.session["role"] = user["role"]
    request.state.current_user = user
    ensure_starter_sections(int(user["id"]))
    with get_conn() as conn:
        has_finance = conn.execute("SELECT 1 FROM finance_categories WHERE owner_user_id=? LIMIT 1", (int(user["id"]),)).fetchone()
        if not has_finance:
            ensure_finance_defaults(conn, int(user["id"]))
            conn.commit()
    request.state.custom_sections = list_sections_for_user(int(user["id"]), sidebar_only=True)
    request.state.active_timer = active_timer_for_user(int(user["id"]))

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if COOKIE_SECURE:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

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


# ----------------- helpers -----------------
ITEM_TYPES = {"assignment", "exam", "lab"}
ITEM_STATUSES = {"todo", "doing", "done"}
JOB_STATUSES = {"interested", "applied", "interview", "offer", "rejected"}
EXPENSE_STATUSES = {"unpaid", "paid"}
EXPENSE_RECURRENCES = {"none", "weekly", "monthly", "yearly"}


def _uid(request: Request) -> int:
    return request_user_id(request)


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


def _get_setting(conn, key: str, default: str, user_id: int | None = None) -> str:
    if user_id:
        return get_user_setting(conn, user_id, key, default)
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _set_setting(conn, key: str, value: str, user_id: int | None = None) -> None:
    if user_id:
        set_user_setting(conn, user_id, key, value)
        return
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


def _create_default_item_reminders(conn, item_id: int, item_type: str, title: str, due_utc_iso: str, owner_user_id: int) -> int:
    due_dt = datetime.fromisoformat(due_utc_iso)
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)

    if item_type == "exam":
        default_csv = _get_setting(conn, "exam_template_minutes", "10080,4320,1440,120,30", owner_user_id)
        minutes_list = _parse_csv_ints(default_csv, [10080, 4320, 1440, 120, 30])

    elif item_type == "lab":
        default_csv = _get_setting(conn, "lab_template_minutes", "4320,1440,180,60", owner_user_id)
        minutes_list = _parse_csv_ints(default_csv, [4320, 1440, 180, 60])

    else:  # assignment (default)
        default_csv = _get_setting(conn, "assignment_template_minutes", "10080,4320,1440,180", owner_user_id)
        minutes_list = _parse_csv_ints(default_csv, [10080, 4320, 1440, 180])

    created = 0
    now = now_utc()
    for mins in minutes_list:
        remind_dt = due_dt - timedelta(minutes=int(mins))
        if remind_dt <= now:
            continue
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
            VALUES('item', ?, ?, ?, ?, ?)
            """,
            (item_id, remind_dt.isoformat(), f"{item_type.title()} due: {title}", now.isoformat(), owner_user_id),
        )
        created += 1

    return created



def _create_default_expense_reminders(conn, expense_id: int, title: str, due_utc_iso: str, owner_user_id: int) -> int:
    due_dt = datetime.fromisoformat(due_utc_iso)
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)

    default_csv = _get_setting(conn, "expense_template_minutes", "4320,1440,180", owner_user_id)
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
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
            VALUES('expense', ?, ?, ?, ?, ?)
            """,
            (expense_id, remind_dt.isoformat(), f"Upcoming payment: {title}", now.isoformat(), owner_user_id),
        )
        created += 1

    # day-of morning reminder
    hhmm = _get_setting(conn, "expense_dayof_local_time", "09:00", owner_user_id)
    try:
        hh, mm = [int(x) for x in hhmm.split(":")]
        tz = ZoneInfo(settings.timezone)
        due_local = due_dt.astimezone(tz)
        morning_local = due_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
        morning_utc = morning_local.astimezone(timezone.utc)
        if now < morning_utc < due_dt:
            conn.execute(
                """
                INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
                VALUES('expense', ?, ?, ?, ?, ?)
                """,
                (expense_id, morning_utc.isoformat(), f"Pay today: {title}", now.isoformat(), owner_user_id),
            )
            created += 1
    except Exception:
        pass

    return created


def _generate_class_reminders(conn, class_id: int, owner_user_id: int, horizon_days: int = 120):
    row = conn.execute("SELECT * FROM class_meetings WHERE id=? AND owner_user_id=?", (class_id, owner_user_id)).fetchone()
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
            WHERE entity_type='class' AND entity_id=? AND remind_at_utc=? AND owner_user_id=?
            """,
            (class_id, remind_iso, owner_user_id),
        ).fetchone()
        if exists:
            continue

        msg = f"Leave for class: {title}" + (f" ({loc})" if loc else "")
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
            VALUES('class', ?, ?, ?, ?, ?)
            """,
            (class_id, remind_iso, msg, now_utc().isoformat(), row["owner_user_id"]),
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
def clear_item_reminders(request: Request, item_id: int):
    uid = _uid(request)
    with get_conn() as conn:
        require_owned_row(conn, "items", item_id, uid, "Item")
        conn.execute(
            "DELETE FROM reminders WHERE entity_type='item' AND entity_id=? AND owner_user_id=?",
            (item_id, uid),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)

@app.get("/health")
def health():
    return {"ok": True}

# ----------------- DASHBOARD -----------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    uid = _uid(request)
    now = now_utc()
    start_today_utc, end_today_utc = _local_day_bounds_utc()
    next7 = now + timedelta(days=7)

    with get_conn() as conn:
        due_today_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE owner_user_id=? AND status != 'done' AND due_at_utc >= ? AND due_at_utc < ?
            """,
            (uid, start_today_utc.isoformat(), end_today_utc.isoformat()),
        ).fetchone()["c"]

        overdue_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE owner_user_id=? AND status != 'done' AND due_at_utc < ?
            """,
            (uid, now.isoformat()),
        ).fetchone()["c"]

        next7_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE owner_user_id=? AND status != 'done' AND due_at_utc >= ? AND due_at_utc < ?
            """,
            (uid, now.isoformat(), next7.isoformat()),
        ).fetchone()["c"]

        unpaid_expenses_count = conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE owner_user_id=? AND status='unpaid'",
            (uid,),
        ).fetchone()["c"]

        upcoming = conn.execute(
            """
            SELECT items.*, courses.name as course_name, courses.color as course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.owner_user_id=? AND courses.owner_user_id=? AND items.status != 'done'
            ORDER BY items.due_at_utc ASC
            LIMIT 10
            """,
            (uid, uid),
        ).fetchall()

        next_reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE owner_user_id=? AND sent_at_utc IS NULL
            ORDER BY remind_at_utc ASC
            LIMIT 8
            """,
            (uid,),
        ).fetchall()

        expenses_rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE owner_user_id=? AND status='unpaid'
            ORDER BY due_at_utc ASC
            LIMIT 6
            """,
            (uid,),
        ).fetchall()

        open_todos = conn.execute(
            "SELECT * FROM todos WHERE owner_user_id=? AND status!='done' ORDER BY (due_at_utc IS NULL), due_at_utc ASC, updated_at_utc DESC LIMIT 6",
            (uid,),
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
            "open_todos": open_todos,
            "projects": project_summary_for_user(uid, 6),
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
    uid = _uid(request)
    q = (q or "").strip()
    with get_conn() as conn:
        if q:
            rows = conn.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM items i WHERE i.course_id=c.id AND i.owner_user_id=? AND i.status!='done') AS open_count
                FROM courses c
                WHERE c.owner_user_id=? AND c.name LIKE ?
                ORDER BY c.name ASC
                """,
                (uid, uid, f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM items i WHERE i.course_id=c.id AND i.owner_user_id=? AND i.status!='done') AS open_count
                FROM courses c
                WHERE c.owner_user_id=?
                ORDER BY c.name ASC
                """,
                (uid, uid),
            ).fetchall()
    return templates.TemplateResponse(request,"courses.html", {"request": request, "courses": rows, "q": q})


@app.get("/courses/new", response_class=HTMLResponse)
def new_course(request: Request):
    return templates.TemplateResponse(request,"new_course.html", {"request": request})


@app.post("/courses/new")
def create_course(
    request: Request,
    name: str = Form(...),
    term: str = Form(""),
    color: str = Form(""),
):
    uid = _uid(request)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO courses(name, term, color, created_at_utc, owner_user_id) VALUES(?,?,?,?,?)",
            (name.strip(), term.strip(), color.strip(), now_utc().isoformat(), uid),
        )
        conn.commit()
    return RedirectResponse("/courses", status_code=303)


@app.get("/courses/{course_id}", response_class=HTMLResponse)
def course_detail(request: Request, course_id: int):
    uid = _uid(request)
    with get_conn() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id=? AND owner_user_id=?", (course_id, uid)).fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        # FIX: join courses so templates can use course_name/course_color safely if needed
        items = conn.execute(
            """
            SELECT items.*, courses.name AS course_name, courses.color AS course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.course_id=? AND items.owner_user_id=? AND courses.owner_user_id=?
            ORDER BY items.due_at_utc ASC
            """,
            (course_id, uid, uid),
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
def delete_course(request: Request, course_id: int):
    uid = _uid(request)
    with get_conn() as conn:
        require_owned_row(conn, "courses", course_id, uid, "Course")
        item_ids = [r["id"] for r in conn.execute("SELECT id FROM items WHERE course_id=? AND owner_user_id=?", (course_id, uid)).fetchall()]
        if item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            conn.execute(f"DELETE FROM reminders WHERE owner_user_id=? AND entity_type='item' AND entity_id IN ({placeholders})", [uid, *item_ids])
            conn.execute(f"DELETE FROM items WHERE owner_user_id=? AND id IN ({placeholders})", [uid, *item_ids])

        conn.execute("DELETE FROM courses WHERE id=? AND owner_user_id=?", (course_id, uid))
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

    uid = _uid(request)
    where = ["items.owner_user_id=?", "courses.owner_user_id=?"]
    params = [uid, uid]

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
        courses = conn.execute("SELECT id, name FROM courses WHERE owner_user_id=? ORDER BY name ASC", (uid,)).fetchall()
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
    uid = _uid(request)
    with get_conn() as conn:
        courses = conn.execute("SELECT * FROM courses WHERE owner_user_id=? ORDER BY name ASC", (uid,)).fetchall()
    return templates.TemplateResponse(request,"new_item.html", {"request": request, "courses": courses})


@app.post("/items/new")
def create_item(
    request: Request,
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
    uid = _uid(request)

    with get_conn() as conn:
        course = conn.execute("SELECT id FROM courses WHERE id=? AND owner_user_id=?", (course_id, uid)).fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        cur = conn.execute(
            """
            INSERT INTO items(course_id,type,title,notes,due_at_utc,status,priority,weight,created_at_utc,updated_at_utc,owner_user_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (course_id, type, title.strip(), notes.strip(), due_utc.isoformat(), "todo", int(priority), w, now, now, uid),
        )
        item_id = cur.lastrowid

        if auto_template == "on":
            _create_default_item_reminders(conn, item_id, type, title.strip(), due_utc.isoformat(), uid)

        conn.commit()

    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.get("/items/{item_id}", response_class=HTMLResponse)
def item_detail(request: Request, item_id: int):
    uid = _uid(request)
    with get_conn() as conn:
        item = conn.execute(
            """
            SELECT items.*, courses.name AS course_name, courses.color AS course_color
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.id=? AND items.owner_user_id=? AND courses.owner_user_id=?
            """,
            (item_id, uid, uid),
        ).fetchone()

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='item' AND entity_id=? AND owner_user_id=?
            ORDER BY remind_at_utc ASC
            """,
            (item_id, uid),
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
def set_item_status(request: Request, item_id: int, status: str = Form(...)):
    uid = _uid(request)
    now = now_utc().isoformat()
    status = _clean_choice(status, ITEM_STATUSES, "todo")
    with get_conn() as conn:
        require_owned_row(conn, "items", item_id, uid, "Item")
        conn.execute("UPDATE items SET status=?, updated_at_utc=? WHERE id=? AND owner_user_id=?", (status, now, item_id, uid))
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)

@app.post("/items/{item_id}/update")
def update_item(
    request: Request,
    item_id: int,
    title: str = Form(...),
    due_at_local: str = Form(...),
    rebuild_template: str = Form("off"),
):
    new_title = title.strip()
    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    now = now_utc().isoformat()
    uid = _uid(request)

    with get_conn() as conn:
        item = conn.execute("SELECT * FROM items WHERE id=? AND owner_user_id=?", (item_id, uid)).fetchone()
        if not item:
            return RedirectResponse("/items", status_code=303)

        old_title = (item["title"] or "").strip()

        # Update the item itself
        conn.execute(
            "UPDATE items SET title=?, due_at_utc=?, updated_at_utc=? WHERE id=? AND owner_user_id=?",
            (new_title, due_utc.isoformat(), now, item_id, uid),
        )

        if rebuild_template == "on":
            # Replace pending reminders with a fresh template based on new due/title
            conn.execute(
                """
                DELETE FROM reminders
                WHERE entity_type='item' AND entity_id=? AND owner_user_id=? AND sent_at_utc IS NULL
                """,
                (item_id, uid),
            )
            _create_default_item_reminders(conn, item_id, item["type"], new_title, due_utc.isoformat(), uid)
        else:
            # NEW: If title changed, update pending reminder messages to match
            if old_title and old_title != new_title:
                conn.execute(
                    """
                    UPDATE reminders
                    SET message = REPLACE(message, ?, ?)
                    WHERE entity_type='item'
                      AND entity_id=?
                      AND owner_user_id=?
                      AND sent_at_utc IS NULL
                      AND message IS NOT NULL
                      AND message LIKE '%' || ? || '%'
                    """,
                    (old_title, new_title, item_id, uid, old_title),
                )

        conn.commit()

    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.post("/items/{item_id}/duplicate")
def duplicate_item(request: Request, item_id: int):
    uid = _uid(request)
    now_dt = now_utc()
    now_iso = now_dt.isoformat()

    with get_conn() as conn:
        item = conn.execute("SELECT * FROM items WHERE id=? AND owner_user_id=?", (item_id, uid)).fetchone()
        if not item:
            return RedirectResponse("/items", status_code=303)

        old_title = (item["title"] or "Untitled").strip()
        new_title = old_title + " (copy)"

        cur = conn.execute(
            """
            INSERT INTO items(course_id,type,title,notes,due_at_utc,status,priority,weight,created_at_utc,updated_at_utc,owner_user_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
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
                uid,
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
              AND owner_user_id=?
              AND sent_at_utc IS NULL
              AND remind_at_utc > ?
            ORDER BY remind_at_utc ASC
            """,
            (item_id, uid, now_iso),
        ).fetchall()

        for r in reminders:
            msg = r["message"] or ""
            # If the old title appears in the message, update it to new title
            if old_title and old_title in msg:
                msg = msg.replace(old_title, new_title)

            conn.execute(
                """
                INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
                VALUES('item', ?, ?, ?, ?, ?)
                """,
                (new_id, r["remind_at_utc"], msg, now_iso, uid),
            )

        conn.commit()

    return RedirectResponse(f"/items/{new_id}", status_code=303)


@app.post("/items/{item_id}/delete")
def delete_item(request: Request, item_id: int):
    uid = _uid(request)
    with get_conn() as conn:
        require_owned_row(conn, "items", item_id, uid, "Item")
        conn.execute("DELETE FROM reminders WHERE entity_type='item' AND entity_id=? AND owner_user_id=?", (item_id, uid))
        conn.execute("DELETE FROM items WHERE id=? AND owner_user_id=?", (item_id, uid))
        conn.commit()
    return RedirectResponse("/items", status_code=303)


@app.post("/items/{item_id}/reminders/new")
def add_item_reminder(
    request: Request,
    item_id: int,
    remind_at_local: str = Form(...),
    message: str = Form(...),
):
    uid = _uid(request)
    remind_utc = parse_local_datetime_localinput(remind_at_local, settings.timezone)
    with get_conn() as conn:
        require_owned_row(conn, "items", item_id, uid, "Item")
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
            VALUES('item', ?, ?, ?, ?, ?)
            """,
            (item_id, remind_utc.isoformat(), message.strip(), now_utc().isoformat(), uid),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.post("/items/{item_id}/reminders/template")
def add_item_reminder_template(request: Request, item_id: int):
    uid = _uid(request)
    with get_conn() as conn:
        item = conn.execute("SELECT type, title, due_at_utc FROM items WHERE id=? AND owner_user_id=?", (item_id, uid)).fetchone()
        if item:
            _create_default_item_reminders(conn, item_id, item["type"], item["title"], item["due_at_utc"], uid)
            conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@app.post("/items/{item_id}/reminders/preset")
def add_item_reminder_preset(request: Request, item_id: int, minutes: int = Form(...)):
    uid = _uid(request)
    remind_utc = now_utc() + timedelta(minutes=int(minutes))
    with get_conn() as conn:
        item = conn.execute("SELECT title FROM items WHERE id=? AND owner_user_id=?", (item_id, uid)).fetchone()
        title = item["title"] if item else "Assignment/Exam"
        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc, owner_user_id)
            VALUES('item', ?, ?, ?, ?, ?)
            """,
            (item_id, remind_utc.isoformat(), f"Reminder: {title}", now_utc().isoformat(), uid),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


# ----------------- TODOS -----------------
TODO_INTERVAL_OPTIONS = [
    (60, "Every 1 hour"), (120, "Every 2 hours"), (180, "Every 3 hours"),
    (240, "Every 4 hours"), (300, "Every 5 hours"), (360, "Every 6 hours"),
    (720, "Every 12 hours"), (1440, "Every 1 day"),
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
    uid = _uid(request)
    q, status, sort = (q or "").strip(), (status or "open").strip(), (sort or "due").strip()
    where, params = ["owner_user_id=?"], [uid]
    if q:
        where.append("(title LIKE ? OR notes LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if status == "open":
        where.append("status!='done'")
    elif status in ITEM_STATUSES:
        where.append("status=?")
        params.append(status)
    sort_sql = {
        "due": "(due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC",
        "created": "created_at_utc DESC", "updated": "updated_at_utc DESC",
    }.get(sort, "(due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC")
    now = now_utc()
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM todos WHERE {' AND '.join(where)} ORDER BY {sort_sql}", tuple(params)).fetchall()
        enabled = _get_setting(conn, "todo_reminder_enabled", "off", uid).strip().lower() == "on"
        try:
            minutes = int(_get_setting(conn, "todo_reminder_minutes", "60", uid))
        except Exception:
            minutes = 60
    view=[]
    for row in rows:
        d=dict(row); d["is_overdue"]=False
        if d.get("due_at_utc") and d.get("status") != "done":
            try:
                due=datetime.fromisoformat(d["due_at_utc"])
                if due.tzinfo is None: due=due.replace(tzinfo=timezone.utc)
                d["is_overdue"] = due < now
            except Exception: pass
        view.append(d)
    return templates.TemplateResponse(request, "todos.html", {
        "request":request, "todos":view, "filters":{"q":q,"status":status,"sort":sort},
        "tz":settings.timezone, "utc_to_local_str":utc_to_local_str,
        "reminder":{"enabled":enabled,"minutes":minutes,"human":_todo_interval_human(minutes),
                    "options":[{"value":v,"label":lbl} for v,lbl in TODO_INTERVAL_OPTIONS]},
    })


@app.get("/todos/new", response_class=HTMLResponse)
def new_todo(request: Request):
    return templates.TemplateResponse(request, "new_todo.html", {"request":request, "tz":settings.timezone})


@app.post("/todos/new")
def create_todo(request: Request, title: str=Form(...), notes: str=Form(""), due_at_local: str=Form(""), status: str=Form("todo")):
    uid=_uid(request); status=_clean_choice(status, ITEM_STATUSES, "todo")
    due_iso=parse_local_datetime_localinput(due_at_local, settings.timezone).isoformat() if due_at_local.strip() else None
    now=now_utc().isoformat()
    with get_conn() as conn:
        cur=conn.execute("INSERT INTO todos(title,notes,due_at_utc,status,created_at_utc,updated_at_utc,owner_user_id) VALUES(?,?,?,?,?,?,?)",
                         (title.strip(),notes.strip(),due_iso,status,now,now,uid))
        conn.commit(); todo_id=cur.lastrowid
    return RedirectResponse(f"/todos/{todo_id}", status_code=303)


@app.get("/todos/{todo_id}", response_class=HTMLResponse)
def todo_detail(request: Request, todo_id: int):
    uid=_uid(request)
    with get_conn() as conn: todo=conn.execute("SELECT * FROM todos WHERE id=? AND owner_user_id=?",(todo_id,uid)).fetchone()
    if not todo: raise HTTPException(404,"To-do not found")
    due_local=_utc_iso_to_local_input(todo["due_at_utc"]) if todo["due_at_utc"] else ""
    return templates.TemplateResponse(request,"todo_detail.html",{"request":request,"todo":todo,"due_at_local_value":due_local,"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.post("/todos/{todo_id}/status")
def set_todo_status(request: Request, todo_id: int, status: str=Form(...)):
    uid=_uid(request); status=_clean_choice(status, ITEM_STATUSES, "todo")
    with get_conn() as conn:
        require_owned_row(conn,"todos",todo_id,uid,"To-do")
        conn.execute("UPDATE todos SET status=?,updated_at_utc=? WHERE id=? AND owner_user_id=?",(status,now_utc().isoformat(),todo_id,uid)); conn.commit()
    return RedirectResponse(f"/todos/{todo_id}",303)


@app.post("/todos/{todo_id}/update")
def update_todo(request: Request, todo_id: int, title: str=Form(...), notes: str=Form(""), due_at_local: str=Form("")):
    uid=_uid(request); due_iso=parse_local_datetime_localinput(due_at_local,settings.timezone).isoformat() if due_at_local.strip() else None
    with get_conn() as conn:
        require_owned_row(conn,"todos",todo_id,uid,"To-do")
        conn.execute("UPDATE todos SET title=?,notes=?,due_at_utc=?,updated_at_utc=? WHERE id=? AND owner_user_id=?",
                     (title.strip(),notes.strip(),due_iso,now_utc().isoformat(),todo_id,uid)); conn.commit()
    return RedirectResponse(f"/todos/{todo_id}",303)


@app.post("/todos/{todo_id}/delete")
def delete_todo(request: Request, todo_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        conn.execute("DELETE FROM todos WHERE id=? AND owner_user_id=?",(todo_id,uid)); conn.commit()
    return RedirectResponse("/todos",303)


@app.post("/todos/reminder/save")
def save_todo_reminder_settings(request: Request, enabled: str=Form("off"), minutes: int=Form(60)):
    uid=_uid(request); allowed={v for v,_ in TODO_INTERVAL_OPTIONS}; minutes=minutes if minutes in allowed else 60
    enabled_norm="on" if enabled.strip().lower()=="on" else "off"
    with get_conn() as conn:
        _set_setting(conn,"todo_reminder_enabled",enabled_norm,uid); _set_setting(conn,"todo_reminder_minutes",str(minutes),uid)
        if enabled_norm=="on": _set_setting(conn,"todo_reminder_last_sent_utc",now_utc().isoformat(),uid)
        conn.commit()
    return RedirectResponse("/todos",303)


@app.post("/todos/reminder/test")
def test_todo_reminder_now(request: Request):
    uid=_uid(request)
    with get_conn() as conn:
        rows=conn.execute("SELECT title FROM todos WHERE owner_user_id=? AND status!='done' ORDER BY (due_at_utc IS NULL),due_at_utc,updated_at_utc DESC LIMIT 8",(uid,)).fetchall()
    body="No open to-dos 🎉" if not rows else "Open to-dos:\n"+"\n".join(f"- {r['title']}" for r in rows)
    send_user_notification(uid,"To-Do reminder (test)",body)
    return RedirectResponse("/todos",303)


# ----------------- JOBS -----------------
@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request, q: str="", status: str="all"):
    uid=_uid(request); q=q.strip(); status=status.strip(); where=["owner_user_id=?"]; params=[uid]
    if q: where.append("(company LIKE ? OR role LIKE ? OR notes LIKE ?)"); params += [f"%{q}%"]*3
    if status!="all": where.append("status=?"); params.append(status)
    with get_conn() as conn: rows=conn.execute(f"SELECT * FROM jobs WHERE {' AND '.join(where)} ORDER BY updated_at_utc DESC",tuple(params)).fetchall()
    return templates.TemplateResponse(request,"jobs.html",{"request":request,"jobs":rows,"filters":{"q":q,"status":status},"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.get("/jobs/new", response_class=HTMLResponse)
def new_job(request: Request): return templates.TemplateResponse(request,"new_job.html",{"request":request})


@app.post("/jobs/new")
def create_job(request: Request, company: str=Form(...), role: str=Form(...), link: str=Form(""), status: str=Form("interested"), applied_at_local: str=Form(""), followup_at_local: str=Form(""), notes: str=Form("")):
    uid=_uid(request); status=_clean_choice(status,JOB_STATUSES,"interested"); now=now_utc().isoformat()
    applied=parse_local_datetime_localinput(applied_at_local,settings.timezone).isoformat() if applied_at_local.strip() else None
    follow=parse_local_datetime_localinput(followup_at_local,settings.timezone).isoformat() if followup_at_local.strip() else None
    with get_conn() as conn:
        cur=conn.execute("INSERT INTO jobs(company,role,link,status,applied_at_utc,followup_at_utc,notes,created_at_utc,updated_at_utc,owner_user_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (company.strip(),role.strip(),link.strip(),status,applied,follow,notes.strip(),now,now,uid)); job_id=cur.lastrowid
        if follow: conn.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc,owner_user_id) VALUES('job',?,?,?,?,?)",(job_id,follow,f"Follow up: {company.strip()} — {role.strip()}",now,uid))
        conn.commit()
    return RedirectResponse(f"/jobs/{job_id}",303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        job=conn.execute("SELECT * FROM jobs WHERE id=? AND owner_user_id=?",(job_id,uid)).fetchone()
        reminders=conn.execute("SELECT * FROM reminders WHERE entity_type='job' AND entity_id=? AND owner_user_id=? ORDER BY remind_at_utc",(job_id,uid)).fetchall()
    if not job: raise HTTPException(404,"Job not found")
    return templates.TemplateResponse(request,"job_detail.html",{"request":request,"job":job,"reminders":reminders,
      "applied_at_local_value":_utc_iso_to_local_input(job["applied_at_utc"]) if job["applied_at_utc"] else "",
      "followup_at_local_value":_utc_iso_to_local_input(job["followup_at_utc"]) if job["followup_at_utc"] else "",
      "tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.post("/jobs/{job_id}/update")
def update_job(request: Request, job_id: int, company: str=Form(...), role: str=Form(...), link: str=Form(""), status: str=Form("interested"), applied_at_local: str=Form(""), followup_at_local: str=Form(""), notes: str=Form("")):
    uid=_uid(request); status=_clean_choice(status,JOB_STATUSES,"interested"); now=now_utc().isoformat()
    applied=parse_local_datetime_localinput(applied_at_local,settings.timezone).isoformat() if applied_at_local.strip() else None
    follow=parse_local_datetime_localinput(followup_at_local,settings.timezone).isoformat() if followup_at_local.strip() else None
    company=company.strip(); role=role.strip()
    with get_conn() as conn:
        old=require_owned_row(conn,"jobs",job_id,uid,"Job")
        conn.execute("UPDATE jobs SET company=?,role=?,link=?,status=?,applied_at_utc=?,followup_at_utc=?,notes=?,updated_at_utc=? WHERE id=? AND owner_user_id=?",
                     (company,role,link.strip(),status,applied,follow,notes.strip(),now,job_id,uid))
        # Keep the automatically generated follow-up reminder in sync; preserve manual reminders.
        oldmsg=f"Follow up: {old['company']} — {old['role']}"
        auto=conn.execute("SELECT id FROM reminders WHERE owner_user_id=? AND entity_type='job' AND entity_id=? AND sent_at_utc IS NULL AND message=? ORDER BY id LIMIT 1",(uid,job_id,oldmsg)).fetchone()
        newmsg=f"Follow up: {company} — {role}"
        if auto and follow: conn.execute("UPDATE reminders SET remind_at_utc=?,message=? WHERE id=? AND owner_user_id=?",(follow,newmsg,auto['id'],uid))
        elif auto and not follow: conn.execute("DELETE FROM reminders WHERE id=? AND owner_user_id=?",(auto['id'],uid))
        elif follow and follow != old['followup_at_utc']: conn.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc,owner_user_id) VALUES('job',?,?,?,?,?)",(job_id,follow,newmsg,now,uid))
        conn.commit()
    return RedirectResponse(f"/jobs/{job_id}",303)


@app.post("/jobs/{job_id}/reminders/new")
def add_job_reminder(request: Request, job_id: int, remind_at_local: str=Form(...), message: str=Form(...)):
    uid=_uid(request); remind=parse_local_datetime_localinput(remind_at_local,settings.timezone).isoformat()
    with get_conn() as conn:
        require_owned_row(conn,"jobs",job_id,uid,"Job")
        conn.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc,owner_user_id) VALUES('job',?,?,?,?,?)",(job_id,remind,message.strip(),now_utc().isoformat(),uid)); conn.commit()
    return RedirectResponse(f"/jobs/{job_id}",303)


@app.post("/jobs/{job_id}/delete")
def delete_job(request: Request, job_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE owner_user_id=? AND entity_type='job' AND entity_id=?",(uid,job_id)); conn.execute("DELETE FROM jobs WHERE id=? AND owner_user_id=?",(job_id,uid)); conn.commit()
    return RedirectResponse("/jobs",303)


# ----------------- EXPENSES -----------------
@app.get("/expenses", response_class=HTMLResponse)
def expenses(request: Request, q: str="", status: str="all", when: str="all", sort: str="due"):
    uid=_uid(request); q=q.strip(); status=status.strip(); when=when.strip(); sort=sort.strip()
    sort_sql={"due":"due_at_utc ASC","amount":"amount DESC,due_at_utc ASC","status":"status ASC,due_at_utc ASC"}.get(sort,"due_at_utc ASC")
    now=now_utc(); start,end=_local_day_bounds_utc(); next7=now+timedelta(days=7); where=["owner_user_id=?"]; params=[uid]
    if q: where.append("(title LIKE ? OR category LIKE ? OR notes LIKE ?)"); params += [f"%{q}%"]*3
    if status!="all": where.append("status=?"); params.append(status)
    if when=="today": where.append("due_at_utc>=? AND due_at_utc<?"); params += [start.isoformat(),end.isoformat()]
    elif when=="next7": where.append("due_at_utc>=? AND due_at_utc<?"); params += [now.isoformat(),next7.isoformat()]
    elif when=="overdue": where += ["due_at_utc<?","status='unpaid'"]; params.append(now.isoformat())
    with get_conn() as conn: rows=conn.execute(f"SELECT * FROM expenses WHERE {' AND '.join(where)} ORDER BY {sort_sql}",tuple(params)).fetchall()
    return templates.TemplateResponse(request,"expenses.html",{"request":request,"expenses":rows,"filters":{"q":q,"status":status,"when":when,"sort":sort},"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.get("/expenses/new", response_class=HTMLResponse)
def new_expense(request: Request): return templates.TemplateResponse(request,"new_expense.html",{"request":request,"tz":settings.timezone})


@app.post("/expenses/new")
def create_expense(request: Request, title: str=Form(...), category: str=Form(""), amount: str=Form(...), due_at_local: str=Form(...), notes: str=Form(""), recurrence: str=Form("none"), recurrence_interval: int=Form(1), auto_template: str=Form("on")):
    uid=_uid(request)
    try: amt=float(amount.replace("$","").replace(",","").strip())
    except ValueError as exc: raise HTTPException(400,"Expense amount must be a valid number.") from exc
    if amt<0: raise HTTPException(400,"Expense amount cannot be negative.")
    due=parse_local_datetime_localinput(due_at_local,settings.timezone).isoformat(); now=now_utc().isoformat(); recurrence=_clean_choice(recurrence,EXPENSE_RECURRENCES,"none"); interval=_clamp_int(recurrence_interval,1,1,24)
    with get_conn() as conn:
        cur=conn.execute("INSERT INTO expenses(title,category,amount,due_at_utc,status,notes,created_at_utc,updated_at_utc,recurrence,recurrence_interval,owner_user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (title.strip(),category.strip(),amt,due,"unpaid",notes.strip(),now,now,recurrence,interval,uid)); eid=cur.lastrowid
        if auto_template=="on": _create_default_expense_reminders(conn,eid,title.strip(),due,uid)
        conn.commit()
    return RedirectResponse(f"/expenses/{eid}",303)


@app.get("/expenses/{expense_id}", response_class=HTMLResponse)
def expense_detail(request: Request, expense_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        exp=conn.execute("SELECT * FROM expenses WHERE id=? AND owner_user_id=?",(expense_id,uid)).fetchone()
        rem=conn.execute("SELECT * FROM reminders WHERE owner_user_id=? AND entity_type='expense' AND entity_id=? ORDER BY remind_at_utc",(uid,expense_id)).fetchall()
    if not exp: raise HTTPException(404,"Expense not found")
    return templates.TemplateResponse(request,"expense_detail.html",{"request":request,"expense":exp,"reminders":rem,"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.post("/expenses/{expense_id}/status")
def set_expense_status(request: Request, expense_id: int, status: str=Form(...)):
    uid=_uid(request); status=_clean_choice(status,EXPENSE_STATUSES,"unpaid"); now=now_utc().isoformat()
    with get_conn() as conn:
        exp=require_owned_row(conn,"expenses",expense_id,uid,"Expense")
        conn.execute("UPDATE expenses SET status=?,updated_at_utc=? WHERE id=? AND owner_user_id=?",(status,now,expense_id,uid))
        if status=="paid" and exp['status']!="paid" and exp['recurrence'] and exp['recurrence']!="none":
            due=datetime.fromisoformat(exp['due_at_utc']); due=due if due.tzinfo else due.replace(tzinfo=timezone.utc); interval=int(exp['recurrence_interval'] or 1)
            nxt=due+timedelta(days=7*interval) if exp['recurrence']=="weekly" else _add_months(due,interval) if exp['recurrence']=="monthly" else _add_years(due,interval) if exp['recurrence']=="yearly" else None
            if nxt:
                nxtiso=nxt.isoformat(); exists=conn.execute("SELECT id FROM expenses WHERE owner_user_id=? AND id!=? AND title=? AND amount=? AND due_at_utc=? AND recurrence=? AND recurrence_interval=? LIMIT 1",(uid,expense_id,exp['title'],float(exp['amount']),nxtiso,exp['recurrence'],interval)).fetchone()
                if not exists:
                    cur=conn.execute("INSERT INTO expenses(title,category,amount,due_at_utc,status,notes,created_at_utc,updated_at_utc,recurrence,recurrence_interval,owner_user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (exp['title'],exp['category'] or "",float(exp['amount']),nxtiso,"unpaid",exp['notes'] or "",now,now,exp['recurrence'],interval,uid)); _create_default_expense_reminders(conn,cur.lastrowid,exp['title'],nxtiso,uid)
        conn.commit()
    return RedirectResponse(f"/expenses/{expense_id}",303)


@app.post("/expenses/{expense_id}/delete")
def delete_expense(request: Request, expense_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE owner_user_id=? AND entity_type='expense' AND entity_id=?",(uid,expense_id)); conn.execute("DELETE FROM expenses WHERE id=? AND owner_user_id=?",(expense_id,uid)); conn.commit()
    return RedirectResponse("/expenses",303)


@app.post("/expenses/{expense_id}/reminders/new")
def add_expense_reminder(request: Request, expense_id: int, remind_at_local: str=Form(...), message: str=Form(...)):
    uid=_uid(request); remind=parse_local_datetime_localinput(remind_at_local,settings.timezone).isoformat()
    with get_conn() as conn:
        require_owned_row(conn,"expenses",expense_id,uid,"Expense")
        conn.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc,owner_user_id) VALUES('expense',?,?,?,?,?)",(expense_id,remind,message.strip(),now_utc().isoformat(),uid)); conn.commit()
    return RedirectResponse(f"/expenses/{expense_id}",303)


@app.post("/expenses/{expense_id}/reminders/template")
def add_expense_reminder_template(request: Request, expense_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        exp=conn.execute("SELECT title,due_at_utc FROM expenses WHERE id=? AND owner_user_id=?",(expense_id,uid)).fetchone()
        if exp: _create_default_expense_reminders(conn,expense_id,exp['title'],exp['due_at_utc'],uid); conn.commit()
    return RedirectResponse(f"/expenses/{expense_id}",303)


# ----------------- SCHEDULE -----------------
@app.get("/schedule", response_class=HTMLResponse)
def schedule_home(request: Request):
    uid=_uid(request); now=now_utc().isoformat()
    with get_conn() as conn:
        class_next=conn.execute("SELECT r.remind_at_utc,r.message,cm.title FROM reminders r JOIN class_meetings cm ON cm.id=r.entity_id WHERE r.owner_user_id=? AND cm.owner_user_id=? AND r.entity_type='class' AND r.sent_at_utc IS NULL ORDER BY r.remind_at_utc LIMIT 8",(uid,uid)).fetchall()
        events_next=conn.execute("SELECT * FROM events WHERE owner_user_id=? AND start_at_utc>=? ORDER BY start_at_utc LIMIT 8",(uid,now)).fetchall()
    return templates.TemplateResponse(request,"schedule.html",{"request":request,"class_next":class_next,"events_next":events_next,"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.get("/classes", response_class=HTMLResponse)
def classes(request: Request):
    uid=_uid(request)
    with get_conn() as conn: rows=conn.execute("SELECT * FROM class_meetings WHERE owner_user_id=? AND active=1 ORDER BY weekday,start_time_local",(uid,)).fetchall()
    view=[]
    for row in rows: d=dict(row); d['weekday_name']=_weekday_name(int(row['weekday'])); view.append(d)
    return templates.TemplateResponse(request,"classes.html",{"request":request,"classes":view,"tz":settings.timezone})


@app.get("/classes/new", response_class=HTMLResponse)
def new_class(request: Request): return templates.TemplateResponse(request,"new_class.html",{"request":request,"tz":settings.timezone})


@app.get("/classes/{class_id}/edit", response_class=HTMLResponse)
def edit_class(request: Request, class_id: int):
    uid=_uid(request)
    with get_conn() as conn: c=conn.execute("SELECT * FROM class_meetings WHERE id=? AND owner_user_id=?",(class_id,uid)).fetchone()
    if not c: raise HTTPException(404,"Class not found")
    return templates.TemplateResponse(request,"edit_class.html",{"request":request,"c":c,"tz":settings.timezone})


@app.post("/classes/new")
def create_class(request: Request, title: str=Form(...), weekday: int=Form(...), start_time_local: str=Form(...), duration_minutes: int=Form(50), location: str=Form(""), remind_before_minutes: int=Form(15), notes: str=Form("")):
    uid=_uid(request); weekday=_clamp_int(weekday,0,0,6); duration_minutes=_clamp_int(duration_minutes,50,5,600); remind_before_minutes=_clamp_int(remind_before_minutes,15,0,1440); now=now_utc().isoformat()
    with get_conn() as conn:
        cur=conn.execute("INSERT INTO class_meetings(title,weekday,start_time_local,duration_minutes,location,remind_before_minutes,notes,active,created_at_utc,updated_at_utc,owner_user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (title.strip(),weekday,start_time_local.strip(),duration_minutes,location.strip(),remind_before_minutes,notes.strip(),1,now,now,uid)); cid=cur.lastrowid
        _generate_class_reminders(conn,cid,uid,120); conn.commit()
    return RedirectResponse("/classes",303)


@app.post("/classes/{class_id}/update")
def update_class(request: Request, class_id: int, title: str=Form(...), weekday: int=Form(...), start_time_local: str=Form(...), duration_minutes: int=Form(50), location: str=Form(""), remind_before_minutes: int=Form(15), notes: str=Form("")):
    uid=_uid(request); weekday=_clamp_int(weekday,0,0,6); duration_minutes=_clamp_int(duration_minutes,50,5,600); remind_before_minutes=_clamp_int(remind_before_minutes,15,0,1440)
    with get_conn() as conn:
        require_owned_row(conn,"class_meetings",class_id,uid,"Class")
        conn.execute("UPDATE class_meetings SET title=?,weekday=?,start_time_local=?,duration_minutes=?,location=?,remind_before_minutes=?,notes=?,updated_at_utc=? WHERE id=? AND owner_user_id=?",
                     (title.strip(),weekday,start_time_local.strip(),duration_minutes,location.strip(),remind_before_minutes,notes.strip(),now_utc().isoformat(),class_id,uid))
        conn.execute("DELETE FROM reminders WHERE owner_user_id=? AND entity_type='class' AND entity_id=? AND sent_at_utc IS NULL",(uid,class_id)); _generate_class_reminders(conn,class_id,uid,120); conn.commit()
    return RedirectResponse("/classes",303)


@app.post("/classes/{class_id}/regen")
def regen_class_reminders(request: Request, class_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        row=conn.execute("SELECT id FROM class_meetings WHERE id=? AND owner_user_id=? AND active=1",(class_id,uid)).fetchone()
        if row:
            conn.execute("DELETE FROM reminders WHERE owner_user_id=? AND entity_type='class' AND entity_id=? AND sent_at_utc IS NULL",(uid,class_id)); _generate_class_reminders(conn,class_id,uid,120); conn.commit()
    return RedirectResponse("/classes",303)


@app.post("/classes/{class_id}/delete")
def delete_class(request: Request, class_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE owner_user_id=? AND entity_type='class' AND entity_id=?",(uid,class_id)); conn.execute("DELETE FROM class_meetings WHERE id=? AND owner_user_id=?",(class_id,uid)); conn.commit()
    return RedirectResponse("/classes",303)


@app.get("/events", response_class=HTMLResponse)
def events(request: Request):
    uid=_uid(request)
    with get_conn() as conn: rows=conn.execute("SELECT * FROM events WHERE owner_user_id=? AND start_at_utc>=? ORDER BY start_at_utc",(uid,now_utc().isoformat())).fetchall()
    return templates.TemplateResponse(request,"events.html",{"request":request,"events":rows,"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.get("/events/new", response_class=HTMLResponse)
def new_event(request: Request): return templates.TemplateResponse(request,"new_event.html",{"request":request,"tz":settings.timezone})


@app.post("/events/new")
def create_event(request: Request, title: str=Form(...), kind: str=Form("meeting"), location: str=Form(""), start_at_local: str=Form(...), end_at_local: str=Form(""), notes: str=Form("")):
    uid=_uid(request); start=parse_local_datetime_localinput(start_at_local,settings.timezone).isoformat(); end=parse_local_datetime_localinput(end_at_local,settings.timezone).isoformat() if end_at_local.strip() else None; now=now_utc().isoformat()
    with get_conn() as conn:
        cur=conn.execute("INSERT INTO events(title,kind,location,start_at_utc,end_at_utc,notes,created_at_utc,updated_at_utc,owner_user_id) VALUES(?,?,?,?,?,?,?,?,?)",(title.strip(),kind.strip(),location.strip(),start,end,notes.strip(),now,now,uid)); conn.commit(); eid=cur.lastrowid
    return RedirectResponse(f"/events/{eid}",303)


@app.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail(request: Request, event_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        event=conn.execute("SELECT * FROM events WHERE id=? AND owner_user_id=?",(event_id,uid)).fetchone(); rem=conn.execute("SELECT * FROM reminders WHERE owner_user_id=? AND entity_type='event' AND entity_id=? ORDER BY remind_at_utc",(uid,event_id)).fetchall()
    if not event: raise HTTPException(404,"Event not found")
    return templates.TemplateResponse(request,"event_detail.html",{"request":request,"event":event,"reminders":rem,"tz":settings.timezone,"utc_to_local_str":utc_to_local_str})


@app.post("/events/{event_id}/delete")
def delete_event(request: Request, event_id: int):
    uid=_uid(request)
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE owner_user_id=? AND entity_type='event' AND entity_id=?",(uid,event_id)); conn.execute("DELETE FROM events WHERE id=? AND owner_user_id=?",(event_id,uid)); conn.commit()
    return RedirectResponse("/events",303)


@app.post("/events/{event_id}/reminders/before")
def add_event_reminder_before(request: Request, event_id: int, minutes_before: int=Form(...)):
    uid=_uid(request)
    with get_conn() as conn:
        ev=conn.execute("SELECT title,start_at_utc FROM events WHERE id=? AND owner_user_id=?",(event_id,uid)).fetchone()
        if not ev: return RedirectResponse("/events",303)
        start=datetime.fromisoformat(ev['start_at_utc']); start=start if start.tzinfo else start.replace(tzinfo=timezone.utc); remind=start-timedelta(minutes=int(minutes_before))
        conn.execute("INSERT INTO reminders(entity_type,entity_id,remind_at_utc,message,created_at_utc,owner_user_id) VALUES('event',?,?,?,?,?)",(event_id,remind.isoformat(),f"Reminder: {ev['title']}",now_utc().isoformat(),uid)); conn.commit()
    return RedirectResponse(f"/events/{event_id}",303)


# ----------------- SETTINGS & DEVICES -----------------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    uid = _uid(request)
    with get_conn() as conn:
        data = {
            "assignment_template_minutes": _get_setting(conn, "assignment_template_minutes", "10080,4320,1440,180", uid),
            "exam_template_minutes": _get_setting(conn, "exam_template_minutes", "10080,4320,1440,120,30", uid),
            "lab_template_minutes": _get_setting(conn, "lab_template_minutes", "4320,1440,180,60", uid),
            "expense_template_minutes": _get_setting(conn, "expense_template_minutes", "4320,1440,180", uid),
            "expense_dayof_local_time": _get_setting(conn, "expense_dayof_local_time", "09:00", uid),
            "quiet_start": _get_setting(conn, "quiet_start", "23:00", uid),
            "quiet_end": _get_setting(conn, "quiet_end", "07:00", uid),
        }
    return templates.TemplateResponse(request, "settings.html", {
        "request": request, "s": data, "tz": settings.timezone,
        "devices": list_notification_devices(uid), "ntfy_base_url": settings.ntfy_base_url,
    })


@app.post("/settings/save")
def settings_save(
    request: Request,
    assignment_template_minutes: str = Form(...), exam_template_minutes: str = Form(...),
    lab_template_minutes: str = Form(...), expense_template_minutes: str = Form(...),
    expense_dayof_local_time: str = Form(...), quiet_start: str = Form(...), quiet_end: str = Form(...),
):
    uid = _uid(request)
    with get_conn() as conn:
        for key, value in {
            "assignment_template_minutes": assignment_template_minutes,
            "exam_template_minutes": exam_template_minutes,
            "lab_template_minutes": lab_template_minutes,
            "expense_template_minutes": expense_template_minutes,
            "expense_dayof_local_time": expense_dayof_local_time,
            "quiet_start": quiet_start, "quiet_end": quiet_end,
        }.items():
            _set_setting(conn, key, value.strip(), uid)
        conn.commit()
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.get("/settings/export")
def settings_export_data(request: Request):
    uid = _uid(request)
    payload = build_user_export(uid)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    username = str(request.state.current_user["username"]).replace("/", "_").replace("\\", "_")
    body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="mlo-{username}-{stamp}.json"'},
    )


@app.post("/settings/test")
def settings_test_notification(request: Request):
    send_user_notification(_uid(request), "MLO test notification", "✅ Your personal notification setup is working.")
    return RedirectResponse("/settings#devices", status_code=303)


@app.post("/settings/devices/new")
def settings_device_new(request: Request, label: str = Form("Phone"), topic: str = Form("")):
    uid = _uid(request)
    topic = (topic or "").strip()
    if not topic:
        topic = f"mlo-{uid}-{secrets.token_urlsafe(18).replace('_','').replace('-','')}"
    # ntfy topics are URL path components; keeping the accepted alphabet narrow also
    # avoids accidental malformed URLs when users paste spaces or full URLs.
    topic = "".join(ch for ch in topic if ch.isalnum() or ch in "-_")[:180]
    if not topic:
        raise HTTPException(status_code=400, detail="Notification topic is invalid")
    create_notification_device(uid, label, topic)
    return RedirectResponse("/settings#devices", status_code=303)


@app.post("/settings/devices/{device_id}/toggle")
def settings_device_toggle(request: Request, device_id: int, enabled: str = Form("0")):
    set_notification_device_enabled(_uid(request), device_id, enabled == "1")
    return RedirectResponse("/settings#devices", status_code=303)


@app.post("/settings/devices/{device_id}/test")
def settings_device_test(request: Request, device_id: int):
    uid = _uid(request)
    device = get_notification_device(uid, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    NtfyNotifier(settings.ntfy_base_url, device["topic"]).send(
        "MLO device test", f"✅ Notifications are connected to {device['label']}."
    )
    return RedirectResponse("/settings#devices", status_code=303)


@app.post("/settings/devices/{device_id}/delete")
def settings_device_delete(request: Request, device_id: int):
    delete_notification_device(_uid(request), device_id)
    return RedirectResponse("/settings#devices", status_code=303)


@app.post("/settings/profile")
def settings_profile(request: Request, display_name: str = Form("")):
    uid = _uid(request)
    update_user_profile(uid, display_name)
    return RedirectResponse("/settings#account", status_code=303)


@app.post("/settings/password")
def settings_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
):
    if new_password != new_password_confirm:
        return RedirectResponse("/settings?password_error=mismatch#account", status_code=303)
    ok, _ = update_user_password(_uid(request), current_password, new_password)
    suffix = "password_saved=1" if ok else "password_error=current"
    return RedirectResponse(f"/settings?{suffix}#account", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/", message: str = ""):
    next = _safe_next_url(next)
    return templates.TemplateResponse(request, "login.html", {"request": request, "next": next, "error": "", "message": message})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
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
            destination = next or "/"
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
):
    if password != password_confirm:
        return templates.TemplateResponse(request, "signup.html", {"request": request, "error": "Passwords do not match.", "message": ""})
    ok, message = create_pending_user(username, display_name, password)
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
    return templates.TemplateResponse(request, "admin_users.html", {"request": request, "users": list_users()})


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


app.include_router(finance_router)
app.include_router(workspace_router)
app.include_router(projects_router)
app.include_router(timers_router)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)