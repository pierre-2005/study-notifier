from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone

from app.db import get_conn
import re
import json

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
        # Additive migration, preserving all existing users and credentials.
        existing={r[1] for r in conn.execute("PRAGMA table_info(users)")}
        columns={"email":"TEXT", "email_verified":"INTEGER NOT NULL DEFAULT 0",
                 "auth_version":"INTEGER NOT NULL DEFAULT 1", "must_change_password":"INTEGER NOT NULL DEFAULT 0",
                 "permissions_json":"TEXT NOT NULL DEFAULT '{}'"}
        for name,ddl in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {ddl}")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(lower(email)) WHERE email IS NOT NULL AND email != ''")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS auth_email_tokens (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          purpose TEXT NOT NULL CHECK(purpose IN ('verify_email','password_reset')),
          token_hash TEXT NOT NULL UNIQUE,
          candidate_email TEXT,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL,
          used_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_auth_email_tokens_user ON auth_email_tokens(user_id,purpose,created_at);
        CREATE TABLE IF NOT EXISTS auth_audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor_id INTEGER,
          target_id INTEGER,
          action TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(actor_id) REFERENCES users(id),
          FOREIGN KEY(target_id) REFERENCES users(id)
        );
        """)
        conn.commit()


def ensure_bootstrap_admin(username: str, password: str) -> None:
    username = (username or "").strip()
    if not username or not password:
        return
    with get_conn() as conn:
        row = conn.execute("SELECT id, role, approved, active, password_hash FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if row:
            # APP_PASSWORD is bootstrap-only. Never silently overwrite an administrator's
            # password or reactivate a disabled account on every deployment.
            # Existing deployments have already initialized the bootstrap account.
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


def create_pending_user(username: str, display_name: str, password: str, email: str = "") -> tuple[bool, str]:
    username = (username or "").strip()
    display_name = (display_name or "").strip() or username
    if len(username) < 3 or len(username) > 40:
        return False, "Username must be between 3 and 40 characters."
    if not all(ch.isalnum() or ch in "._-" for ch in username):
        return False, "Username can only contain letters, numbers, periods, underscores, and hyphens."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    email=(email or '').strip().lower()
    if email and (len(email)>254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email)):
        return False,"Enter a valid email address."
    with get_conn() as conn:
        if email and conn.execute("SELECT 1 FROM users WHERE lower(email)=?",(email,)).fetchone():
            return False,"That email address is already linked to an account."
        if conn.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone():
            return False, "That username is already taken."
        conn.execute(
            """
            INSERT INTO users(username, display_name, password_hash, role, approved, active, created_at_utc, email)
            VALUES(?,?,?,?,0,1,?,?)
            """,
            (username, display_name[:80], hash_password(password), "member", _now_iso(), email or None),
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

# Capabilities are grantable independently of the administrator role.
# IMPORTANT: Legacy administrator-owned academic/finance tables are NOT exposed
# through these flags, because they are not fully isolated per user.
PERMISSION_LABELS = {
    "projects_create": "Create projects",
    "projects_share": "Share projects and spaces",
    "calendar_connect": "Connect external calendars",
    "files_upload": "Upload project files",
    "import_tasks": "Import task files",
    "devices_manage": "Manage notification devices",
}

def user_capabilities(user):
    if user["role"]=="admin":
        return {k:True for k in PERMISSION_LABELS}
    try:
        values=json.loads(user["permissions_json"] or '{}')
    except (ValueError,TypeError):
        values={}
    return {k:values.get(k, True) is not False for k in PERMISSION_LABELS}


def set_user_capabilities(target_id, values, actor_id):
    with get_conn() as conn:
        row=conn.execute("SELECT role FROM users WHERE id=?",(target_id,)).fetchone()
        if not row or row['role']=='admin': return False
        prefs={k:bool(values.get(k,False)) for k in PERMISSION_LABELS}
        conn.execute("UPDATE users SET permissions_json=? WHERE id=?",(json.dumps(prefs),target_id))
        conn.execute("INSERT INTO auth_audit_log(actor_id,target_id,action,created_at) VALUES(?,?,?,?)",
                     (actor_id,target_id,'permissions_updated',_now_iso()))
        conn.commit()
        return True


def update_user_password(target_id,password,actor_id=None,temporary=False):
    if len(password or '')<12 or len(password)>256:
        raise ValueError('Use a password of 12 to 256 characters.')
    with get_conn() as conn:
        row=conn.execute("SELECT id FROM users WHERE id=?",(target_id,)).fetchone()
        if not row: raise ValueError('Account not found.')
        conn.execute("""UPDATE users SET password_hash=?,auth_version=auth_version+1,
                      must_change_password=? WHERE id=?""",
                     (hash_password(password),1 if temporary else 0,target_id))
        conn.execute("UPDATE auth_email_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL",(_now_iso(),target_id))
        conn.execute("INSERT INTO auth_audit_log(actor_id,target_id,action,created_at) VALUES(?,?,?,?)",
                     (actor_id,target_id,'password_admin_reset' if temporary else 'password_changed',_now_iso()))
        conn.commit()
