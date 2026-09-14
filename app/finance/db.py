from __future__ import annotations

from datetime import datetime, timezone

from app.db import get_conn
from app.finance.parser import STANDARD_CATEGORIES, DEFAULT_RULES
from app.finance.budget import INCOME_ROWS, SAVINGS_ROWS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_sql(conn, name: str) -> str:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return (row["sql"] if row and row["sql"] else "")


def _legacy_table_needs_migration(conn, name: str) -> bool:
    sql = _table_sql(conn, name)
    return bool(sql) and "owner_user_id" not in sql


def _migrate_legacy_finance(conn, default_owner_id: int | None) -> None:
    """Migrate the pre-multi-user finance schema without dropping existing data."""
    owner = int(default_owner_id or 0)
    if owner <= 0:
        return

    if _legacy_table_needs_migration(conn, "finance_categories"):
        conn.execute("ALTER TABLE finance_categories RENAME TO finance_categories_legacy")
    if _legacy_table_needs_migration(conn, "finance_merchant_rules"):
        conn.execute("ALTER TABLE finance_merchant_rules RENAME TO finance_merchant_rules_legacy")
    if _legacy_table_needs_migration(conn, "finance_imports"):
        conn.execute("ALTER TABLE finance_imports RENAME TO finance_imports_legacy")
    if _legacy_table_needs_migration(conn, "finance_transactions"):
        conn.execute("DROP INDEX IF EXISTS idx_finance_transactions_unique")
        conn.execute("DROP INDEX IF EXISTS idx_finance_transactions_date")
        conn.execute("DROP INDEX IF EXISTS idx_finance_transactions_category")
        conn.execute("ALTER TABLE finance_transactions RENAME TO finance_transactions_legacy")
    if _legacy_table_needs_migration(conn, "finance_budget_rows"):
        conn.execute("ALTER TABLE finance_budget_rows RENAME TO finance_budget_rows_legacy")
    if _legacy_table_needs_migration(conn, "finance_settings"):
        conn.execute("ALTER TABLE finance_settings RENAME TO finance_settings_legacy")


def _create_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS finance_categories(
            owner_user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            is_custom INTEGER NOT NULL DEFAULT 0,
            created_at_utc TEXT NOT NULL,
            PRIMARY KEY(owner_user_id, name),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS finance_merchant_rules(
            owner_user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            PRIMARY KEY(owner_user_id, category, keyword),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS finance_imports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            signature TEXT NOT NULL,
            filename TEXT NOT NULL,
            bank TEXT NOT NULL,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            imported_at_utc TEXT NOT NULL,
            UNIQUE(owner_user_id, signature),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS finance_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            bank TEXT NOT NULL,
            source_file TEXT NOT NULL,
            transaction_type TEXT NOT NULL DEFAULT 'Purchase',
            included INTEGER NOT NULL DEFAULT 1,
            note TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_transactions_unique
          ON finance_transactions(owner_user_id, date, description, amount, bank, source_file);
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_date
          ON finance_transactions(owner_user_id, date);
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_category
          ON finance_transactions(owner_user_id, category);

        CREATE TABLE IF NOT EXISTS finance_budget_rows(
            owner_user_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            frequency TEXT NOT NULL DEFAULT 'Monthly',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(owner_user_id, section, name),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS finance_settings(
            owner_user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY(owner_user_id, key),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )


def _copy_legacy(conn, default_owner_id: int | None) -> None:
    owner = int(default_owner_id or 0)
    if owner <= 0:
        return

    copies = [
        ("finance_categories_legacy", "INSERT OR IGNORE INTO finance_categories(owner_user_id,name,is_custom,created_at_utc) SELECT ?,name,is_custom,created_at_utc FROM finance_categories_legacy"),
        ("finance_merchant_rules_legacy", "INSERT OR IGNORE INTO finance_merchant_rules(owner_user_id,category,keyword,created_at_utc) SELECT ?,category,keyword,created_at_utc FROM finance_merchant_rules_legacy"),
        ("finance_imports_legacy", "INSERT OR IGNORE INTO finance_imports(id,owner_user_id,signature,filename,bank,transaction_count,imported_at_utc) SELECT id,?,signature,filename,bank,transaction_count,imported_at_utc FROM finance_imports_legacy"),
        ("finance_transactions_legacy", "INSERT OR IGNORE INTO finance_transactions(id,owner_user_id,date,description,amount,category,bank,source_file,transaction_type,included,note,created_at_utc,updated_at_utc) SELECT id,?,date,description,amount,category,bank,source_file,transaction_type,included,note,created_at_utc,updated_at_utc FROM finance_transactions_legacy"),
        ("finance_budget_rows_legacy", "INSERT OR IGNORE INTO finance_budget_rows(owner_user_id,section,name,amount,frequency,created_at_utc,updated_at_utc) SELECT ?,section,name,amount,frequency,created_at_utc,updated_at_utc FROM finance_budget_rows_legacy"),
        ("finance_settings_legacy", "INSERT OR IGNORE INTO finance_settings(owner_user_id,key,value) SELECT ?,key,value FROM finance_settings_legacy"),
    ]
    for table, sql in copies:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if exists:
            conn.execute(sql, (owner,))
            conn.execute(f"DROP TABLE {table}")


def ensure_finance_defaults(conn, user_id: int) -> None:
    ts = now_iso()
    for category in STANDARD_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO finance_categories(owner_user_id,name,is_custom,created_at_utc) VALUES(?,?,?,?)",
            (user_id, category, 0, ts),
        )
    for category, keywords in DEFAULT_RULES.items():
        for keyword in keywords:
            conn.execute(
                "INSERT OR IGNORE INTO finance_merchant_rules(owner_user_id,category,keyword,created_at_utc) VALUES(?,?,?,?)",
                (user_id, category, keyword, ts),
            )
    for name in INCOME_ROWS:
        conn.execute(
            """
            INSERT OR IGNORE INTO finance_budget_rows(owner_user_id,section,name,amount,frequency,created_at_utc,updated_at_utc)
            VALUES(?, 'income', ?, 0, ?, ?, ?)
            """,
            (user_id, name, "Annually" if "employment" in name.lower() else "Monthly", ts, ts),
        )
    for category in STANDARD_CATEGORIES:
        conn.execute(
            """
            INSERT OR IGNORE INTO finance_budget_rows(owner_user_id,section,name,amount,frequency,created_at_utc,updated_at_utc)
            VALUES(?, 'expenses', ?, 0, 'Monthly', ?, ?)
            """,
            (user_id, category, ts, ts),
        )
    for name in SAVINGS_ROWS:
        conn.execute(
            """
            INSERT OR IGNORE INTO finance_budget_rows(owner_user_id,section,name,amount,frequency,created_at_utc,updated_at_utc)
            VALUES(?, 'savings', ?, 0, 'Monthly', ?, ?)
            """,
            (user_id, name, ts, ts),
        )


def init_finance_schema(default_owner_id: int | None = None) -> None:
    """Create the finance schema and migrate existing single-user data."""
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        _migrate_legacy_finance(conn, default_owner_id)
        _create_schema(conn)
        _copy_legacy(conn, default_owner_id)
        conn.execute("PRAGMA foreign_keys=ON")
        if default_owner_id:
            ensure_finance_defaults(conn, int(default_owner_id))
        conn.commit()
