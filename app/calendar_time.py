"""Project cached calendar values without shifting floating all-day dates."""
from datetime import date, datetime, time, timezone


def is_all_day(event):
    value=event['starts_at']
    # Pre-v3.7 rows have no all-day flag, but retain their date-only value.
    return bool(event['is_all_day'] or not value or len(str(value))==10)


def cached_start(event,zone):
    try:
        if is_all_day(event):
            return datetime.combine(date.fromisoformat(event['starts_on']),time(),zone)
        value=datetime.fromisoformat(event['starts_at'].replace('Z','+00:00'))
        if value.tzinfo is None:
            value=value.replace(tzinfo=timezone.utc if event['provider']=='microsoft' else zone)
        return value.astimezone(zone)
    except (ValueError,TypeError,AttributeError):
        return None


def reminder_date(event):
    if is_all_day(event):return event['starts_on']
    value=event['starts_at']
    # Historical Graph cache rows can contain UTC without its suffix.
    if event['provider']=='microsoft':
        try:
            if datetime.fromisoformat(value.replace('Z','+00:00')).tzinfo is None:return value+'Z'
        except (ValueError,TypeError,AttributeError):pass
    return value
