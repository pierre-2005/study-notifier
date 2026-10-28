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

@router.get("/jobs", response_class=HTMLResponse)
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


@router.get("/jobs/new", response_class=HTMLResponse)
def new_job(request: Request):
    return templates.TemplateResponse(request,"new_job.html", {"request": request})


@router.post("/jobs/new")
def create_job(
    company: str = Form(...),
    role: str = Form(...),
    link: str = Form(""),
    status: str = Form("interested"),
    applied_at_local: str = Form(""),
    followup_at_local: str = Form(""),
    notes: str = Form(""),
):
    company=require_title(company,'Company')
    role=require_title(role,'Role')
    from app.ui import safe_href
    if link.strip() and not safe_href(link):raise HTTPException(422,'Enter a valid http or https posting URL.')
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


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
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


@router.post("/jobs/{job_id}/update")
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
    company=require_title(company,'Company')
    role=require_title(role,'Role')
    from app.ui import safe_href
    if link.strip() and not safe_href(link):raise HTTPException(422,'Enter a valid http or https posting URL.')
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


@router.post("/jobs/{job_id}/reminders/new")
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


@router.post("/jobs/{job_id}/delete")
def delete_job(job_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM reminders WHERE entity_type='job' AND entity_id=?", (job_id,))
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
    return RedirectResponse("/jobs", status_code=303)
