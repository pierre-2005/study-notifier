from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi.staticfiles import StaticFiles
import calendar
import os
import urllib.parse
from starlette.middleware.sessions import SessionMiddleware


from app.config import settings
from app.db import init_db, get_conn
from app.scheduler import start_scheduler
from app.timeutil import now_utc, parse_local_datetime_localinput, utc_to_local_str
from app.notifier import build_notifier

APP_VERSION = "1.2.8"

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sched = start_scheduler(settings.timezone)
    yield
    sched.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

# --- Simple login/session auth ---
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
APP_USERNAME = os.getenv("APP_USERNAME", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() in ("1", "true", "yes", "on")

# Signed cookie sessions
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET or "dev-insecure-change-me",
    same_site="lax",
    https_only=COOKIE_SECURE,
)

# Redirect to /login if not authenticated
@app.middleware("http")
async def require_auth(request: Request, call_next):
    path = request.url.path

    # Allow login + static assets without auth
    if path.startswith("/static") or path in ("/login", "/logout"):
        return await call_next(request)

    # Already logged in
    if request.session.get("user"):
        return await call_next(request)

    # Not logged in -> send to login with ?next=
    next_url = path
    if request.url.query:
        next_url += "?" + request.url.query
    return RedirectResponse(
        url="/login?next=" + urllib.parse.quote(next_url),
        status_code=303
    )


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ----------------- helpers -----------------
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
    try:
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    except Exception:
        row = conn.execute("SELECT key FROM app_settings WHERE key=?", (key,)).fetchone()
        if row:
            conn.execute("UPDATE app_settings SET value=? WHERE key=?", (value, key))
        else:
            conn.execute("INSERT INTO app_settings(key, value) VALUES(?, ?)", (key, value))


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



@app.post("/items/{item_id}/reminders/clear")
def clear_item_reminders(item_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM reminders WHERE entity_type='item' AND entity_id=?",
            (item_id,),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


# ----------------- DASHBOARD -----------------
@app.get("/", response_class=HTMLResponse)
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

    return templates.TemplateResponse(
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
    return templates.TemplateResponse("courses.html", {"request": request, "courses": rows, "q": q})


@app.get("/courses/new", response_class=HTMLResponse)
def new_course(request: Request):
    return templates.TemplateResponse("new_course.html", {"request": request})


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

    return templates.TemplateResponse(
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

    return templates.TemplateResponse(
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
    return templates.TemplateResponse("new_item.html", {"request": request, "courses": courses})


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

        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='item' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (item_id,),
        ).fetchall()

    return templates.TemplateResponse(
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

    return templates.TemplateResponse(
        "jobs.html",
        {"request": request, "jobs": rows, "filters": {"q": q, "status": status}, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.get("/jobs/new", response_class=HTMLResponse)
def new_job(request: Request):
    return templates.TemplateResponse("new_job.html", {"request": request})


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
        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='job' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (job_id,),
        ).fetchall()

    return templates.TemplateResponse(
        "job_detail.html",
        {"request": request, "job": job, "reminders": reminders, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


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

    return templates.TemplateResponse(
        "expenses.html",
        {"request": request, "expenses": rows, "filters": {"q": q, "status": status, "when": when, "sort": sort}, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.get("/expenses/new", response_class=HTMLResponse)
def new_expense(request: Request):
    return templates.TemplateResponse("new_expense.html", {"request": request, "tz": settings.timezone})


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
    try:
        amt = float(amount)
    except ValueError:
        amt = 0.0

    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    now = now_utc().isoformat()

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
        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='expense' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (expense_id,),
        ).fetchall()

    return templates.TemplateResponse(
        "expense_detail.html",
        {"request": request, "expense": expense, "reminders": reminders, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )


@app.post("/expenses/{expense_id}/status")
def set_expense_status(expense_id: int, status: str = Form(...)):
    now = now_utc().isoformat()
    with get_conn() as conn:
        exp = conn.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if not exp:
            return RedirectResponse("/expenses", status_code=303)

        conn.execute("UPDATE expenses SET status=?, updated_at_utc=? WHERE id=?", (status, now, expense_id))

        if status == "paid" and exp["recurrence"] and exp["recurrence"] != "none":
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
                cur = conn.execute(
                    """
                    INSERT INTO expenses(title, category, amount, due_at_utc, status, notes, created_at_utc, updated_at_utc, recurrence, recurrence_interval)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        exp["title"],
                        exp["category"] or "",
                        float(exp["amount"]),
                        next_due.isoformat(),
                        "unpaid",
                        exp["notes"] or "",
                        now,
                        now,
                        exp["recurrence"],
                        interval,
                    ),
                )
                new_id = cur.lastrowid
                _create_default_expense_reminders(conn, new_id, exp["title"], next_due.isoformat())

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

    return templates.TemplateResponse(
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
    return templates.TemplateResponse("classes.html", {"request": request, "classes": view, "tz": settings.timezone})


@app.get("/classes/new", response_class=HTMLResponse)
def new_class(request: Request):
    return templates.TemplateResponse("new_class.html", {"request": request, "tz": settings.timezone})


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
    now = now_utc().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO class_meetings(title, weekday, start_time_local, duration_minutes, location,
                                       remind_before_minutes, notes, active, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (title.strip(), int(weekday), start_time_local.strip(), int(duration_minutes), location.strip(),
             int(remind_before_minutes), notes.strip(), 1, now, now),
        )
        class_id = cur.lastrowid
        _generate_class_reminders(conn, class_id, horizon_days=120)
        conn.commit()
    return RedirectResponse("/classes", status_code=303)


@app.post("/classes/{class_id}/regen")
def regen_class_reminders(class_id: int):
    with get_conn() as conn:
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
    return templates.TemplateResponse("events.html", {"request": request, "events": rows, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str})


@app.get("/events/new", response_class=HTMLResponse)
def new_event(request: Request):
    return templates.TemplateResponse("new_event.html", {"request": request, "tz": settings.timezone})


@app.post("/events/new")
def create_event(
    title: str = Form(...),
    kind: str = Form("meeting"),
    location: str = Form(""),
    start_at_local: str = Form(...),
    end_at_local: str = Form(""),
    notes: str = Form(""),
):
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
        reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE entity_type='event' AND entity_id=?
            ORDER BY remind_at_utc ASC
            """,
            (event_id,),
        ).fetchall()
    return templates.TemplateResponse("event_detail.html", {"request": request, "event": event, "reminders": reminders, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str})


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
    return templates.TemplateResponse("settings.html", {"request": request, "s": data, "tz": settings.timezone})


@app.post("/settings/save")
def settings_save(
    assignment_template_minutes: str = Form(...),
    exam_template_minutes: str = Form(...),
    lab_template_minutes: str = Form(...),
    expense_template_minutes: str = Form(...),
    expense_dayof_local_time: str = Form(...),
    quiet_start: str = Form(...),
    quiet_end: str = Form(...),
):
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
def settings_test_notification():
    notifier = build_notifier()
    notifier.send("Test notification", "✅ Your notifier is working.")
    return RedirectResponse("/settings", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    return templates.TemplateResponse("login.html", {"request": request, "next": next, "error": ""})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    # If you forgot to set env vars, fail closed (safer)
    if not APP_USERNAME or not APP_PASSWORD or not SESSION_SECRET:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "next": next,
                "error": "Server login is not configured yet. Set SESSION_SECRET, APP_USERNAME, APP_PASSWORD.",
            },
        )

    if username == APP_USERNAME and password == APP_PASSWORD:
        request.session["user"] = username
        return RedirectResponse(next or "/", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "next": next, "error": "Invalid login."})


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
