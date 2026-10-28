"""Additive metadata for v4. Existing record identities and values are preserved."""
from app.db import get_conn

def init_v4_schema():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS mlo_bill_successors (
            expense_id INTEGER PRIMARY KEY REFERENCES expenses(id) ON DELETE CASCADE,
            successor_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL)''')
        conn.commit()
