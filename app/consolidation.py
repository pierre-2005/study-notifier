"""Non-destructive, idempotent import of the obsolete task-list database.

Only original administrator records are imported: classic tables have no owner_id.
The old rows remain for backup/recovery and legacy reminder references.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.db import get_conn
from app.config import settings

def consolidate_todos():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS life_legacy_todo_map (
            todo_id INTEGER PRIMARY KEY,
            task_id INTEGER UNIQUE REFERENCES life_tasks(id) ON DELETE SET NULL,
            imported_at TEXT NOT NULL)''')
        admin = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if not admin:
            conn.commit()
            return 0
        count = 0
        todos = conn.execute("SELECT id,title,notes,due_at_utc,status,created_at_utc,updated_at_utc FROM todos ORDER BY id").fetchall()
        for t in todos:
            if conn.execute('SELECT 1 FROM life_legacy_todo_map WHERE todo_id=?',(t['id'],)).fetchone():
                continue
            due = None
            if t['due_at_utc']:
                try:
                    dt = datetime.fromisoformat(t['due_at_utc'].replace('Z','+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    due = dt.astimezone(ZoneInfo(settings.timezone)).date().isoformat()
                except (ValueError, KeyError):
                    pass
            ts = datetime.now(timezone.utc).isoformat()
            old_status = t['status'] if t['status'] in ('todo','doing','done') else 'todo'
            cur = conn.execute('''INSERT INTO life_tasks
                (owner_id,title,description,status,priority,area,due_on,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)''',
                (admin['id'],t['title'],t['notes'] or '',old_status,'normal','Personal',due,
                 t['created_at_utc'] or ts,t['updated_at_utc'] or ts))
            conn.execute('INSERT INTO life_legacy_todo_map(todo_id,task_id,imported_at) VALUES(?,?,?)',
                         (t['id'],cur.lastrowid,ts))
            count += 1
        conn.commit()
        return count

def mirror_legacy_status(conn, task_id, status):
    row = conn.execute('SELECT todo_id FROM life_legacy_todo_map WHERE task_id=?',(task_id,)).fetchone()
    if row:
        conn.execute('UPDATE todos SET status=?,updated_at_utc=? WHERE id=?',
                     ('done' if status=='done' else 'doing' if status=='doing' else 'todo',
                      datetime.now(timezone.utc).isoformat(),row['todo_id']))
