from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_conn
from app.meta import APP_VERSION

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["APP_VERSION"] = APP_VERSION
router = APIRouter(prefix="/sections", tags=["sections"])

SECTION_TYPES = {"blank", "grocery"}
SECTION_CATEGORIES = ("Personal", "Study", "Work", "Projects", "Home", "Shared", "Other")
SECTION_ICONS = ["📄", "🛒", "🍽️", "🏠", "📚", "💡", "🎯", "🧾", "✈️", "🧰", "💼", "🧪", "🗂️", "🙏"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_workspace_schema() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspace_sections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_user_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              icon TEXT NOT NULL DEFAULT '📄',
              description TEXT NOT NULL DEFAULT '',
              section_type TEXT NOT NULL DEFAULT 'blank' CHECK(section_type IN ('blank','grocery')),
              content TEXT NOT NULL DEFAULT '',
              show_in_sidebar INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_workspace_sections_owner ON workspace_sections(owner_user_id, updated_at_utc);

            CREATE TABLE IF NOT EXISTS workspace_section_members (
              section_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              can_edit INTEGER NOT NULL DEFAULT 1,
              added_at_utc TEXT NOT NULL,
              PRIMARY KEY(section_id, user_id),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS workspace_checklist_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              content TEXT NOT NULL,
              checked INTEGER NOT NULL DEFAULT 0,
              position INTEGER NOT NULL DEFAULT 0,
              created_by INTEGER NOT NULL,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS grocery_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              default_unit TEXT NOT NULL DEFAULT 'item',
              aisle TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              UNIQUE(section_id, name),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS grocery_list_entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              grocery_item_id INTEGER NOT NULL,
              quantity REAL NOT NULL DEFAULT 1,
              unit TEXT NOT NULL DEFAULT '',
              checked INTEGER NOT NULL DEFAULT 0,
              note TEXT NOT NULL DEFAULT '',
              added_by INTEGER NOT NULL,
              added_at_utc TEXT NOT NULL,
              checked_at_utc TEXT,
              UNIQUE(section_id, grocery_item_id),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(grocery_item_id) REFERENCES grocery_items(id) ON DELETE CASCADE,
              FOREIGN KEY(added_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS grocery_recipes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              section_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              notes TEXT NOT NULL DEFAULT '',
              created_by INTEGER NOT NULL,
              created_at_utc TEXT NOT NULL,
              updated_at_utc TEXT NOT NULL,
              UNIQUE(section_id, name),
              FOREIGN KEY(section_id) REFERENCES workspace_sections(id) ON DELETE CASCADE,
              FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS grocery_recipe_ingredients (
              recipe_id INTEGER NOT NULL,
              grocery_item_id INTEGER NOT NULL,
              quantity REAL NOT NULL DEFAULT 1,
              unit TEXT NOT NULL DEFAULT '',
              PRIMARY KEY(recipe_id, grocery_item_id),
              FOREIGN KEY(recipe_id) REFERENCES grocery_recipes(id) ON DELETE CASCADE,
              FOREIGN KEY(grocery_item_id) REFERENCES grocery_items(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS grocery_price_history (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              grocery_item_id INTEGER NOT NULL,
              purchased_by INTEGER NOT NULL,
              store TEXT NOT NULL DEFAULT '',
              purchased_on TEXT NOT NULL,
              quantity REAL NOT NULL DEFAULT 1,
              total_cost REAL NOT NULL,
              unit_cost REAL NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              created_at_utc TEXT NOT NULL,
              FOREIGN KEY(grocery_item_id) REFERENCES grocery_items(id) ON DELETE CASCADE,
              FOREIGN KEY(purchased_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_grocery_prices_item_date ON grocery_price_history(grocery_item_id, purchased_on DESC, id DESC);
            """
        )
        # Add organization metadata to installations created before v2.0.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(workspace_sections)").fetchall()}
        if "category" not in cols:
            conn.execute("ALTER TABLE workspace_sections ADD COLUMN category TEXT NOT NULL DEFAULT 'Personal'")
        if "color" not in cols:
            conn.execute("ALTER TABLE workspace_sections ADD COLUMN color TEXT NOT NULL DEFAULT '#5b7cfa'")
        if "favorite" not in cols:
            conn.execute("ALTER TABLE workspace_sections ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def ensure_starter_sections(user_id: int) -> None:
    """Create a useful starter workspace for a brand-new account."""
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM workspace_sections WHERE owner_user_id=?", (user_id,)).fetchone()["c"]
        if count:
            return
        ts = now_iso()
        starter = [
            ("Personal HQ", "🏠", "Personal", "#5b7cfa", "Goals, errands, routines, and anything that keeps life moving."),
            ("Study Hub", "📚", "Study", "#7c5ce7", "Courses, study plans, exam prep, and academic notes."),
            ("Work Hub", "💼", "Work", "#0f8a6c", "Work priorities, meeting notes, follow-ups, and references."),
            ("Ideas & Projects", "💡", "Projects", "#d47b22", "Scratchpad for ideas before they become full projects."),
        ]
        for name, icon, category, color, description in starter:
            conn.execute(
                """
                INSERT INTO workspace_sections(owner_user_id,name,icon,description,section_type,content,show_in_sidebar,category,color,favorite,created_at_utc,updated_at_utc)
                VALUES(?,?,?,?,'blank','',1,?,?,0,?,?)
                """,
                (user_id, name, icon, description, category, color, ts, ts),
            )
        conn.commit()


def _user(request: Request):
    user = getattr(request.state, "current_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def _section_access(conn, request: Request, section_id: int, require_edit: bool = False):
    user = _user(request)
    row = conn.execute(
        """
        SELECT s.*,
               CASE WHEN s.owner_user_id=? THEN 1 ELSE COALESCE(m.can_edit, 0) END AS can_edit,
               CASE WHEN s.owner_user_id=? THEN 1 ELSE 0 END AS is_owner
        FROM workspace_sections s
        LEFT JOIN workspace_section_members m ON m.section_id=s.id AND m.user_id=?
        WHERE s.id=? AND (s.owner_user_id=? OR m.user_id IS NOT NULL)
        """,
        (user["id"], user["id"], user["id"], section_id, user["id"]),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Section not found")
    if require_edit and not row["can_edit"]:
        raise HTTPException(status_code=403, detail="You do not have edit access to this section")
    return row


def list_sections_for_user(user_id: int, sidebar_only: bool = False):
    where = "AND s.show_in_sidebar=1" if sidebar_only else ""
    with get_conn() as conn:
        return conn.execute(
            f"""
            SELECT s.*, CASE WHEN s.owner_user_id=? THEN 1 ELSE 0 END AS is_owner,
                   CASE WHEN s.owner_user_id=? THEN 1 ELSE COALESCE(m.can_edit,0) END AS can_edit
            FROM workspace_sections s
            LEFT JOIN workspace_section_members m ON m.section_id=s.id AND m.user_id=?
            WHERE (s.owner_user_id=? OR m.user_id IS NOT NULL) {where}
            ORDER BY s.favorite DESC, s.category COLLATE NOCASE, s.updated_at_utc DESC, s.name COLLATE NOCASE
            """,
            (user_id, user_id, user_id, user_id),
        ).fetchall()


def _template_context(request: Request, **extra):
    ctx = {"request": request, "section_icons": SECTION_ICONS, "section_categories": SECTION_CATEGORIES}
    ctx.update(extra)
    return ctx


@router.get("", response_class=HTMLResponse)
def sections_home(request: Request):
    user = _user(request)
    rows = list_sections_for_user(user["id"])
    return templates.TemplateResponse(request, "sections.html", _template_context(request, sections=rows))


@router.get("/new", response_class=HTMLResponse)
def new_section(request: Request):
    _user(request)
    return templates.TemplateResponse(request, "section_new.html", _template_context(request))


@router.post("/new")
def create_section(
    request: Request,
    name: str = Form(...),
    section_type: str = Form("blank"),
    icon: str = Form("📄"),
    description: str = Form(""),
    category: str = Form("Personal"),
    color: str = Form("#5b7cfa"),
):
    user = _user(request)
    name = (name or "").strip()[:100]
    if not name:
        raise HTTPException(status_code=400, detail="Section name is required")
    section_type = section_type if section_type in SECTION_TYPES else "blank"
    icon = (icon or "📄").strip()[:8] or "📄"
    category = category if category in SECTION_CATEGORIES else "Other"
    color = (color or "#5b7cfa").strip()[:20]
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO workspace_sections(owner_user_id,name,icon,description,section_type,category,color,created_at_utc,updated_at_utc)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (user["id"], name, icon, (description or "").strip()[:500], section_type, category, color, ts, ts),
        )
        section_id = cur.lastrowid
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


@router.get("/{section_id}", response_class=HTMLResponse)
def section_detail(request: Request, section_id: int):
    user = _user(request)
    with get_conn() as conn:
        section = _section_access(conn, request, section_id)
        members = conn.execute(
            """
            SELECT u.id,u.username,u.display_name,m.can_edit
            FROM workspace_section_members m JOIN users u ON u.id=m.user_id
            WHERE m.section_id=? ORDER BY u.display_name COLLATE NOCASE
            """,
            (section_id,),
        ).fetchall()
        shareable_users = conn.execute(
            """
            SELECT id,username,display_name FROM users
            WHERE approved=1 AND active=1 AND id!=? AND id NOT IN (
              SELECT user_id FROM workspace_section_members WHERE section_id=?
            ) ORDER BY display_name COLLATE NOCASE
            """,
            (user["id"], section_id),
        ).fetchall() if section["is_owner"] else []

        if section["section_type"] == "grocery":
            items = conn.execute(
                """
                SELECT gi.*, gle.id AS list_entry_id, gle.quantity AS list_quantity, gle.unit AS list_unit,
                       gle.checked, gle.note AS list_note,
                       (SELECT unit_cost FROM grocery_price_history ph WHERE ph.grocery_item_id=gi.id ORDER BY purchased_on DESC,id DESC LIMIT 1) AS latest_unit_cost,
                       (SELECT unit_cost FROM grocery_price_history ph WHERE ph.grocery_item_id=gi.id ORDER BY purchased_on DESC,id DESC LIMIT 1 OFFSET 1) AS previous_unit_cost,
                       (SELECT total_cost FROM grocery_price_history ph WHERE ph.grocery_item_id=gi.id ORDER BY purchased_on DESC,id DESC LIMIT 1) AS latest_total_cost,
                       (SELECT purchased_on FROM grocery_price_history ph WHERE ph.grocery_item_id=gi.id ORDER BY purchased_on DESC,id DESC LIMIT 1) AS latest_purchase_date,
                       (SELECT store FROM grocery_price_history ph WHERE ph.grocery_item_id=gi.id ORDER BY purchased_on DESC,id DESC LIMIT 1) AS latest_store
                FROM grocery_items gi
                LEFT JOIN grocery_list_entries gle ON gle.grocery_item_id=gi.id AND gle.section_id=gi.section_id
                WHERE gi.section_id=? AND gi.active=1
                ORDER BY COALESCE(gle.checked,0), gi.aisle COLLATE NOCASE, gi.name COLLATE NOCASE
                """,
                (section_id,),
            ).fetchall()
            recipes = conn.execute(
                """
                SELECT r.*, COUNT(ri.grocery_item_id) AS ingredient_count
                FROM grocery_recipes r LEFT JOIN grocery_recipe_ingredients ri ON ri.recipe_id=r.id
                WHERE r.section_id=? GROUP BY r.id ORDER BY r.name COLLATE NOCASE
                """,
                (section_id,),
            ).fetchall()
            ingredients = conn.execute(
                """
                SELECT ri.*, r.name AS recipe_name, gi.name AS item_name, gi.default_unit
                FROM grocery_recipe_ingredients ri
                JOIN grocery_recipes r ON r.id=ri.recipe_id
                JOIN grocery_items gi ON gi.id=ri.grocery_item_id
                WHERE r.section_id=? ORDER BY r.name COLLATE NOCASE, gi.name COLLATE NOCASE
                """,
                (section_id,),
            ).fetchall()
            recipe_map: dict[int, list] = {}
            item_recipe_map: dict[int, list[str]] = {}
            for ing in ingredients:
                recipe_map.setdefault(ing["recipe_id"], []).append(ing)
                item_recipe_map.setdefault(ing["grocery_item_id"], []).append(ing["recipe_name"])
            price_history = conn.execute(
                """
                SELECT ph.*, gi.name AS item_name, u.display_name AS purchased_by_name
                FROM grocery_price_history ph
                JOIN grocery_items gi ON gi.id=ph.grocery_item_id
                JOIN users u ON u.id=ph.purchased_by
                WHERE gi.section_id=? ORDER BY ph.purchased_on DESC,ph.id DESC LIMIT 60
                """,
                (section_id,),
            ).fetchall()
            return templates.TemplateResponse(
                request,
                "section_grocery.html",
                _template_context(
                    request,
                    section=section,
                    members=members,
                    shareable_users=shareable_users,
                    items=items,
                    recipes=recipes,
                    recipe_map=recipe_map,
                    item_recipe_map=item_recipe_map,
                    price_history=price_history,
                    today=date.today().isoformat(),
                ),
            )

        checklist = conn.execute(
            "SELECT * FROM workspace_checklist_items WHERE section_id=? ORDER BY checked,position,id",
            (section_id,),
        ).fetchall()
    return templates.TemplateResponse(
        request,
        "section_blank.html",
        _template_context(request, section=section, checklist=checklist, members=members, shareable_users=shareable_users),
    )


@router.post("/{section_id}/update")
def update_section(
    request: Request,
    section_id: int,
    name: str = Form(...),
    icon: str = Form("📄"),
    description: str = Form(""),
    content: str = Form(""),
    show_in_sidebar: str = Form("off"),
    category: str = Form("Personal"),
    color: str = Form("#5b7cfa"),
    favorite: str = Form("off"),
):
    category = category if category in SECTION_CATEGORIES else "Other"
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute(
            """
            UPDATE workspace_sections SET name=?,icon=?,description=?,content=?,show_in_sidebar=?,category=?,color=?,favorite=?,updated_at_utc=? WHERE id=?
            """,
            ((name or "Untitled").strip()[:100], (icon or "📄").strip()[:8], (description or "").strip()[:500], content or "", 1 if show_in_sidebar == "on" else 0, category, (color or "#5b7cfa")[:20], 1 if favorite == "on" else 0, now_iso(), section_id),
        )
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


@router.post("/{section_id}/delete")
def delete_section(request: Request, section_id: int):
    with get_conn() as conn:
        section = _section_access(conn, request, section_id)
        if not section["is_owner"]:
            raise HTTPException(status_code=403, detail="Only the section owner can delete it")
        conn.execute("DELETE FROM workspace_sections WHERE id=?", (section_id,))
        conn.commit()
    return RedirectResponse("/sections", status_code=303)


@router.post("/{section_id}/share")
def share_section(request: Request, section_id: int, user_id: int = Form(...), can_edit: str = Form("on")):
    with get_conn() as conn:
        section = _section_access(conn, request, section_id)
        if not section["is_owner"]:
            raise HTTPException(status_code=403, detail="Only the section owner can share it")
        valid = conn.execute("SELECT 1 FROM users WHERE id=? AND approved=1 AND active=1", (user_id,)).fetchone()
        if valid:
            conn.execute(
                "INSERT OR REPLACE INTO workspace_section_members(section_id,user_id,can_edit,added_at_utc) VALUES(?,?,?,?)",
                (section_id, user_id, 1 if can_edit == "on" else 0, now_iso()),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


@router.post("/{section_id}/share/{user_id}/remove")
def unshare_section(request: Request, section_id: int, user_id: int):
    with get_conn() as conn:
        section = _section_access(conn, request, section_id)
        if not section["is_owner"]:
            raise HTTPException(status_code=403, detail="Only the section owner can change sharing")
        conn.execute("DELETE FROM workspace_section_members WHERE section_id=? AND user_id=?", (section_id, user_id))
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


@router.post("/{section_id}/checklist/add")
def add_checklist(request: Request, section_id: int, content: str = Form(...)):
    user = _user(request)
    content = (content or "").strip()
    if content:
        with get_conn() as conn:
            _section_access(conn, request, section_id, require_edit=True)
            pos = conn.execute("SELECT COALESCE(MAX(position),0)+1 AS p FROM workspace_checklist_items WHERE section_id=?", (section_id,)).fetchone()["p"]
            ts = now_iso()
            conn.execute(
                "INSERT INTO workspace_checklist_items(section_id,content,position,created_by,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
                (section_id, content[:500], pos, user["id"], ts, ts),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


@router.post("/{section_id}/checklist/{item_id}/toggle")
def toggle_checklist(request: Request, section_id: int, item_id: int):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute("UPDATE workspace_checklist_items SET checked=CASE checked WHEN 1 THEN 0 ELSE 1 END, updated_at_utc=? WHERE id=? AND section_id=?", (now_iso(), item_id, section_id))
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


@router.post("/{section_id}/checklist/{item_id}/delete")
def delete_checklist(request: Request, section_id: int, item_id: int):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute("DELETE FROM workspace_checklist_items WHERE id=? AND section_id=?", (item_id, section_id))
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}", status_code=303)


# Grocery planner actions ----------------------------------------------------
@router.post("/{section_id}/groceries/items/add")
def grocery_add_item(request: Request, section_id: int, name: str = Form(...), unit: str = Form("item"), aisle: str = Form("")):
    user = _user(request)
    name = (name or "").strip()
    if not name:
        return RedirectResponse(f"/sections/{section_id}", status_code=303)
    with get_conn() as conn:
        section = _section_access(conn, request, section_id, require_edit=True)
        if section["section_type"] != "grocery":
            raise HTTPException(status_code=400, detail="Not a grocery section")
        ts = now_iso()
        conn.execute(
            "INSERT OR IGNORE INTO grocery_items(section_id,name,default_unit,aisle,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
            (section_id, name[:120], (unit or "item").strip()[:30], (aisle or "").strip()[:80], ts, ts),
        )
        item = conn.execute("SELECT id,default_unit FROM grocery_items WHERE section_id=? AND name=?", (section_id, name[:120])).fetchone()
        if item:
            conn.execute(
                """
                INSERT INTO grocery_list_entries(section_id,grocery_item_id,quantity,unit,added_by,added_at_utc)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(section_id,grocery_item_id) DO UPDATE SET checked=0, quantity=MAX(grocery_list_entries.quantity,1)
                """,
                (section_id, item["id"], 1, item["default_unit"], user["id"], ts),
            )
        conn.execute("UPDATE workspace_sections SET updated_at_utc=? WHERE id=?", (ts, section_id))
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}#shopping-list", status_code=303)


@router.post("/{section_id}/groceries/list/add-existing")
def grocery_add_existing(request: Request, section_id: int, grocery_item_id: int = Form(...)):
    user = _user(request)
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        item = conn.execute("SELECT default_unit FROM grocery_items WHERE id=? AND section_id=?", (grocery_item_id, section_id)).fetchone()
        if item:
            conn.execute(
                """
                INSERT INTO grocery_list_entries(section_id,grocery_item_id,quantity,unit,added_by,added_at_utc)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(section_id,grocery_item_id) DO UPDATE SET checked=0
                """,
                (section_id, grocery_item_id, 1, item["default_unit"], user["id"], now_iso()),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}#shopping-list", status_code=303)


@router.post("/{section_id}/groceries/list/{entry_id}/toggle")
def grocery_toggle_entry(request: Request, section_id: int, entry_id: int):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute(
            """
            UPDATE grocery_list_entries
            SET checked=CASE checked WHEN 1 THEN 0 ELSE 1 END,
                checked_at_utc=CASE checked WHEN 0 THEN ? ELSE NULL END
            WHERE id=? AND section_id=?
            """,
            (now_iso(), entry_id, section_id),
        )
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}#shopping-list", status_code=303)


@router.post("/{section_id}/groceries/list/{entry_id}/update")
def grocery_update_entry(request: Request, section_id: int, entry_id: int, quantity: float = Form(1), unit: str = Form(""), note: str = Form("")):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute(
            "UPDATE grocery_list_entries SET quantity=?,unit=?,note=? WHERE id=? AND section_id=?",
            (max(0.01, float(quantity or 1)), (unit or "").strip()[:30], (note or "").strip()[:200], entry_id, section_id),
        )
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}#shopping-list", status_code=303)


@router.post("/{section_id}/groceries/list/clear")
def grocery_clear_checked(request: Request, section_id: int):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute("DELETE FROM grocery_list_entries WHERE section_id=? AND checked=1", (section_id,))
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}#shopping-list", status_code=303)


@router.post("/{section_id}/groceries/recipes/add")
def grocery_add_recipe(request: Request, section_id: int, name: str = Form(...), notes: str = Form("")):
    user = _user(request)
    name = (name or "").strip()
    if name:
        with get_conn() as conn:
            _section_access(conn, request, section_id, require_edit=True)
            ts = now_iso()
            conn.execute(
                "INSERT OR IGNORE INTO grocery_recipes(section_id,name,notes,created_by,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
                (section_id, name[:120], (notes or "").strip()[:1000], user["id"], ts, ts),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}#recipes", status_code=303)


@router.post("/{section_id}/groceries/recipes/{recipe_id}/ingredient")
def grocery_add_ingredient(request: Request, section_id: int, recipe_id: int, grocery_item_id: int = Form(...), quantity: float = Form(1), unit: str = Form("")):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        valid = conn.execute("SELECT 1 FROM grocery_recipes WHERE id=? AND section_id=?", (recipe_id, section_id)).fetchone()
        item = conn.execute("SELECT default_unit FROM grocery_items WHERE id=? AND section_id=?", (grocery_item_id, section_id)).fetchone()
        if valid and item:
            conn.execute(
                "INSERT OR REPLACE INTO grocery_recipe_ingredients(recipe_id,grocery_item_id,quantity,unit) VALUES(?,?,?,?)",
                (recipe_id, grocery_item_id, max(0.01, float(quantity or 1)), (unit or item["default_unit"] or "").strip()[:30]),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}#recipes", status_code=303)


@router.post("/{section_id}/groceries/recipes/{recipe_id}/ingredient/{grocery_item_id}/remove")
def grocery_remove_ingredient(request: Request, section_id: int, recipe_id: int, grocery_item_id: int):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        recipe = conn.execute(
            "SELECT 1 FROM grocery_recipes WHERE id=? AND section_id=?",
            (recipe_id, section_id),
        ).fetchone()
        item = conn.execute(
            "SELECT 1 FROM grocery_items WHERE id=? AND section_id=?",
            (grocery_item_id, section_id),
        ).fetchone()
        if recipe and item:
            conn.execute(
                "DELETE FROM grocery_recipe_ingredients WHERE recipe_id=? AND grocery_item_id=?",
                (recipe_id, grocery_item_id),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}#recipes", status_code=303)


@router.post("/{section_id}/groceries/recipes/{recipe_id}/add-to-list")
def grocery_recipe_to_list(request: Request, section_id: int, recipe_id: int):
    user = _user(request)
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        ingredients = conn.execute(
            """
            SELECT ri.grocery_item_id,ri.quantity,ri.unit
            FROM grocery_recipe_ingredients ri JOIN grocery_recipes r ON r.id=ri.recipe_id
            WHERE ri.recipe_id=? AND r.section_id=?
            """,
            (recipe_id, section_id),
        ).fetchall()
        ts = now_iso()
        for ing in ingredients:
            conn.execute(
                """
                INSERT INTO grocery_list_entries(section_id,grocery_item_id,quantity,unit,added_by,added_at_utc)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(section_id,grocery_item_id) DO UPDATE SET
                    quantity=MAX(grocery_list_entries.quantity,excluded.quantity),
                    unit=CASE WHEN excluded.unit!='' THEN excluded.unit ELSE grocery_list_entries.unit END,
                    checked=0
                """,
                (section_id, ing["grocery_item_id"], ing["quantity"], ing["unit"], user["id"], ts),
            )
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}#shopping-list", status_code=303)


@router.post("/{section_id}/groceries/recipes/{recipe_id}/delete")
def grocery_delete_recipe(request: Request, section_id: int, recipe_id: int):
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        conn.execute("DELETE FROM grocery_recipes WHERE id=? AND section_id=?", (recipe_id, section_id))
        conn.commit()
    return RedirectResponse(f"/sections/{section_id}#recipes", status_code=303)


@router.post("/{section_id}/groceries/prices/add")
def grocery_add_price(
    request: Request,
    section_id: int,
    grocery_item_id: int = Form(...),
    total_cost: float = Form(...),
    quantity: float = Form(1),
    store: str = Form(""),
    purchased_on: str = Form(...),
    note: str = Form(""),
):
    user = _user(request)
    quantity = max(0.01, float(quantity or 1))
    total_cost = max(0.0, float(total_cost or 0))
    with get_conn() as conn:
        _section_access(conn, request, section_id, require_edit=True)
        item = conn.execute("SELECT 1 FROM grocery_items WHERE id=? AND section_id=?", (grocery_item_id, section_id)).fetchone()
        if item:
            conn.execute(
                """
                INSERT INTO grocery_price_history(grocery_item_id,purchased_by,store,purchased_on,quantity,total_cost,unit_cost,note,created_at_utc)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (grocery_item_id, user["id"], (store or "").strip()[:100], purchased_on[:10], quantity, total_cost, total_cost / quantity, (note or "").strip()[:300], now_iso()),
            )
            conn.commit()
    return RedirectResponse(f"/sections/{section_id}#prices", status_code=303)
