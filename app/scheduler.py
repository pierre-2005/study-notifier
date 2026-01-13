from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import timezone
from app.db import get_conn
from app.timeutil import now_utc
from app.notifier import build_notifier

def process_due_reminders() -> None:
    notifier = build_notifier()
    now = now_utc()

    with get_conn() as conn:
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
            title = "Reminder"
            body = r["message"]
            notifier.send(title, body)
            conn.execute(
                "UPDATE reminders SET sent_at_utc = ? WHERE id = ?",
                (now.isoformat(), r["id"]),
            )

        conn.commit()

def start_scheduler(timezone_name: str) -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=timezone_name)
    sched.add_job(process_due_reminders, trigger=IntervalTrigger(seconds=30), id="due_reminders", replace_existing=True)
    sched.start()
    return sched
