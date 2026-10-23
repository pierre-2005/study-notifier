"""Today's agenda from existing owned records, without network calls or copies."""
from datetime import datetime, time, timedelta, timezone
from urllib.parse import quote

from app.legacy_access import owns_legacy_data


def agenda_for(db,uid,day,zone):
    first=datetime.combine(day,time(),zone).astimezone(timezone.utc)
    last=datetime.combine(day+timedelta(days=1),time(),zone).astimezone(timezone.utc)
    rows=[]
    def add(value,title,href,label,all_day=False):
        try:
            stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
            if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=zone if all_day else timezone.utc)
            local=stamp.astimezone(zone)
            if local.date()==day:rows.append({'sort':local.isoformat(),'title':title,'href':href,'label':label,'clock':'All day' if all_day else local.strftime('%H:%M')})
        except (TypeError,ValueError):pass
    for row in db.execute('SELECT * FROM life_local_events WHERE user_id=? AND start_at_utc>=? AND start_at_utc<? ORDER BY start_at_utc LIMIT 50',
                          (uid,(first-timedelta(days=1)).isoformat(),(last+timedelta(days=1)).isoformat())):
        add(row['start_at_utc'],row['title'],f"/life/calendars/local/{row['id']}/edit",'Study session' if row['kind']=='study' else 'My calendar')
    for row in db.execute('''SELECT e.*,c.provider,c.label FROM life_external_events e JOIN life_calendar_connections c ON c.id=e.connection_id
            WHERE c.user_id=? AND e.starts_on>=? AND e.starts_on<=? ORDER BY e.starts_on LIMIT 100''',
            (uid,(day-timedelta(days=1)).isoformat(),(day+timedelta(days=1)).isoformat())):
        href=(f"/life/calendars/{row['connection_id']}/events/{quote(row['uid'],safe='')}/edit" if row['provider'] in ('google','microsoft') else '/life/calendars')
        add(row['starts_on'] if row['is_all_day'] else row['starts_at'] or row['starts_on'],row['title'],href,row['label'],bool(row['is_all_day'] or not row['starts_at']))
    if owns_legacy_data(db,uid):
        for row in db.execute('SELECT * FROM events WHERE start_at_utc>=? AND start_at_utc<?',(first.isoformat(),last.isoformat())):
            add(row['start_at_utc'],row['title'],f"/events/{row['id']}",'Event')
        for row in db.execute('SELECT * FROM class_meetings WHERE active=1 AND weekday=?',(day.weekday(),)):
            add(datetime.combine(day,time.fromisoformat(row['start_time_local']),zone).isoformat(),row['title'],f"/classes/{row['id']}/edit",row['location'] or 'Class')
    return sorted(rows,key=lambda r:r['sort'])[:12]
