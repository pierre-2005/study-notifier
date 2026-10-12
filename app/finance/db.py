from __future__ import annotations

from datetime import datetime, timezone

from app.db import get_conn
from app.finance.parser import STANDARD_CATEGORIES, DEFAULT_RULES
from app.finance.budget import INCOME_ROWS, SAVINGS_ROWS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_finance_schema() -> None:
    """Create finance tables and seed default categories/rules/budget rows.

    This is safe to call on every startup. Existing user data is not overwritten.
    """
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_categories(
            name TEXT PRIMARY KEY,
            is_custom INTEGER NOT NULL DEFAULT 0,
            created_at_utc TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_merchant_rules(
            category TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            PRIMARY KEY(category, keyword)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_imports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signature TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            bank TEXT NOT NULL,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            imported_at_utc TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            updated_at_utc TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_finance_transactions_unique
        ON finance_transactions(date, description, amount, bank, source_file)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_date
        ON finance_transactions(date)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_category
        ON finance_transactions(category)
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_budget_rows(
            section TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            frequency TEXT NOT NULL DEFAULT 'Monthly',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(section, name)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

        ts = now_iso()
        for category in STANDARD_CATEGORIES:
            conn.execute(
                "INSERT OR IGNORE INTO finance_categories(name, is_custom, created_at_utc) VALUES(?,?,?)",
                (category, 0, ts),
            )

        for category, keywords in DEFAULT_RULES.items():
            for keyword in keywords:
                conn.execute(
                    "INSERT OR IGNORE INTO finance_merchant_rules(category, keyword, created_at_utc) VALUES(?,?,?)",
                    (category, keyword, ts),
                )

        for name in INCOME_ROWS:
            conn.execute(
                """
                INSERT OR IGNORE INTO finance_budget_rows(section, name, amount, frequency, created_at_utc, updated_at_utc)
                VALUES('income', ?, 0, ?, ?, ?)
                """,
                (name, "Annually" if "employment" in name.lower() else "Monthly", ts, ts),
            )
        for category in STANDARD_CATEGORIES:
            conn.execute(
                """
                INSERT OR IGNORE INTO finance_budget_rows(section, name, amount, frequency, created_at_utc, updated_at_utc)
                VALUES('expenses', ?, 0, 'Monthly', ?, ?)
                """,
                (category, ts, ts),
            )
        for name in SAVINGS_ROWS:
            conn.execute(
                """
                INSERT OR IGNORE INTO finance_budget_rows(section, name, amount, frequency, created_at_utc, updated_at_utc)
                VALUES('savings', ?, 0, 'Monthly', ?, ?)
                """,
                (name, ts, ts),
            )

        conn.commit()
