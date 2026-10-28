from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import calendar
import math
import re
from app.ui import templates
from app.db import get_conn
from app.config import settings
from app.timeutil import now_utc, parse_local_datetime_localinput, utc_to_local_str
from app.notifier import build_notifier
from app.record_helpers import *
from app.record_helpers import _clean_choice, _clamp_int, _course_name, _weekday_name, _parse_csv_ints, _get_setting, _set_setting, _add_months, _add_years, _local_day_bounds_utc, _utc_iso_to_local_input, _create_default_item_reminders, _create_default_expense_reminders, _generate_class_reminders, _safe_next_url

router=APIRouter()

@router.post("/items/{item_id}/reminders/clear")
def clear_item_reminders(item_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM reminders WHERE entity_type='item' AND entity_id=?",
            (item_id,),
        )
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@router.get("/courses", response_class=HTMLResponse)
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


@router.get("/courses/new", response_class=HTMLResponse)
def new_course(request: Request):
    return templates.TemplateResponse(request,"new_course.html", {"request": request})


@router.post("/courses/new")
def create_course(
    name: str = Form(...),
    term: str = Form(""),
    color: str = Form(""),
):
    name=require_title(name,'Name')
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO courses(name, term, color, created_at_utc) VALUES(?,?,?,?)",
            (name.strip(), term.strip(), color.strip(), now_utc().isoformat()),
        )
        conn.commit()
    return RedirectResponse("/courses", status_code=303)


@router.get("/courses/{course_id}", response_class=HTMLResponse)
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


@router.post('/courses/{course_id}/update')
def update_course(course_id:int,name:str=Form(...),term:str=Form(''),color:str=Form('')):
    name=require_title(name,'Course name')
    if color and not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise HTTPException(422,'Choose a valid course color.')
    with get_conn() as conn:
        require_record(conn,'courses',course_id)
        conn.execute('UPDATE courses SET name=?,term=?,color=? WHERE id=?',(name,term.strip()[:100],color,course_id));conn.commit()
    return RedirectResponse(f'/courses/{course_id}',303)


@router.post("/courses/{course_id}/delete")
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


@router.get("/items", response_class=HTMLResponse)
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


@router.get("/items/new", response_class=HTMLResponse)
def new_item(request: Request):
    with get_conn() as conn:
        courses = conn.execute("SELECT * FROM courses ORDER BY name ASC").fetchall()
    return templates.TemplateResponse(request,"new_item.html", {"request": request, "courses": courses})


@router.post("/items/new")
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
    title=require_title(title,'Title')
    type = _clean_choice(type, ITEM_TYPES, "assignment")
    priority = _clamp_int(priority, 2, 1, 5)
    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    w = None
    if weight.strip():
        try:
            w = float(weight.strip())
            if not math.isfinite(w) or not 0<=w<=100:raise ValueError()
        except ValueError:
            w = None

    now = now_utc().isoformat()

    with get_conn() as conn:
        require_record(conn,'courses',course_id)
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


@router.get("/items/{item_id}", response_class=HTMLResponse)
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


@router.post("/items/{item_id}/status")
def set_item_status(item_id: int, status: str = Form(...)):
    now = now_utc().isoformat()
    status = _clean_choice(status, ITEM_STATUSES, "todo")
    with get_conn() as conn:
        conn.execute("UPDATE items SET status=?, updated_at_utc=? WHERE id=?", (status, now, item_id))
        conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@router.post("/items/{item_id}/update")
def update_item(
    item_id: int,
    title: str = Form(...),
    due_at_local: str = Form(...),
    rebuild_template: str = Form("off"),
    notes: str | None = Form(None),
    weight: str | None = Form(None),
    priority: int | None = Form(None),
    type: str | None = Form(None),
):
    title=require_title(title,'Title')
    new_title = title.strip()
    due_utc = parse_local_datetime_localinput(due_at_local, settings.timezone)
    now = now_utc().isoformat()

    with get_conn() as conn:
        item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            return RedirectResponse("/items", status_code=303)

        old_title = (item["title"] or "").strip()
        fields={}
        if notes is not None:
            if len(notes)>100000:raise HTTPException(422,'Notes can contain up to 100,000 characters.')
            fields['notes']=notes
        if priority is not None:
            if not 1<=priority<=5:raise HTTPException(422,'Priority must be 1 to 5.')
            fields['priority']=priority
        if type is not None:
            if type not in ITEM_TYPES:raise HTTPException(422,'Choose a valid assessment type.')
            fields['type']=type
        if weight is not None:
            try:w=float(weight) if weight.strip() else None
            except ValueError:raise HTTPException(422,'Enter a valid assessment weight.')
            if w is not None and (not math.isfinite(w) or not 0<=w<=100):raise HTTPException(422,'Weight must be between 0 and 100.')
            fields['weight']=w
        if fields:conn.execute('UPDATE items SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),item_id))
        if rebuild_template!='on':
            old_due=datetime.fromisoformat(item['due_at_utc'].replace('Z','+00:00'))
            if old_due.tzinfo is None:old_due=old_due.replace(tzinfo=timezone.utc)
            delta=due_utc-old_due
            for r in conn.execute("SELECT id,remind_at_utc FROM reminders WHERE entity_type='item' AND entity_id=? AND sent_at_utc IS NULL",(item_id,)).fetchall():
                instant=datetime.fromisoformat(r['remind_at_utc'].replace('Z','+00:00'))
                if instant.tzinfo is None:instant=instant.replace(tzinfo=timezone.utc)
                conn.execute('UPDATE reminders SET remind_at_utc=? WHERE id=?',((instant+delta).isoformat(),r['id']))

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


@router.post("/items/{item_id}/duplicate")
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


@router.post("/items/{item_id}/delete")
def delete_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='item' AND entity_id=?", (item_id,))
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit()
    return RedirectResponse("/items", status_code=303)


@router.post("/items/{item_id}/reminders/new")
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


@router.post("/items/{item_id}/reminders/template")
def add_item_reminder_template(item_id: int):
    with get_conn() as conn:
        item = conn.execute("SELECT type, title, due_at_utc FROM items WHERE id=?", (item_id,)).fetchone()
        if item:
            _create_default_item_reminders(conn, item_id, item["type"], item["title"], item["due_at_utc"])
            conn.commit()
    return RedirectResponse(f"/items/{item_id}", status_code=303)


@router.post("/items/{item_id}/reminders/preset")
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


@router.get("/classes", response_class=HTMLResponse)
def classes(request: Request):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM class_meetings WHERE active=1 ORDER BY weekday ASC, start_time_local ASC").fetchall()
    view = []
    for r in rows:
        d = dict(r)
        d["weekday_name"] = _weekday_name(int(r["weekday"]))
        view.append(d)
    return templates.TemplateResponse(request,"classes.html", {"request": request, "classes": view, "tz": settings.timezone})


@router.get("/classes/new", response_class=HTMLResponse)
def new_class(request: Request):
    return templates.TemplateResponse(request,"new_class.html", {"request": request, "tz": settings.timezone})


@router.get("/classes/{class_id}/edit", response_class=HTMLResponse)
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


@router.post("/classes/new")
def create_class(
    title: str = Form(...),
    weekday: int = Form(...),
    start_time_local: str = Form(...),
    duration_minutes: int = Form(50),
    location: str = Form(""),
    remind_before_minutes: int = Form(15),
    notes: str = Form(""),
):
    title=require_title(title,'Title')
    datetime.strptime(start_time_local,'%H:%M')
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


@router.post("/classes/{class_id}/update")
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
    title=require_title(title,'Title')
    datetime.strptime(start_time_local,'%H:%M')
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


@router.post("/classes/{class_id}/regen")
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


@router.post("/classes/{class_id}/delete")
def delete_class(class_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='class' AND entity_id=?", (class_id,))
        conn.execute("DELETE FROM class_meetings WHERE id=?", (class_id,))
        conn.commit()
    return RedirectResponse("/classes", status_code=303)
