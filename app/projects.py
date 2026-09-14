from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_conn
from app.meta import APP_VERSION
from app.tenancy import request_user_id

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION
router = APIRouter(prefix="/projects", tags=["projects"])

PROJECT_STATUSES = {"idea", "planned", "active", "paused", "done", "archived"}
PROJECT_CATEGORIES = ("Personal", "Study", "Work", "Club", "Side Project", "Other")
PROJECT_PRIORITIES = {"low", "normal", "high", "critical"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_project_schema() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_user_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              category TEXT NOT NULL DEFAULT 'Personal',
              status TEXT NOT NULL DEFAULT 'active',
              priority TEXT NOT NULL DEFAULT 'normal',
              color TEXT NOT NULL DEFAULT '#5b7cfa',
              description TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '',
              start_date TEXT,
              due_date TEXT,
              favorite INTEGER NOT NULL DEFAULT 0,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_projects_owner_status ON projects(owner_user_id, status, updated_at_utc DESC);

            CREATE TABLE IF NOT EXISTS project_tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_id INTEGER NOT NULL,
              title TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
              priority INTEGER NOT NULL DEFAULT 2 CHECK(priority BETWEEN 1 AND 5),
              due_date TEXT,
              notes TEXT NOT NULL DEFAULT '',
              position INTEGER NOT NULL DEFAULT 0,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_project_tasks_project ON project_tasks(project_id, status, position, id);

            CREATE TABLE IF NOT EXISTS project_links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_id INTEGER NOT NULL,
              label TEXT NOT NULL,
              url TEXT NOT NULL,
              created_at_utc TEXT NOT NULL,
              FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()


def _project(conn, user_id: int, project_id: int):
    row = conn.execute("SELECT * FROM projects WHERE id=? AND owner_user_id=?", (project_id, user_id)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


def _normalize_status(value: str) -> str:
    value = (value or "active").strip().lower()
    return value if value in PROJECT_STATUSES else "active"


def _normalize_priority(value: str) -> str:
    value = (value or "normal").strip().lower()
    return value if value in PROJECT_PRIORITIES else "normal"


def project_summary_for_user(user_id: int, limit: int = 6):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT p.*,
                   COUNT(t.id) AS task_count,
                   SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) AS done_count,
                   CASE WHEN COUNT(t.id)=0 THEN 0
                        ELSE ROUND(100.0 * SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) / COUNT(t.id)) END AS progress
            FROM projects p
            LEFT JOIN project_tasks t ON t.project_id=p.id
            WHERE p.owner_user_id=? AND p.status NOT IN ('archived','done')
            GROUP BY p.id
            ORDER BY p.favorite DESC,
                     CASE p.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                     p.updated_at_utc DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


@router.get("", response_class=HTMLResponse)
def projects_home(request: Request, status: str = "open", category: str = "All", q: str = ""):
    uid = request_user_id(request)
    q = (q or "").strip()
    where = ["p.owner_user_id=?"]
    params: list = [uid]
    if status == "open":
        where.append("p.status NOT IN ('done','archived')")
    elif status in PROJECT_STATUSES:
        where.append("p.status=?")
        params.append(status)
    if category and category != "All":
        where.append("p.category=?")
        params.append(category)
    if q:
        where.append("(p.name LIKE ? OR p.description LIKE ? OR p.notes LIKE ?)")
        params.extend([f"%{q}%"] * 3)

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*,
                   COUNT(t.id) AS task_count,
                   SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) AS done_count,
                   CASE WHEN COUNT(t.id)=0 THEN 0
                        ELSE ROUND(100.0 * SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) / COUNT(t.id)) END AS progress
            FROM projects p
            LEFT JOIN project_tasks t ON t.project_id=p.id
            WHERE {' AND '.join(where)}
            GROUP BY p.id
            ORDER BY p.favorite DESC,
                     CASE p.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                     CASE WHEN p.due_date IS NULL OR p.due_date='' THEN 1 ELSE 0 END,
                     p.due_date ASC,
                     p.updated_at_utc DESC
            """,
            tuple(params),
        ).fetchall()

    return templates.TemplateResponse(
        request,
        "projects.html",
        {"request": request, "projects": rows, "categories": PROJECT_CATEGORIES, "filters": {"status": status, "category": category, "q": q}},
    )


@router.get("/new", response_class=HTMLResponse)
def project_new(request: Request):
    return templates.TemplateResponse(request, "project_form.html", {"request": request, "project": None, "categories": PROJECT_CATEGORIES})


@router.post("/new")
def project_create(
    request: Request,
    name: str = Form(...),
    category: str = Form("Personal"),
    status: str = Form("active"),
    priority: str = Form("normal"),
    color: str = Form("#5b7cfa"),
    description: str = Form(""),
    notes: str = Form(""),
    start_date: str = Form(""),
    due_date: str = Form(""),
):
    uid = request_user_id(request)
    name = " ".join((name or "").split()).strip()[:160]
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    if category not in PROJECT_CATEGORIES:
        category = "Other"
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO projects(owner_user_id,name,category,status,priority,color,description,notes,start_date,due_date,created_at_utc,updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (uid, name, category, _normalize_status(status), _normalize_priority(priority), color[:20], description.strip()[:2000], notes.strip()[:10000], start_date or None, due_date or None, ts, ts),
        )
        project_id = cur.lastrowid
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.get("/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: int):
    uid = request_user_id(request)
    with get_conn() as conn:
        project = _project(conn, uid, project_id)
        tasks = conn.execute(
            "SELECT * FROM project_tasks WHERE project_id=? ORDER BY status='done', position, priority DESC, id",
            (project_id,),
        ).fetchall()
        links = conn.execute("SELECT * FROM project_links WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
        total = len(tasks)
        done = sum(1 for t in tasks if t["status"] == "done")
    progress = int(round(100 * done / total)) if total else 0
    return templates.TemplateResponse(
        request,
        "project_detail.html",
        {"request": request, "project": project, "tasks": tasks, "links": links, "progress": progress, "categories": PROJECT_CATEGORIES},
    )


@router.post("/{project_id}/update")
def project_update(
    request: Request,
    project_id: int,
    name: str = Form(...),
    category: str = Form("Personal"),
    status: str = Form("active"),
    priority: str = Form("normal"),
    color: str = Form("#5b7cfa"),
    description: str = Form(""),
    notes: str = Form(""),
    start_date: str = Form(""),
    due_date: str = Form(""),
    favorite: str = Form("off"),
):
    uid = request_user_id(request)
    if category not in PROJECT_CATEGORIES:
        category = "Other"
    with get_conn() as conn:
        _project(conn, uid, project_id)
        conn.execute(
            """
            UPDATE projects SET name=?,category=?,status=?,priority=?,color=?,description=?,notes=?,start_date=?,due_date=?,favorite=?,updated_at_utc=?
            WHERE id=? AND owner_user_id=?
            """,
            (name.strip()[:160], category, _normalize_status(status), _normalize_priority(priority), color[:20], description.strip()[:2000], notes.strip()[:10000], start_date or None, due_date or None, 1 if favorite == "on" else 0, now_iso(), project_id, uid),
        )
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/delete")
def project_delete(request: Request, project_id: int):
    uid = request_user_id(request)
    with get_conn() as conn:
        _project(conn, uid, project_id)
        conn.execute("DELETE FROM projects WHERE id=? AND owner_user_id=?", (project_id, uid))
        conn.commit()
    return RedirectResponse("/projects", status_code=303)


@router.post("/{project_id}/tasks/new")
def task_create(
    request: Request,
    project_id: int,
    title: str = Form(...),
    priority: int = Form(2),
    due_date: str = Form(""),
    notes: str = Form(""),
):
    uid = request_user_id(request)
    ts = now_iso()
    with get_conn() as conn:
        _project(conn, uid, project_id)
        pos = conn.execute("SELECT COALESCE(MAX(position),0)+1 AS p FROM project_tasks WHERE project_id=?", (project_id,)).fetchone()["p"]
        conn.execute(
            "INSERT INTO project_tasks(project_id,title,status,priority,due_date,notes,position,created_at_utc,updated_at_utc) VALUES(?,?,'todo',?,?,?,?,?,?)",
            (project_id, title.strip()[:300], max(1, min(int(priority), 5)), due_date or None, notes.strip()[:2000], pos, ts, ts),
        )
        conn.execute("UPDATE projects SET updated_at_utc=? WHERE id=?", (ts, project_id))
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/tasks/{task_id}/status")
def task_status(request: Request, project_id: int, task_id: int, status: str = Form(...)):
    uid = request_user_id(request)
    status = status if status in {"todo", "doing", "done"} else "todo"
    with get_conn() as conn:
        _project(conn, uid, project_id)
        conn.execute("UPDATE project_tasks SET status=?,updated_at_utc=? WHERE id=? AND project_id=?", (status, now_iso(), task_id, project_id))
        conn.execute("UPDATE projects SET updated_at_utc=? WHERE id=?", (now_iso(), project_id))
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/tasks/{task_id}/delete")
def task_delete(request: Request, project_id: int, task_id: int):
    uid = request_user_id(request)
    with get_conn() as conn:
        _project(conn, uid, project_id)
        conn.execute("DELETE FROM project_tasks WHERE id=? AND project_id=?", (task_id, project_id))
        conn.execute("UPDATE projects SET updated_at_utc=? WHERE id=?", (now_iso(), project_id))
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/links/new")
def link_create(request: Request, project_id: int, label: str = Form(...), url: str = Form(...)):
    uid = request_user_id(request)
    url = (url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    with get_conn() as conn:
        _project(conn, uid, project_id)
        conn.execute(
            "INSERT INTO project_links(project_id,label,url,created_at_utc) VALUES(?,?,?,?)",
            (project_id, label.strip()[:120], url[:1500], now_iso()),
        )
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)


@router.post("/{project_id}/links/{link_id}/delete")
def link_delete(request: Request, project_id: int, link_id: int):
    uid = request_user_id(request)
    with get_conn() as conn:
        _project(conn, uid, project_id)
        conn.execute("DELETE FROM project_links WHERE id=? AND project_id=?", (link_id, project_id))
        conn.commit()
    return RedirectResponse(f"/projects/{project_id}", status_code=303)
