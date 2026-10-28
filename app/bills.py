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

@router.get("/expenses", response_class=HTMLResponse)
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


@router.get("/expenses/new", response_class=HTMLResponse)
def new_expense(request: Request):
    return templates.TemplateResponse(request,"new_expense.html", {"request": request, "tz": settings.timezone})


@router.post("/expenses/new")
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
    title=require_title(title,'Title')
    from app.finance.budget import money_decimal
    amt=float(money_decimal(amount))

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


@router.get("/expenses/{expense_id}", response_class=HTMLResponse)
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


@router.post('/expenses/{expense_id}/update')
def update_expense(expense_id:int,title:str=Form(...),category:str=Form(''),amount:str=Form(...),due_at_local:str=Form(...),notes:str=Form(''),recurrence:str=Form('none'),recurrence_interval:int=Form(1)):
    from app.finance.budget import money_decimal
    title=require_title(title)
    amount=float(money_decimal(amount))
    due=parse_local_datetime_localinput(due_at_local,settings.timezone)
    if recurrence not in EXPENSE_RECURRENCES or not 1<=recurrence_interval<=24:raise HTTPException(422,'Choose a valid repeat interval.')
    with get_conn() as conn:
        conn.execute('BEGIN IMMEDIATE')
        expense=require_record(conn,'expenses',expense_id)
        previous=datetime.fromisoformat(expense['due_at_utc'].replace('Z','+00:00'))
        if previous.tzinfo is None:previous=previous.replace(tzinfo=timezone.utc)
        delta=due-previous
        for reminder in conn.execute("SELECT id,remind_at_utc FROM reminders WHERE entity_type='expense' AND entity_id=? AND sent_at_utc IS NULL",(expense_id,)).fetchall():
            instant=datetime.fromisoformat(reminder['remind_at_utc'].replace('Z','+00:00'))
            if instant.tzinfo is None:instant=instant.replace(tzinfo=timezone.utc)
            conn.execute('UPDATE reminders SET remind_at_utc=? WHERE id=?',((instant+delta).isoformat(),reminder['id']))
        conn.execute('UPDATE expenses SET title=?,category=?,amount=?,due_at_utc=?,notes=?,recurrence=?,recurrence_interval=?,updated_at_utc=? WHERE id=?',
                     (title,category.strip()[:120],amount,due.isoformat(),notes[:100000],recurrence,recurrence_interval,now_utc().isoformat(),expense_id))
        conn.commit()
    return RedirectResponse(f'/expenses/{expense_id}',303)


@router.post("/expenses/{expense_id}/status")
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


@router.post("/expenses/{expense_id}/delete")
def delete_expense(expense_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='expense' AND entity_id=?", (expense_id,))
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()
    return RedirectResponse("/expenses", status_code=303)


@router.post("/expenses/{expense_id}/reminders/new")
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


@router.post("/expenses/{expense_id}/reminders/template")
def add_expense_reminder_template(expense_id: int):
    with get_conn() as conn:
        exp = conn.execute("SELECT title, due_at_utc FROM expenses WHERE id=?", (expense_id,)).fetchone()
        if exp:
            _create_default_expense_reminders(conn, expense_id, exp["title"], exp["due_at_utc"])
            conn.commit()
    return RedirectResponse(f"/expenses/{expense_id}", status_code=303)
