from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, Request

from app.db import get_conn

OWNER_TABLES = (
    "courses",
    "items",
    "reminders",
    "jobs",
    "todos",
    "expenses",
    "class_meetings",
    "events",
)

DEFAULT_USER_SETTINGS = {
    "assignment_template_minutes": "10080,4320,1440,180",
    "exam_template_minutes": "10080,4320,1440,120,30",
    "lab_template_minutes": "4320,1440,180,60",
    "expense_template_minutes": "4320,1440,180",
    "expense_dayof_local_time": "09:00",
    "quiet_start": "23:00",
    "quiet_end": "07:00",
    "todo_reminder_enabled": "off",
    "todo_reminder_minutes": "60",
    "todo_reminder_last_sent_utc": "",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_tenancy_schema() -> None:
    """Add ownership to legacy personal tables and create per-user settings.

    owner_user_id intentionally starts nullable so existing installations can be
    upgraded before the bootstrap administrator is resolved. `claim_legacy_data`
    assigns legacy rows once an administrator exists.
    """
    with get_conn() as conn:
        for table in OWNER_TABLES:
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "owner_user_id" not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN owner_user_id INTEGER")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_owner ON {table}(owner_user_id)")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
              user_id INTEGER NOT NULL,
              key TEXT NOT NULL,
              value TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              PRIMARY KEY(user_id, key),
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_notification_devices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              label TEXT NOT NULL,
              provider TEXT NOT NULL DEFAULT 'ntfy' CHECK(provider IN ('ntfy')),
              topic TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              UNIQUE(user_id, topic),
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_notification_devices_user
              ON user_notification_devices(user_id, enabled, id);
            """
        )
        conn.commit()


def claim_legacy_data(owner_user_id: int) -> None:
    """Assign rows created before multi-user support to the bootstrap admin."""
    if not owner_user_id:
        return
    with get_conn() as conn:
        for table in OWNER_TABLES:
            conn.execute(
                f"UPDATE {table} SET owner_user_id=? WHERE owner_user_id IS NULL",
                (owner_user_id,),
            )
        conn.commit()


def request_user(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def request_user_id(request: Request) -> int:
    return int(request_user(request)["id"])


def owned_row(conn, table: str, row_id: int, user_id: int):
    if table not in OWNER_TABLES:
        raise ValueError(f"Unsupported owned table: {table}")
    return conn.execute(
        f"SELECT * FROM {table} WHERE id=? AND owner_user_id=?",
        (row_id, user_id),
    ).fetchone()


def require_owned_row(conn, table: str, row_id: int, user_id: int, label: str = "Item"):
    row = owned_row(conn, table, row_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return row


def get_user_setting(conn, user_id: int, key: str, default: str | None = None) -> str:
    row = conn.execute(
        "SELECT value FROM user_settings WHERE user_id=? AND key=?",
        (user_id, key),
    ).fetchone()
    if row:
        return row["value"]

    # Preserve existing installations by treating app_settings as deployment defaults.
    legacy = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    if legacy:
        return legacy["value"]
    if default is not None:
        return default
    return DEFAULT_USER_SETTINGS.get(key, "")


def set_user_setting(conn, user_id: int, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO user_settings(user_id,key,value,updated_at_utc)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at_utc=excluded.updated_at_utc
        """,
        (user_id, key, value, now_iso()),
    )


def list_notification_devices(user_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM user_notification_devices WHERE user_id=? ORDER BY enabled DESC, label COLLATE NOCASE",
            (user_id,),
        ).fetchall()


def create_notification_device(user_id: int, label: str, topic: str) -> int:
    label = " ".join((label or "Phone").split()).strip()[:80] or "Phone"
    topic = "".join((topic or "").strip().split())[:180]
    if not topic:
        raise ValueError("A notification topic is required")
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO user_notification_devices(user_id,label,provider,topic,enabled,created_at_utc,updated_at_utc)
            VALUES(?,?, 'ntfy', ?, 1, ?, ?)
            ON CONFLICT(user_id,topic) DO UPDATE SET label=excluded.label, enabled=1, updated_at_utc=excluded.updated_at_utc
            """,
            (user_id, label, topic, ts, ts),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def delete_notification_device(user_id: int, device_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM user_notification_devices WHERE id=? AND user_id=?", (device_id, user_id))
        conn.commit()


def set_notification_device_enabled(user_id: int, device_id: int, enabled: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_notification_devices SET enabled=?, updated_at_utc=? WHERE id=? AND user_id=?",
            (1 if enabled else 0, now_iso(), device_id, user_id),
        )
        conn.commit()


def get_notification_device(user_id: int, device_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM user_notification_devices WHERE id=? AND user_id=?",
            (device_id, user_id),
        ).fetchone()
