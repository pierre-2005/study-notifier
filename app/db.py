import sqlite3
from pathlib import Path
import os

DB_PATH = Path(os.getenv("STUDY_NOTIFIER_DB", "study_notifier.db"))

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  term TEXT,
  color TEXT,
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('assignment','exam')),
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

-- Polymorphic reminders so we can add new modules later (jobs, etc.)
CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,         -- 'item' or 'job' (expand later)
  entity_id INTEGER NOT NULL,
  remind_at_utc TEXT NOT NULL,
  message TEXT NOT NULL,
  sent_at_utc TEXT,
  created_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(sent_at_utc, remind_at_utc);

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

CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  category TEXT,
  amount REAL NOT NULL,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unpaid' CHECK(status IN ('unpaid','paid')),
  notes TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
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
  kind TEXT NOT NULL DEFAULT 'meeting', -- meeting / personal / other
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
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
