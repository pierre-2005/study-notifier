"""Personal reminders from existing owned source records and calendar caches.

One scheduler process. Leases prevent concurrent sends; a provider timeout after
accepting a request can still cause an at-least-once retry, as ntfy has no
transaction shared with SQLite. A failed delivery is never recorded as sent.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import settings
from app.db import get_conn
from app.calendar_time import reminder_date
from app.legacy_access import owns_legacy_data
from app.notifier.ntfy import NtfyNotifier
from app.v37 import read_user_setup, MODULE_KIND

UTC = timezone.utc


def deadline(value, zone, day_time):
    value = str(value)
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), time.fromisoformat(day_time), zone).astimezone(UTC)
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return result.replace(tzinfo=zone).astimezone(UTC) if result.tzinfo is None else result.astimezone(UTC)


def sources(db, uid, modules):
    """Yield source, ID, kind, title, deadline. Never query a remote provider."""
    kinds = {MODULE_KIND[m] for m in modules}
    rows = db.execute('''SELECT t.* FROM life_tasks t LEFT JOIN life_projects p ON p.id=t.project_id
        LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=t.owner_id
        WHERE t.owner_id=? AND t.status!='done' AND t.due_on IS NOT NULL
        AND (t.project_id IS NULL OR p.owner_id=t.owner_id OR m.user_id IS NOT NULL)''', (uid,)).fetchall()
    assessments = {}
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='life_course_assessments'").fetchone():
        assessments = {r['task_id']: dict(r) for r in db.execute(
            'SELECT task_id,kind,due_on,due_at_utc FROM life_course_assessments WHERE user_id=?', (uid,))}
    for row in rows:
        assessment = assessments.get(row['id'],{})
        kind = assessment.get('kind')
        if kind and 'study' not in kinds:
            continue
        kind = kind or ('work' if row['area'] == 'Work' and 'work' in kinds else
                        'study' if row['area'] == 'Study' and 'study' in kinds else 'task')
        if kind in kinds or kind in ('assignment', 'exam', 'lab') and 'study' in kinds:
            yield 'task', str(row['id']), kind, row['title'], (assessment.get('due_at_utc') if assessment.get('due_on')==row['due_on'] else None) or row['due_on']
    if 'project' in kinds:
        for r in db.execute("SELECT id,name,due_on FROM life_projects WHERE owner_id=? AND due_on IS NOT NULL AND status IN ('active','on_hold')", (uid,)):
            yield 'project', str(r['id']), 'project', r['name'], r['due_on']
    if 'event' in kinds:
        for r in db.execute('''SELECT e.id,e.title,e.start_at_utc FROM life_local_events e
                LEFT JOIN life_study_blocks b ON b.event_id=e.id AND b.user_id=e.user_id
                LEFT JOIN life_tasks t ON t.id=b.task_id WHERE e.user_id=? AND (t.status IS NULL OR t.status!='done')''', (uid,)):
            yield 'local_event', str(r['id']), 'event', r['title'], r['start_at_utc']
        for r in db.execute('''SELECT e.*,c.provider FROM life_external_events e
                JOIN life_calendar_connections c ON c.id=e.connection_id WHERE c.user_id=?''', (uid,)):
            yield 'external_event', f"{r['connection_id']}:{r['uid']}", 'event', r['title'], reminder_date(r)
    if 'notes' in kinds:
        for r in db.execute('''SELECT r.note_id,r.remind_at_utc,n.title FROM life_note_reminders r
                JOIN life_notes n ON n.id=r.note_id LEFT JOIN life_projects p ON p.id=n.project_id
                LEFT JOIN life_project_members m ON m.project_id=p.id AND m.user_id=r.user_id
                WHERE r.user_id=? AND (n.owner_id=r.user_id AND n.project_id IS NULL
                OR p.owner_id=r.user_id OR m.user_id IS NOT NULL)''', (uid,)):
            yield 'note', str(r['note_id']), 'notes', r['title'], r['remind_at_utc']
    if 'focus' in kinds:
        for r in db.execute("SELECT * FROM timers WHERE user_id=? AND status='running' AND kind='focus'", (uid,)):
            start = deadline(r['started_at_utc'], UTC, '09:00')
            end = start + timedelta(seconds=r['remaining_seconds'] if r['remaining_seconds'] is not None else r['duration_seconds'])
            yield 'focus', str(r['id']), 'focus', r['label'], end.isoformat()
    # Existing academic, job and expense records have one explicitly bound owner.
    if owns_legacy_data(db, uid):
        if 'study' in kinds:
            for r in db.execute("SELECT id,type,title,due_at_utc FROM items WHERE status!='done'"):
                yield 'item', str(r['id']), r['type'], r['title'], r['due_at_utc']
        if 'bill' in kinds:
            for r in db.execute("SELECT id,title,due_at_utc FROM expenses WHERE status='unpaid'"):
                yield 'bill', str(r['id']), 'bill', r['title'], r['due_at_utc']
        if 'work' in kinds:
            for r in db.execute("SELECT id,company,followup_at_utc FROM jobs WHERE followup_at_utc IS NOT NULL AND status NOT IN ('rejected','offer')"):
                yield 'job', str(r['id']), 'work', 'Follow up: ' + r['company'], r['followup_at_utc']


def process_personal_reminders(at=None, sender=None):
    at = (at or datetime.now(UTC)).astimezone(UTC)
    from app.scheduler import _in_quiet_hours
    with get_conn() as db:
        users = db.execute('''SELECT u.id FROM users u JOIN v37_workspace_preferences p ON p.user_id=u.id
            WHERE u.active=1 AND u.approved=1 AND (u.requires_email_verification=0 OR u.email_verified=1)
            AND p.onboarding_completed=1''').fetchall()
    sent = 0
    for user in users:
        uid = user['id']
        with get_conn() as db:
            prefs = read_user_setup(db, uid)
            zone = ZoneInfo(prefs['timezone'])
            if _in_quiet_hours(at.astimezone(zone), prefs['quiet_start'], prefs['quiet_end']):
                continue
            devices = db.execute('SELECT id,topic FROM life_devices WHERE owner_id=? AND enabled=1', (uid,)).fetchall()
            targets = list(sources(db, uid, prefs['selected_modules'])) if devices else []
        for source, sid, kind, title, raw in targets:
            try:
                due = deadline(raw, zone, prefs['day_time'])
            except (ValueError, TypeError):
                continue
            offsets = prefs['reminders'].get(kind, [])
            if kind in ('assignment', 'exam', 'lab') and not offsets:
                # An explicit empty per-kind override mutes that subtype.
                with get_conn() as db:
                    explicit = db.execute('SELECT 1 FROM v37_reminder_overrides WHERE user_id=? AND kind=?', (uid, kind)).fetchone()
                if not explicit:
                    offsets = prefs['reminders'].get('study', [])
            eligible = [n for n in offsets if due - timedelta(minutes=n) <= at
                        and at <= due + timedelta(minutes=15)
                        and at - (due - timedelta(minutes=n)) <= timedelta(hours=24)]
            if source == 'focus':
                with get_conn() as db:
                    timer=db.execute('SELECT started_at_utc FROM timers WHERE id=? AND user_id=?',(sid,uid)).fetchone()
                if timer:
                    started=deadline(timer['started_at_utc'],UTC,'09:00')
                    eligible=[n for n in eligible if due-timedelta(minutes=n)>=started]
            if not eligible:
                continue
            # Quiet hours/downtime coalesce overdue offsets into the latest one.
            chosen = min(eligible)
            canonical = due.isoformat()
            for device in devices:
                key = (uid, source, sid, device['id'], canonical, chosen)
                with get_conn() as db:
                    db.execute('BEGIN IMMEDIATE')
                    db.execute('''INSERT OR IGNORE INTO v37_notification_deliveries
                        (user_id,source,source_id,device_id,deadline,offset_minutes) VALUES(?,?,?,?,?,?)''', key)
                    # Do not replay earlier offsets when a more recent offset has sent.
                    later = db.execute('''SELECT 1 FROM v37_notification_deliveries WHERE user_id=? AND source=?
                        AND source_id=? AND device_id=? AND deadline=? AND offset_minutes<=? AND state='sent' ''', key).fetchone()
                    claim = None if later else db.execute('''UPDATE v37_notification_deliveries SET state='sending',
                        lease_until=?,attempts=attempts+1 WHERE user_id=? AND source=? AND source_id=? AND device_id=?
                        AND deadline=? AND offset_minutes=? AND state!='sent' AND (lease_until IS NULL OR lease_until<=?)''',
                        ((at + timedelta(minutes=3)).isoformat(), *key, at.isoformat()))
                    db.commit()
                if claim is None or claim.rowcount != 1:
                    continue
                try:
                    ok = bool(sender(device['topic'], kind, title) if sender else
                              NtfyNotifier(settings.ntfy_base_url, device['topic']).send(kind.title() + ' reminder', title))
                except Exception:
                    ok = False
                with get_conn() as db:
                    db.execute('''UPDATE v37_notification_deliveries SET state=?,sent_at=?,lease_until=?
                        WHERE user_id=? AND source=? AND source_id=? AND device_id=? AND deadline=? AND offset_minutes=?''',
                        ('sent' if ok else 'pending', at.isoformat() if ok else None,
                         None if ok else (at + timedelta(minutes=2)).isoformat(), *key))
                    db.commit()
                sent += int(ok)
    return sent
