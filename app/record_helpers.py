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
import urllib.parse
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
    if next_url.startswith("//") or "\\" in next_url or any(ord(c)<32 for c in next_url):
        return "/"

    parsed = urllib.parse.urlparse(next_url)

    # Block full external URLs
    if parsed.scheme or parsed.netloc:
        return "/"

    return next_url



def require_title(value,label='Title',limit=240):
    value=str(value).strip()
    if not value or len(value)>limit:raise HTTPException(422,f'{label} must contain 1 to {limit} characters.')
    return value


def require_record(conn,table,record_id):
    if table not in ('items','courses','jobs','expenses','events','class_meetings'):raise ValueError('Invalid record type')
    row=conn.execute('SELECT * FROM '+table+' WHERE id=?',(record_id,)).fetchone()
    if not row:raise HTTPException(404,'Record not found.')
    return row
