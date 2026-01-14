from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db import get_conn
from app.timeutil import now_utc
from app.notifier import build_notifier
from app.config import settings


def _get_setting(conn, key: str, default: str) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _in_quiet_hours(now_local: datetime, start_hhmm: str, end_hhmm: str) -> bool:
    """
    Quiet hours are in local time. Supports overnight windows, e.g. 22:00 -> 07:00.
    """
    if not start_hhmm or not end_hhmm:
        return False

    try:
        sh, sm = [int(x) for x in start_hhmm.split(":")]
        eh, em = [int(x) for x in end_hhmm.split(":")]
    except Exception:
        return False

    start = now_local.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end = now_local.replace(hour=eh, minute=em, second=0, microsecond=0)

    if start == end:
        return False

    # Overnight window
    if start > end:
        return now_local >= start or now_local < end

    return start <= now_local < end


def process_due_reminders() -> None:
    notifier = build_notifier()
    now = now_utc()
    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)

    with get_conn() as conn:
        quiet_start = _get_setting(conn, "quiet_start", "23:00")
        quiet_end = _get_setting(conn, "quiet_end", "07:00")
        if _in_quiet_hours(now_local, quiet_start, quiet_end):
            # Don't send during quiet hours; reminders will send once quiet hours ends.
            return

        rows = conn.execute(
            """
            SELECT id, entity_type, entity_id, remind_at_utc, message
            FROM reminders
            WHERE sent_at_utc IS NULL AND remind_at_utc <= ?
            ORDER BY remind_at_utc ASC
            LIMIT 25
            """,
            (now.isoformat(),),
        ).fetchall()

        for r in rows:
            notifier.send("Reminder", r["message"])
            conn.execute(
                "UPDATE reminders SET sent_at_utc = ? WHERE id = ?",
                (now.isoformat(), r["id"]),
            )

        conn.commit()


def start_scheduler(timezone_name: str) -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=timezone_name)
    sched.add_job(
        process_due_reminders,
        trigger=IntervalTrigger(seconds=30),
        id="due_reminders",
        replace_existing=True,
    )
    sched.start()
    return sched
