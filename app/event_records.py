from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import calendar
from app.ui import templates
from app.db import get_conn
from app.config import settings
from app.timeutil import now_utc, parse_local_datetime_localinput, utc_to_local_str
from app.notifier import build_notifier
from app.record_helpers import *
from app.record_helpers import _clean_choice, _clamp_int, _course_name, _weekday_name, _parse_csv_ints, _get_setting, _set_setting, _add_months, _add_years, _local_day_bounds_utc, _utc_iso_to_local_input, _create_default_item_reminders, _create_default_expense_reminders, _generate_class_reminders, _safe_next_url

router=APIRouter()

@router.get("/events", response_class=HTMLResponse)
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


@router.get("/events/new", response_class=HTMLResponse)
def new_event(request: Request):
    return RedirectResponse("/life/calendars/new", status_code=303)


@router.post("/events/new")
def create_event(
    request: Request,
    title: str = Form(...),
    kind: str = Form("meeting"),
    location: str = Form(""),
    start_at_local: str = Form(...),
    end_at_local: str = Form(""),
    notes: str = Form(""),
):
    title=require_title(title,'Title')
    if request.state.current_user["role"] != "admin":
        raise HTTPException(403, "Legacy shared events require administrator access")
    start_utc = parse_local_datetime_localinput(start_at_local, settings.timezone).isoformat()
    end_utc = parse_local_datetime_localinput(end_at_local, settings.timezone).isoformat() if end_at_local else None
    if end_utc and end_utc<=start_utc:raise HTTPException(422,'End must be after start.')
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


@router.get("/events/{event_id}", response_class=HTMLResponse)
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


@router.post('/events/{event_id}/update')
def update_event(event_id:int,title:str=Form(...),kind:str=Form('meeting'),location:str=Form(''),start_at_local:str=Form(...),end_at_local:str=Form(''),notes:str=Form('')):
    title=require_title(title)
    start=parse_local_datetime_localinput(start_at_local,settings.timezone)
    end=parse_local_datetime_localinput(end_at_local,settings.timezone) if end_at_local else None
    if end and end<=start:raise HTTPException(422,'End must be after start.')
    with get_conn() as conn:
        require_record(conn,'events',event_id)
        conn.execute('UPDATE events SET title=?,kind=?,location=?,start_at_utc=?,end_at_utc=?,notes=?,updated_at_utc=? WHERE id=?',(title,kind[:40],location[:300],start.isoformat(),end.isoformat() if end else None,notes[:100000],now_utc().isoformat(),event_id));conn.commit()
    return RedirectResponse(f'/events/{event_id}',303)


@router.post("/events/{event_id}/delete")
def delete_event(event_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='event' AND entity_id=?", (event_id,))
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
    return RedirectResponse("/events", status_code=303)


@router.post("/events/{event_id}/reminders/before")
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
