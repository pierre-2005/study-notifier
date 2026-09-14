from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.db import get_conn
from app.timeutil import now_utc
from app.config import settings
from app.tenancy import get_user_setting, set_user_setting
from app.notifications import send_user_notification


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


def process_due_reminders() -> None:
    now = now_utc()
    now_local = datetime.now(ZoneInfo(settings.timezone))

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.owner_user_id, r.message
            FROM reminders r
            JOIN users u ON u.id=r.owner_user_id
            WHERE r.sent_at_utc IS NULL
              AND r.remind_at_utc <= ?
              AND u.approved=1 AND u.active=1
            ORDER BY r.remind_at_utc ASC
            LIMIT 100
            """,
            (now.isoformat(),),
        ).fetchall()

        for r in rows:
            uid = int(r["owner_user_id"])
            quiet_start = get_user_setting(conn, uid, "quiet_start", "23:00")
            quiet_end = get_user_setting(conn, uid, "quiet_end", "07:00")
            if _in_quiet_hours(now_local, quiet_start, quiet_end):
                continue
            try:
                ok = send_user_notification(uid, "Reminder", r["message"])
            except Exception as exc:
                print(f"[scheduler] notification failed for user {uid}: {exc}")
                ok = False
            if ok:
                conn.execute(
                    "UPDATE reminders SET sent_at_utc=? WHERE id=? AND owner_user_id=?",
                    (now.isoformat(), r["id"], uid),
                )
        conn.commit()


def process_todo_digest() -> None:
    now = now_utc()
    now_local = datetime.now(ZoneInfo(settings.timezone))

    with get_conn() as conn:
        users = conn.execute(
            "SELECT id FROM users WHERE approved=1 AND active=1 ORDER BY id"
        ).fetchall()

        for user in users:
            uid = int(user["id"])
            if get_user_setting(conn, uid, "todo_reminder_enabled", "off").strip().lower() != "on":
                continue

            quiet_start = get_user_setting(conn, uid, "quiet_start", "23:00")
            quiet_end = get_user_setting(conn, uid, "quiet_end", "07:00")
            if _in_quiet_hours(now_local, quiet_start, quiet_end):
                continue

            try:
                minutes = int(get_user_setting(conn, uid, "todo_reminder_minutes", "60"))
            except Exception:
                minutes = 60

            last_iso = (get_user_setting(conn, uid, "todo_reminder_last_sent_utc", "") or "").strip()
            last_dt = None
            if last_iso:
                try:
                    last_dt = datetime.fromisoformat(last_iso)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            if last_dt is None:
                set_user_setting(conn, uid, "todo_reminder_last_sent_utc", now.isoformat())
                continue
            if (now - last_dt).total_seconds() < minutes * 60:
                continue

            todos = conn.execute(
                """
                SELECT title FROM todos
                WHERE owner_user_id=? AND status!='done'
                ORDER BY (due_at_utc IS NULL) ASC, due_at_utc ASC, updated_at_utc DESC
                LIMIT 8
                """,
                (uid,),
            ).fetchall()

            # Advance the clock even when there is nothing open so the scheduler
            # stays predictable without sending empty notifications.
            if not todos:
                set_user_setting(conn, uid, "todo_reminder_last_sent_utc", now.isoformat())
                continue

            body = "Open to-dos:\n" + "\n".join(f"- {t['title']}" for t in todos)
            try:
                ok = send_user_notification(uid, "To-Do reminder", body)
            except Exception as exc:
                print(f"[scheduler] to-do notification failed for user {uid}: {exc}")
                ok = False
            if ok:
                set_user_setting(conn, uid, "todo_reminder_last_sent_utc", now.isoformat())

        conn.commit()


def start_scheduler(timezone_name: str) -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=timezone_name)
    sched.add_job(process_due_reminders, IntervalTrigger(seconds=30), id="due_reminders", replace_existing=True)
    sched.add_job(process_todo_digest, IntervalTrigger(seconds=60), id="todo_digest", replace_existing=True)
    sched.start()
    return sched
