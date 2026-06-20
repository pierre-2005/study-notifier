from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.db import get_conn
from app.timeutil import now_utc
from app.notifier import build_notifier
from app.config import settings


def _get_setting(conn, key: str, default: str) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _in_quiet_hours(now_local: datetime, start_hhmm: str, end_hhmm: str) -> bool:
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

    if start > end:
        return now_local >= start or now_local < end

    return start <= now_local < end


def _safe_send(notifier, title: str, body: str) -> bool:
    try:
        return bool(notifier.send(title, body))
    except Exception as e:
        print(f"[scheduler] notification failed: {e}")
        return False

def process_due_reminders() -> None:
    notifier = build_notifier()
    now = now_utc()
    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)

    with get_conn() as conn:
        quiet_start = _get_setting(conn, "quiet_start", "23:00")
        quiet_end = _get_setting(conn, "quiet_end", "07:00")
        if _in_quiet_hours(now_local, quiet_start, quiet_end):
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
            ok = _safe_send(notifier, "Reminder", r["message"])
            if ok:
                conn.execute(
                    "UPDATE reminders SET sent_at_utc = ? WHERE id = ?",
                    (now.isoformat(), r["id"]),
                )

        conn.commit()


def process_todo_digest() -> None:
    notifier = build_notifier()
    now = now_utc()

    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)

    with get_conn() as conn:
        quiet_start = _get_setting(conn, "quiet_start", "23:00")
        quiet_end = _get_setting(conn, "quiet_end", "07:00")
        if _in_quiet_hours(now_local, quiet_start, quiet_end):
            return

        enabled = _get_setting(conn, "todo_reminder_enabled", "off").strip().lower() == "on"
        if not enabled:
            return

        try:
            minutes = int(_get_setting(conn, "todo_reminder_minutes", "60"))
        except Exception:
            minutes = 60

        last_iso = (_get_setting(conn, "todo_reminder_last_sent_utc", "") or "").strip()
        last_dt = None
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(last_iso)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
            except Exception:
                last_dt = None

        if last_dt is None:
            # If it's never been sent, start the clock now (prevents immediate spam)
            conn.execute(
                "UPDATE app_settings SET value=? WHERE key='todo_reminder_last_sent_utc'",
                (now.isoformat(),),
            )
            conn.commit()
            return

        elapsed = (now - last_dt).total_seconds()
        if elapsed < minutes * 60:
            return

        todos = conn.execute(
            """
            SELECT id, title, due_at_utc, status
            FROM todos
            WHERE status != 'done'
            ORDER BY (due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC
            LIMIT 8
            """
        ).fetchall()

        if not todos:
            # Don't spam "nothing to do" reminders
            conn.execute(
                "UPDATE app_settings SET value=? WHERE key='todo_reminder_last_sent_utc'",
                (now.isoformat(),),
            )
            conn.commit()
            return

        lines = []
        for t in todos:
            lines.append(f"- {t['title']}")

        body = "Open to-dos:\n" + "\n".join(lines)

        ok = _safe_send(notifier, "To-Do reminder", body)
        if ok:
            conn.execute(
                "UPDATE app_settings SET value=? WHERE key='todo_reminder_last_sent_utc'",
                (now.isoformat(),),
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

    # Check every minute; only sends if the saved interval has elapsed
    sched.add_job(
        process_todo_digest,
        trigger=IntervalTrigger(seconds=60),
        id="todo_digest",
        replace_existing=True,
    )

    sched.start()
    return sched
