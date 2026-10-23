"""Bind ownerless historical data to its original installation account.

These records predate member accounts. Never infer that all administrators own
them, and never assign them to a newly created account by counting users.
"""
import os
from app.db import get_conn


def init_legacy_owner():
    with get_conn() as db:
        if db.execute("SELECT 1 FROM app_settings WHERE key='legacy_owner_id'").fetchone():
            return
        user = db.execute('SELECT id FROM users WHERE username=? COLLATE NOCASE AND role=?',
                          (os.getenv('APP_USERNAME', ''), 'admin')).fetchone()
        if user:
            db.execute("INSERT INTO app_settings(key,value) VALUES('legacy_owner_id',?)", (str(user['id']),))
            db.commit()


def owns_legacy_data(db, uid):
    row = db.execute("SELECT value FROM app_settings WHERE key='legacy_owner_id'").fetchone()
    return bool(row and str(uid) == row['value'])
