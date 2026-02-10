import sqlite3
from pathlib import Path
import os

DB_PATH = Path(os.getenv("STUDY_NOTIFIER_DB", "study_notifier.db"))

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  term TEXT,
  color TEXT,
  created_at_utc TEXT NOT NULL
);

-- IMPORTANT: allow lab in type
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('assignment','exam','lab')),
  title TEXT NOT NULL,
  notes TEXT,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
  priority INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 1 AND 5),
  weight REAL,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL,
  FOREIGN KEY(course_id) REFERENCES courses(id)
);

CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  remind_at_utc TEXT NOT NULL,
  message TEXT NOT NULL,
  sent_at_utc TEXT,
  created_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(sent_at_utc, remind_at_utc);
CREATE INDEX IF NOT EXISTS idx_reminders_entity ON reminders(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company TEXT NOT NULL,
  role TEXT NOT NULL,
  link TEXT,
  status TEXT NOT NULL DEFAULT 'interested'
    CHECK(status IN ('interested','applied','interview','offer','rejected')),
  applied_at_utc TEXT,
  followup_at_utc TEXT,
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  notes TEXT,
  due_at_utc TEXT,
  status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_todos_status_due ON todos(status, due_at_utc);

-- Include recurrence columns in base schema for new installs
CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  category TEXT,
  amount REAL NOT NULL,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unpaid' CHECK(status IN ('unpaid','paid')),
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL,
  recurrence TEXT NOT NULL DEFAULT 'none',
  recurrence_interval INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_expenses_due ON expenses(status, due_at_utc);

CREATE TABLE IF NOT EXISTS class_meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
  start_time_local TEXT NOT NULL, -- "HH:MM"
  duration_minutes INTEGER NOT NULL DEFAULT 50,
  location TEXT,
  remind_before_minutes INTEGER NOT NULL DEFAULT 15,
  notes TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'meeting',
  location TEXT,
  start_at_utc TEXT NOT NULL,
  end_at_utc TEXT,
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Make sure FK constraints actually enforce
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _ensure_column(conn, table: str, col_name: str, col_def_sql: str) -> None:
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col_name in cols:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def_sql}")


def _upsert_setting(conn, key: str, value: str) -> None:
    try:
        conn.execute(
            "INSERT INTO app_settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    except Exception:
        row = conn.execute("SELECT key FROM app_settings WHERE key=?", (key,)).fetchone()
        if row:
            conn.execute("UPDATE app_settings SET value=? WHERE key=?", (value, key))
        else:
            conn.execute("INSERT INTO app_settings(key, value) VALUES(?, ?)", (key, value))


def _migrate_items_allow_lab(conn) -> None:
    """
    Existing DBs might have:
      CHECK(type IN ('assignment','exam'))
    SQLite cannot ALTER a CHECK constraint directly, so we rebuild the table.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='items'"
    ).fetchone()
    if not row or not row["sql"]:
        return

    create_sql = row["sql"]

    # Already supports lab -> nothing to do
    if "('assignment','exam','lab')" in create_sql or "('assignment', 'exam', 'lab')" in create_sql:
        return

    # Only migrate if we detect the old constraint
    if "('assignment','exam')" not in create_sql and "('assignment', 'exam')" not in create_sql:
        return

    conn.execute("PRAGMA foreign_keys=OFF;")
    conn.execute("BEGIN;")

    # Recreate table with updated constraint
    conn.execute("""
    CREATE TABLE items_new (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      course_id INTEGER NOT NULL,
      type TEXT NOT NULL CHECK(type IN ('assignment','exam','lab')),
      title TEXT NOT NULL,
      notes TEXT,
      due_at_utc TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
      priority INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 1 AND 5),
      weight REAL,
      created_at_utc TEXT NOT NULL,
      updated_at_utc TEXT NOT NULL,
      FOREIGN KEY(course_id) REFERENCES courses(id)
    );
    """)

    # Copy rows exactly
    conn.execute("""
    INSERT INTO items_new (id, course_id, type, title, notes, due_at_utc, status, priority, weight, created_at_utc, updated_at_utc)
    SELECT id, course_id, type, title, notes, due_at_utc, status, priority, weight, created_at_utc, updated_at_utc
    FROM items;
    """)

    conn.execute("DROP TABLE items;")
    conn.execute("ALTER TABLE items_new RENAME TO items;")

    conn.execute("COMMIT;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA foreign_key_check;")


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)

        # --- Safe migrations for existing DBs ---
        # expenses recurrence columns (older DBs)
        _ensure_column(conn, "expenses", "recurrence", "recurrence TEXT NOT NULL DEFAULT 'none'")
        _ensure_column(conn, "expenses", "recurrence_interval", "recurrence_interval INTEGER NOT NULL DEFAULT 1")

        # items type constraint upgrade to allow 'lab'
        _migrate_items_allow_lab(conn)

        # --- Default settings ---
        defaults = {
            "assignment_template_minutes": "10080,4320,1440,180",  # 7d,3d,24h,3h
            "exam_template_minutes": "10080,4320,1440,120,30",     # 7d,3d,24h,2h,30m
            "lab_template_minutes": "10080,4320,1440,180",         # safe default (same as assignment)
            "expense_template_minutes": "4320,1440,180",           # 3d,24h,3h
            "expense_dayof_local_time": "09:00",
            "quiet_start": "23:00",
            "quiet_end": "07:00",
            "todo_reminder_enabled": "off",
            "todo_reminder_minutes": "60",
            "todo_reminder_last_sent_utc": "",
        }

        for k, v in defaults.items():
            row = conn.execute("SELECT value FROM app_settings WHERE key=?", (k,)).fetchone()
            if not row:
                _upsert_setting(conn, k, v)

        conn.commit()
