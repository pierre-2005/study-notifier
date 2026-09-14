from __future__ import annotations

from app.config import settings
from app.db import get_conn
from app.notifier.ntfy import NtfyNotifier


def send_user_notification(user_id: int, title: str, message: str) -> bool:
    """Send a notification to every enabled device belonging to one user.

    For upgraded single-user installations, the global NTFY_TOPIC remains an
    administrator fallback until a device is added in Settings.
    """
    with get_conn() as conn:
        devices = conn.execute(
            "SELECT topic FROM user_notification_devices WHERE user_id=? AND enabled=1 ORDER BY id",
            (user_id,),
        ).fetchall()
        user = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()

    topics = [d["topic"] for d in devices if d["topic"]]
    if not topics and user and user["role"] == "admin" and settings.ntfy_topic:
        topics = [settings.ntfy_topic]

    if not topics:
        return False

    any_ok = False
    for topic in topics:
        try:
            any_ok = NtfyNotifier(settings.ntfy_base_url, topic).send(title, message) or any_ok
        except Exception as exc:
            print(f"[notifications] failed for user {user_id}: {exc}")
    return any_ok
