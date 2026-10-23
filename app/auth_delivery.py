"""Durable, encrypted account email and rate-limited one-time reset codes."""
import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from app.db import get_conn


def now():
    return datetime.now(timezone.utc)


def init_delivery_schema():
    with get_conn() as db:
        columns={r[1] for r in db.execute('PRAGMA table_info(users)')}
        if 'requires_email_verification' not in columns:
            db.execute('ALTER TABLE users ADD COLUMN requires_email_verification INTEGER NOT NULL DEFAULT 0')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS auth_reset_codes (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          code_hash TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0, used_at TEXT
        );
        CREATE INDEX IF NOT EXISTS auth_code_user ON auth_reset_codes(user_id,created_at);
        CREATE TABLE IF NOT EXISTS auth_mail_outbox (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          payload TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT, sent_at TEXT
        );
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
          bucket TEXT PRIMARY KEY, window_at TEXT NOT NULL, attempts INTEGER NOT NULL
        );
        ''')
        db.commit()


def _cipher():
    # Separate derivation from, and no changes to, the existing OAuth key.
    key=hashlib.sha256(('mlo-account-mail-v1:' + os.environ['SESSION_SECRET']).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def digest(value):
    return hmac.new(os.environ['SESSION_SECRET'].encode(), value.encode(), hashlib.sha256).hexdigest()


def allow(bucket, limit=5, minutes=15):
    at=now()
    key=digest(bucket)
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM auth_rate_limits WHERE window_at<?', ((at-timedelta(days=1)).isoformat(),))
        row=db.execute('SELECT * FROM auth_rate_limits WHERE bucket=?',(key,)).fetchone()
        if row and row['window_at'] > (at-timedelta(minutes=minutes)).isoformat():
            if row['attempts'] >= limit:
                return False
            db.execute('UPDATE auth_rate_limits SET attempts=attempts+1 WHERE bucket=?',(key,))
        else:
            db.execute('''INSERT INTO auth_rate_limits(bucket,window_at,attempts) VALUES(?,?,1)
                ON CONFLICT(bucket) DO UPDATE SET window_at=excluded.window_at,attempts=1''',(key,at.isoformat()))
        db.commit()
    return True


def queue_email(uid, to, subject, body, minutes=60, db=None):
    import json
    payload=_cipher().encrypt(json.dumps({'to':to,'subject':subject,'body':body}).encode()).decode()
    def insert(conn):
        conn.execute('''INSERT INTO auth_mail_outbox(user_id,payload,created_at,expires_at)
            VALUES(?,?,?,?)''',(uid,payload,now().isoformat(),(now()+timedelta(minutes=minutes)).isoformat()))
    if db is not None:
        insert(db)
    else:
        with get_conn() as conn:
            insert(conn)
            conn.commit()


def deliver_mail():
    import json
    from app.account_security import _email_configured, _send_email
    at=now()
    sent=0
    with get_conn() as db:
        # Remove token-bearing payloads after delivery or expiry.
        db.execute('DELETE FROM auth_mail_outbox WHERE expires_at<=? OR sent_at IS NOT NULL',(at.isoformat(),))
        rows=db.execute('''SELECT * FROM auth_mail_outbox WHERE EXISTS(SELECT 1 FROM users u WHERE u.id=auth_mail_outbox.user_id AND u.active=1) AND sent_at IS NULL AND expires_at>?
            AND attempts<10 AND (next_attempt IS NULL OR next_attempt<=?) ORDER BY id LIMIT 10''',
            (at.isoformat(),at.isoformat())).fetchall()
        db.commit()
    if not _email_configured():
        return 0
    for row in rows:
        with get_conn() as db:
            claim=db.execute('''UPDATE auth_mail_outbox SET next_attempt=?,attempts=attempts+1
                WHERE id=? AND sent_at IS NULL AND (next_attempt IS NULL OR next_attempt<=?)''',
                ((at+timedelta(minutes=2)).isoformat(),row['id'],at.isoformat()))
            db.commit()
        if claim.rowcount!=1:
            continue
        try:
            mail=json.loads(_cipher().decrypt(row['payload'].encode()))
            ok=_send_email(mail['to'],mail['subject'],mail['body'])
        except Exception:
            # Never log recipients, reset codes, SMTP responses or credentials.
            ok=False
        if ok:
            with get_conn() as db:
                db.execute('DELETE FROM auth_mail_outbox WHERE id=?',(row['id'],))
                db.commit()
            sent+=1
    return sent


def issue_reset_code(uid, email):
    at=now()
    with get_conn() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM auth_reset_codes WHERE user_id=? AND created_at>?',
                      (uid,(at-timedelta(minutes=5)).isoformat())).fetchone():
            return False
        code=f'{secrets.randbelow(1000000):06d}'
        db.execute('UPDATE auth_reset_codes SET used_at=? WHERE user_id=? AND used_at IS NULL',(at.isoformat(),uid))
        # A previous queued code is now invalid; do not deliver it after recovery.
        db.execute('DELETE FROM auth_mail_outbox WHERE user_id=?',(uid,))
        db.execute('''INSERT INTO auth_reset_codes(user_id,code_hash,created_at,expires_at)
            VALUES(?,?,?,?)''',(uid,digest(f'{uid}:{code}'),at.isoformat(),(at+timedelta(minutes=10)).isoformat()))
        queue_email(uid,email,'Your MLO password reset code',
                    f'Your code is {code}.\n\nIt expires in 10 minutes and can be used once. '
                    'If you did not request a reset, ignore this email.',minutes=10,db=db)
        db.commit()
    return True


def consume_reset_code(db, identity, code, password):
    """The caller holds BEGIN IMMEDIATE; password update and consumption are atomic."""
    from app.auth import hash_password
    at=now().isoformat()
    user=db.execute('''SELECT id FROM users WHERE lower(email)=? AND email_verified=1
        AND active=1 AND approved=1''',(identity.strip().lower(),)).fetchone()
    if not user:
        return False
    entry=db.execute('''SELECT * FROM auth_reset_codes WHERE user_id=? AND used_at IS NULL
        AND expires_at>? ORDER BY id DESC LIMIT 1''',(user['id'],at)).fetchone()
    if not entry or entry['attempts']>=5:
        return False
    db.execute('UPDATE auth_reset_codes SET attempts=attempts+1 WHERE id=?',(entry['id'],))
    if not hmac.compare_digest(entry['code_hash'],digest(f"{user['id']}:{code.strip()}")):
        return False
    db.execute('UPDATE auth_reset_codes SET used_at=? WHERE id=?',(at,entry['id']))
    db.execute('''UPDATE users SET password_hash=?,auth_version=auth_version+1,must_change_password=0
        WHERE id=?''',(hash_password(password),user['id']))
    db.execute('UPDATE auth_email_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL',(at,user['id']))
    db.execute('DELETE FROM auth_mail_outbox WHERE user_id=?',(user['id'],))
    db.execute('INSERT INTO auth_audit_log(target_id,action,created_at) VALUES(?,?,?)',(user['id'],'password_reset_code',at))
    return True
