from __future__ import annotations

from datetime import datetime, timezone

from app.db import get_conn

CORE_OWNER_TABLES = (
    "courses",
    "items",
    "reminders",
    "jobs",
    "todos",
    "expenses",
    "class_meetings",
    "events",
)

FINANCE_OWNER_TABLES = (
    "finance_categories",
    "finance_merchant_rules",
    "finance_imports",
    "finance_transactions",
    "finance_budget_rows",
    "finance_settings",
)


def _rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def build_user_export(user_id: int) -> dict:
    """Build a portable JSON snapshot of data owned by one account.

    Password hashes, session data, and notification topic secrets are deliberately
    excluded. Shared sections owned by somebody else are also excluded: they are
    part of the owner's backup, not the collaborator's.
    """
    with get_conn() as conn:
        user = conn.execute(
            "SELECT id,username,display_name,role,created_at_utc FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if not user:
            raise ValueError("User not found")

        data: dict[str, object] = {
            "format": "mlo-user-export-v1",
            "exported_at_utc": datetime.now(timezone.utc).isoformat(),
            "account": dict(user),
            "personal": {},
            "finance": {},
            "projects": {},
            "workspace": {},
            "timers": [],
            "settings": [],
            "notification_devices": [],
        }

        personal = data["personal"]
        assert isinstance(personal, dict)
        for table in CORE_OWNER_TABLES:
            personal[table] = _rows(conn, f"SELECT * FROM {table} WHERE owner_user_id=? ORDER BY id", (user_id,))

        finance = data["finance"]
        assert isinstance(finance, dict)
        for table in FINANCE_OWNER_TABLES:
            order = "id" if table in {"finance_imports", "finance_transactions"} else "rowid"
            finance[table] = _rows(conn, f"SELECT * FROM {table} WHERE owner_user_id=? ORDER BY {order}", (user_id,))

        projects = _rows(conn, "SELECT * FROM projects WHERE owner_user_id=? ORDER BY id", (user_id,))
        project_ids = [int(row["id"]) for row in projects]
        project_tasks: list[dict] = []
        project_links: list[dict] = []
        if project_ids:
            placeholders = ",".join("?" for _ in project_ids)
            project_tasks = _rows(conn, f"SELECT * FROM project_tasks WHERE project_id IN ({placeholders}) ORDER BY project_id,position,id", tuple(project_ids))
            project_links = _rows(conn, f"SELECT * FROM project_links WHERE project_id IN ({placeholders}) ORDER BY project_id,id", tuple(project_ids))
        data["projects"] = {"projects": projects, "tasks": project_tasks, "links": project_links}

        sections = _rows(conn, "SELECT * FROM workspace_sections WHERE owner_user_id=? ORDER BY id", (user_id,))
        section_ids = [int(row["id"]) for row in sections]
        workspace: dict[str, object] = {
            "sections": sections,
            "members": [],
            "checklist_items": [],
            "grocery_items": [],
            "grocery_list_entries": [],
            "grocery_recipes": [],
            "grocery_recipe_ingredients": [],
            "grocery_price_history": [],
        }
        if section_ids:
            placeholders = ",".join("?" for _ in section_ids)
            section_params = tuple(section_ids)
            workspace["members"] = _rows(conn, f"SELECT * FROM workspace_section_members WHERE section_id IN ({placeholders}) ORDER BY section_id,user_id", section_params)
            workspace["checklist_items"] = _rows(conn, f"SELECT * FROM workspace_checklist_items WHERE section_id IN ({placeholders}) ORDER BY section_id,position,id", section_params)
            grocery_items = _rows(conn, f"SELECT * FROM grocery_items WHERE section_id IN ({placeholders}) ORDER BY section_id,id", section_params)
            workspace["grocery_items"] = grocery_items
            workspace["grocery_list_entries"] = _rows(conn, f"SELECT * FROM grocery_list_entries WHERE section_id IN ({placeholders}) ORDER BY section_id,id", section_params)
            recipes = _rows(conn, f"SELECT * FROM grocery_recipes WHERE section_id IN ({placeholders}) ORDER BY section_id,id", section_params)
            workspace["grocery_recipes"] = recipes
            recipe_ids = [int(row["id"]) for row in recipes]
            item_ids = [int(row["id"]) for row in grocery_items]
            if recipe_ids:
                rp = ",".join("?" for _ in recipe_ids)
                workspace["grocery_recipe_ingredients"] = _rows(conn, f"SELECT * FROM grocery_recipe_ingredients WHERE recipe_id IN ({rp}) ORDER BY recipe_id,grocery_item_id", tuple(recipe_ids))
            if item_ids:
                ip = ",".join("?" for _ in item_ids)
                workspace["grocery_price_history"] = _rows(conn, f"SELECT * FROM grocery_price_history WHERE grocery_item_id IN ({ip}) ORDER BY grocery_item_id,purchased_on,id", tuple(item_ids))
        data["workspace"] = workspace

        data["timers"] = _rows(conn, "SELECT * FROM timers WHERE user_id=? ORDER BY id", (user_id,))
        data["settings"] = _rows(conn, "SELECT * FROM user_settings WHERE user_id=? ORDER BY key", (user_id,))
        # Keep labels/status for inventory, but never export the ntfy topic itself.
        data["notification_devices"] = _rows(
            conn,
            "SELECT id,label,provider,enabled,created_at_utc,updated_at_utc FROM user_notification_devices WHERE user_id=? ORDER BY id",
            (user_id,),
        )
        return data
