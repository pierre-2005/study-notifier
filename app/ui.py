"""Shared template environment and safe presentation helpers."""
from pathlib import Path
from datetime import date, datetime, timezone
from urllib.parse import urlsplit
from fastapi.templating import Jinja2Templates
from app.meta import APP_VERSION
from app.config import settings

def safe_href(value):
    value = str(value or '').strip()
    if not value or any(ord(c) < 32 for c in value) or '\\' in value: return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() in ('https', 'http') and parsed.hostname and not parsed.username:
            parsed.port
            return value
        if value.startswith('/') and not value.startswith('//'): return value
    except ValueError: pass
    return ''

def status_label(value):
    return {'todo':'To do','doing':'In progress','done':'Done','interested':'Interested','applied':'Applied',
            'interview':'Interview','offer':'Offer','rejected':'Rejected','unpaid':'Unpaid','paid':'Paid',
            'blocked':'Blocked','none':'Does not repeat'}.get(str(value),str(value).replace('_',' ').capitalize())

def local_input(value, zone):
    if not value: return ''
    from zoneinfo import ZoneInfo
    try:
        instant=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if instant.tzinfo is None: instant=instant.replace(tzinfo=timezone.utc)
        return instant.astimezone(ZoneInfo(zone)).strftime('%Y-%m-%dT%H:%M')
    except (ValueError,TypeError): return ''

templates=Jinja2Templates(directory=str(Path(__file__).parent/'templates'))
templates.env.globals.update(APP_VERSION=APP_VERSION,record_timezone=settings.timezone,current_day=lambda:date.today().isoformat(),safe_href=safe_href,status_label=status_label,local_input=local_input)
templates.env.filters.update(status_label=status_label,safe_href=safe_href)
