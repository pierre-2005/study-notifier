from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone

from app.db import get_conn

PBKDF2_ITERATIONS = 310_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    password = password or ""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def init_auth_schema() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE COLLATE NOCASE,
              display_name TEXT NOT NULL DEFAULT '',
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'member' CHECK(role IN ('admin','member')),
              approved INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              approved_at_utc TEXT,
              approved_by INTEGER,
              FOREIGN KEY(approved_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_users_approval ON users(approved, active, created_at_utc);
            """
        )
        conn.commit()


def ensure_bootstrap_admin(username: str, password: str) -> None:
    username = (username or "").strip()
    if not username or not password:
        return
    with get_conn() as conn:
        row = conn.execute("SELECT id, role, approved, active, password_hash FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if row:
            # Keep the bootstrap administrator controlled by the deployment
            # credentials. This preserves the pre-1.4 behavior where changing
            # APP_PASSWORD changes the administrator password after a restart.
            password_changed = not verify_password(password, row["password_hash"])
            if row["role"] != "admin" or not row["approved"] or not row["active"] or password_changed:
                conn.execute(
                    """
                    UPDATE users
                    SET role='admin',
                        approved=1,
                        active=1,
                        approved_at_utc=COALESCE(approved_at_utc, ?),
                        password_hash=?
                    WHERE id=?
                    """,
                    (_now_iso(), hash_password(password) if password_changed else row["password_hash"], row["id"]),
                )
                conn.commit()
            return
        conn.execute(
            """
            INSERT INTO users(username, display_name, password_hash, role, approved, active, created_at_utc, approved_at_utc)
            VALUES(?,?,?,?,1,1,?,?)
            """,
            (username, username, hash_password(password), "admin", _now_iso(), _now_iso()),
        )
        conn.commit()


def get_user_by_username(username: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", ((username or "").strip(),)).fetchone()


def get_user_by_id(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def create_pending_user(username: str, display_name: str, password: str) -> tuple[bool, str]:
    username = (username or "").strip()
    display_name = (display_name or "").strip() or username
    if len(username) < 3 or len(username) > 40:
        return False, "Username must be between 3 and 40 characters."
    if not all(ch.isalnum() or ch in "._-" for ch in username):
        return False, "Username can only contain letters, numbers, periods, underscores, and hyphens."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone():
            return False, "That username is already taken."
        conn.execute(
            """
            INSERT INTO users(username, display_name, password_hash, role, approved, active, created_at_utc)
            VALUES(?,?,?,?,0,1,?)
            """,
            (username, display_name[:80], hash_password(password), "member", _now_iso()),
        )
        conn.commit()
    return True, "Account created. An administrator must approve it before you can sign in."


def list_users():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users ORDER BY approved ASC, active DESC, created_at_utc DESC"
        ).fetchall()


def set_user_approval(user_id: int, approved: bool, admin_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET approved=?, approved_at_utc=?, approved_by=? WHERE id=? AND role!='admin'",
            (1 if approved else 0, _now_iso() if approved else None, admin_id if approved else None, user_id),
        )
        conn.commit()


def set_user_active(user_id: int, active: bool) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET active=? WHERE id=? AND role!='admin'", (1 if active else 0, user_id))
        conn.commit()
