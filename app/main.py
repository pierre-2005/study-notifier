from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi.staticfiles import StaticFiles


from app.config import settings
from app.db import init_db, get_conn
from app.scheduler import start_scheduler
from app.timeutil import now_utc, parse_local_datetime_localinput, utc_to_local_str

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sched = start_scheduler(settings.timezone)
    yield
    sched.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def _course_name(conn, course_id: int) -> str:
    row = conn.execute("SELECT name FROM courses WHERE id=?", (course_id,)).fetchone()
    return row["name"] if row else "Unknown Course"

def _weekday_name(n: int) -> str:
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][n]

def _generate_class_reminders(conn, class_id: int, horizon_days: int = 120):
    """
    Create reminder rows for the next `horizon_days` days for a weekly class meeting.
    Avoid duplicates by checking existing reminders with the same remind_at_utc.
    """
    row = conn.execute("SELECT * FROM class_meetings WHERE id=?", (class_id,)).fetchone()
    if not row or row["active"] != 1:
        return

    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)
    now_u = now_utc()

    # Parse HH:MM
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

        # Don’t create reminders in the past
        if remind_utc <= now_u:
            continue

        remind_iso = remind_utc.isoformat()

        # avoid duplicates
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

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    with get_conn() as conn:
        upcoming = conn.execute(
            """
            SELECT items.*, courses.name as course_name
            FROM items
            JOIN courses ON courses.id = items.course_id
            WHERE items.status != 'done'
            ORDER BY items.due_at_utc ASC
            LIMIT 15
            """
        ).fetchall()

        next_reminders = conn.execute(
            """
            SELECT * FROM reminders
            WHERE sent_at_utc IS NULL
            ORDER BY remind_at_utc ASC
            LIMIT 10
            """
        ).fetchall()

        # NEW: unpaid expenses (for dashboard card)
        expenses_rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE status='unpaid'
            ORDER BY due_at_utc ASC
            LIMIT 8
            """
        ).fetchall()

    # Compute overdue flag safely outside the DB context
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
            "expenses_due": expenses_due,  # NEW
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )

# ---------- COURSES ----------
@app.get("/courses", response_class=HTMLResponse)
def courses(request: Request):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM courses ORDER BY name ASC").fetchall()
    return templates.TemplateResponse("courses.html", {"request": request, "courses": rows})

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
        items = conn.execute(
            """
            SELECT * FROM items
            WHERE course_id=?
            ORDER BY due_at_utc ASC
            """,
            (course_id,),
        ).fetchall()
    return templates.TemplateResponse(
        "course_detail.html",
        {"request": request, "course": course, "items": items, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )

# ---------- ITEMS ----------
@app.get("/items", response_class=HTMLResponse)
def items(request: Request, sort: str = "due"):
    sort_sql = {
        "due": "due_at_utc ASC",
        "priority": "priority DESC, due_at_utc ASC",
        "course": "course_name ASC, due_at_utc ASC",
    }.get(sort, "due_at_utc ASC")

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT items.*, courses.name AS course_name
            FROM items
            JOIN courses ON courses.id = items.course_id
            ORDER BY {sort_sql}
            """
        ).fetchall()

    return templates.TemplateResponse(
        "items.html",
        {"request": request, "items": rows, "sort": sort, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
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
        conn.execute(
            """
            INSERT INTO items(course_id,type,title,notes,due_at_utc,status,priority,weight,created_at_utc,updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (course_id, type, title.strip(), notes.strip(), due_utc.isoformat(), "todo", int(priority), w, now, now),
        )
        conn.commit()

    return RedirectResponse("/items", status_code=303)

@app.get("/items/{item_id}", response_class=HTMLResponse)
def item_detail(request: Request, item_id: int):
    with get_conn() as conn:
        item = conn.execute(
            """
            SELECT items.*, courses.name AS course_name
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

# ---------- JOBS ----------
@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY updated_at_utc DESC").fetchall()
    return templates.TemplateResponse("jobs.html", {"request": request, "jobs": rows, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str})

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

        # Optional: auto-create a reminder for follow-up if followup date is set
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
def add_job_reminder(
    job_id: int,
    remind_at_local: str = Form(...),
    message: str = Form(...),
):
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

# ---------- DELETE ----------
@app.post("/items/{item_id}/delete")
def delete_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='item' AND entity_id=?", (item_id,))
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit()
    return RedirectResponse("/items", status_code=303)

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

@app.post("/jobs/{job_id}/delete")
def delete_job(job_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='job' AND entity_id=?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
    return RedirectResponse("/jobs", status_code=303)

@app.post("/items/{item_id}/reminders/preset")
def add_item_reminder_preset(
    item_id: int,
    minutes: int = Form(...),
):
    # Reminder time = now + preset minutes
    remind_utc = now_utc() + timedelta(minutes=int(minutes))

    with get_conn() as conn:
        # Pull item title for a nicer default message
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

# ---------- EXPENSES ----------
@app.get("/expenses", response_class=HTMLResponse)
def expenses(request: Request, sort: str = "due"):
    sort_sql = {
        "due": "due_at_utc ASC",
        "amount": "amount DESC, due_at_utc ASC",
        "status": "status ASC, due_at_utc ASC",
    }.get(sort, "due_at_utc ASC")

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM expenses
            ORDER BY {sort_sql}
            """
        ).fetchall()

    return templates.TemplateResponse(
        "expenses.html",
        {"request": request, "expenses": rows, "sort": sort, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
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
            INSERT INTO expenses(title, category, amount, due_at_utc, status, notes, created_at_utc, updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (title.strip(), category.strip(), amt, due_utc.isoformat(), "unpaid", notes.strip(), now, now),
        )
        expense_id = cur.lastrowid
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
        conn.execute("UPDATE expenses SET status=?, updated_at_utc=? WHERE id=?", (status, now, expense_id))
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
def add_expense_reminder(
    expense_id: int,
    remind_at_local: str = Form(...),
    message: str = Form(...),
):
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

@app.post("/expenses/{expense_id}/reminders/preset_now")
def add_expense_reminder_preset_now(
    expense_id: int,
    minutes: int = Form(...),
):
    remind_utc = now_utc() + timedelta(minutes=int(minutes))

    with get_conn() as conn:
        exp = conn.execute("SELECT title FROM expenses WHERE id=?", (expense_id,)).fetchone()
        title = exp["title"] if exp else "Expense"
        msg = f"Pay expense: {title}"

        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('expense', ?, ?, ?, ?)
            """,
            (expense_id, remind_utc.isoformat(), msg, now_utc().isoformat()),
        )
        conn.commit()

    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)

@app.post("/expenses/{expense_id}/reminders/preset_before_due")
def add_expense_reminder_preset_before_due(
    expense_id: int,
    minutes_before_due: int = Form(...),
):
    with get_conn() as conn:
        exp = conn.execute("SELECT title, due_at_utc FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if not exp:
            return RedirectResponse("/expenses", status_code=303)

        due_utc = exp["due_at_utc"]
        # due_utc is ISO string; parse to datetime
        from datetime import datetime, timezone
        due_dt = datetime.fromisoformat(due_utc)
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)

        remind_dt = due_dt - timedelta(minutes=int(minutes_before_due))
        msg = f"Upcoming payment: {exp['title']} (due soon)"

        conn.execute(
            """
            INSERT INTO reminders(entity_type, entity_id, remind_at_utc, message, created_at_utc)
            VALUES('expense', ?, ?, ?, ?)
            """,
            (expense_id, remind_dt.isoformat(), msg, now_utc().isoformat()),
        )
        conn.commit()

    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)

# ---------- SCHEDULE (home) ----------
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
        {
            "request": request,
            "class_next": class_next,
            "events_next": events_next,
            "tz": settings.timezone,
            "utc_to_local_str": utc_to_local_str,
        },
    )


# ---------- CLASSES (recurring weekly) ----------
@app.get("/classes", response_class=HTMLResponse)
def classes(request: Request):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM class_meetings WHERE active=1 ORDER BY weekday ASC, start_time_local ASC"
        ).fetchall()

    # Add weekday name for display
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
    start_time_local: str = Form(...),  # "HH:MM"
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

        # auto-generate reminders for the next ~4 months
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


# ---------- EVENTS / MEETINGS (one-off) ----------
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

    return templates.TemplateResponse(
        "events.html",
        {"request": request, "events": rows, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )

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

    return templates.TemplateResponse(
        "event_detail.html",
        {"request": request, "event": event, "reminders": reminders, "tz": settings.timezone, "utc_to_local_str": utc_to_local_str},
    )

@app.post("/events/{event_id}/delete")
def delete_event(event_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='event' AND entity_id=?", (event_id,))
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
    return RedirectResponse("/events", status_code=303)

@app.post("/events/{event_id}/reminders/before")
def add_event_reminder_before(
    event_id: int,
    minutes_before: int = Form(...),
):
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
