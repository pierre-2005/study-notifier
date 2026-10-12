from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.db import get_conn, _ensure_column
from app.meta import APP_VERSION

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION
router = APIRouter(prefix="/timers", tags=["timers"])


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def init_timer_schema() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS timers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              label TEXT NOT NULL,
              duration_seconds INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running','paused','done')),
              started_at_utc TEXT,
              remaining_seconds INTEGER,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              completed_at_utc TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_timers_user_status ON timers(user_id,status,updated_at_utc DESC);
            """
        )
        _ensure_column(conn, "timers", "task_id", "task_id INTEGER REFERENCES life_tasks(id) ON DELETE SET NULL")
        _ensure_column(conn, "timers", "kind", "kind TEXT NOT NULL DEFAULT 'general'")
        conn.commit()


def _user(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def _remaining(row) -> int:
    if row["status"] == "done":
        return 0
    if row["status"] == "paused":
        return max(0, int(row["remaining_seconds"] or 0))
    if not row["started_at_utc"]:
        return max(0, int(row["duration_seconds"] or 0))
    start = datetime.fromisoformat(row["started_at_utc"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    base = int(row["remaining_seconds"] if row["remaining_seconds"] is not None else row["duration_seconds"])
    return max(0, base - int((now_utc() - start).total_seconds()))


def active_timer_for_user(user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM timers WHERE user_id=? AND status IN ('running','paused') ORDER BY updated_at_utc DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row) | {"remaining": _remaining(row)}


@router.get("", response_class=HTMLResponse)
def timers_page(request: Request):
    user = _user(request)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM timers WHERE user_id=? ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'paused' THEN 1 ELSE 2 END, updated_at_utc DESC LIMIT 40", (user["id"],)).fetchall()
    timers = [dict(r) | {"remaining": _remaining(r)} for r in rows]
    return templates.TemplateResponse(request, "timers.html", {"request": request, "timers": timers})


@router.post("/new")
def create_timer(request: Request, label: str = Form("Focus timer"), minutes: int = Form(25), seconds: int = Form(0), task_id: str = Form(""), next_page: str = Form("/timers"), kind: str = Form("general")):
    user = _user(request)
    duration = max(1, min(24 * 3600, int(minutes or 0) * 60 + int(seconds or 0)))
    ts = now_iso()
    with get_conn() as conn:
        tid = int(task_id) if task_id.isdigit() else None
        if tid:
            from app.lifeos import task_access
            task_access(conn, int(user["id"]), tid, edit=False)
        conn.execute(
            "INSERT INTO timers(user_id,label,task_id,kind,duration_seconds,status,started_at_utc,remaining_seconds,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,'running',?,?,?,?)",
            (user["id"], (label or "Timer").strip()[:120], tid, kind if kind in ('general','focus','break') else 'general', duration, ts, duration, ts, ts),
        )
        conn.commit()
    return RedirectResponse(next_page if next_page.startswith('/life') and not next_page.startswith('//') else '/life/focus', status_code=303)


@router.post("/{timer_id}/pause")
def pause_timer(request: Request, timer_id: int):
    user = _user(request)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM timers WHERE id=? AND user_id=?", (timer_id, user["id"])).fetchone()
        if row and row["status"] == "running":
            remaining = _remaining(row)
            conn.execute("UPDATE timers SET status='paused',remaining_seconds=?,started_at_utc=NULL,updated_at_utc=? WHERE id=?", (remaining, now_iso(), timer_id))
            conn.commit()
    return RedirectResponse("/life/focus", status_code=303)


@router.post("/{timer_id}/resume")
def resume_timer(request: Request, timer_id: int):
    user = _user(request)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM timers WHERE id=? AND user_id=?", (timer_id, user["id"])).fetchone()
        if row and row["status"] == "paused" and int(row["remaining_seconds"] or 0) > 0:
            ts = now_iso()
            conn.execute("UPDATE timers SET status='running',started_at_utc=?,updated_at_utc=? WHERE id=?", (ts, ts, timer_id))
            conn.commit()
    return RedirectResponse("/life/focus", status_code=303)


@router.post("/{timer_id}/restart")
def restart_timer(request: Request, timer_id: int):
    user = _user(request)
    ts = now_iso()
    with get_conn() as conn:
        conn.execute(
            "UPDATE timers SET status='running',started_at_utc=?,remaining_seconds=duration_seconds,completed_at_utc=NULL,updated_at_utc=? WHERE id=? AND user_id=?",
            (ts, ts, timer_id, user["id"]),
        )
        conn.commit()
    return RedirectResponse("/life/focus", status_code=303)


@router.post("/{timer_id}/complete")
def complete_timer(request: Request, timer_id: int):
    user = _user(request)
    ts = now_iso()
    with get_conn() as conn:
        timer = conn.execute("SELECT * FROM timers WHERE id=? AND user_id=?", (timer_id, user['id'])).fetchone()
        if timer and timer['status'] != 'done':
            elapsed = max(0, timer['duration_seconds'] - _remaining(timer))
            conn.execute(
                "UPDATE timers SET status='done',remaining_seconds=0,started_at_utc=NULL,completed_at_utc=?,updated_at_utc=? WHERE id=? AND user_id=?",
                (ts, ts, timer_id, user["id"]),
            )
            if elapsed >= 60 and (timer['kind']=='focus' or timer['task_id'] is not None):
                from app.lifeos import today, task_access
                pid = None
                tid = timer['task_id']
                if tid:
                    task = task_access(conn, int(user['id']), tid)
                    pid = task['project_id']
                conn.execute("INSERT INTO life_time_entries(owner_id,task_id,project_id,minutes,note,occurred_on,created_at) VALUES(?,?,?,?,?,?,?)",
                             (user['id'],tid,pid,min(1440,round(elapsed/60)),timer['label'],today(),ts))
            conn.commit()
    if request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"ok": True})
    return RedirectResponse("/life/focus", status_code=303)


@router.post("/{timer_id}/delete")
def delete_timer(request: Request, timer_id: int):
    user = _user(request)
    with get_conn() as conn:
        conn.execute("DELETE FROM timers WHERE id=? AND user_id=?", (timer_id, user["id"]))
        conn.commit()
    return RedirectResponse("/life/focus", status_code=303)
