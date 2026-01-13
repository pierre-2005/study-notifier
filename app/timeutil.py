from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def parse_local_datetime_localinput(dt_str: str, tz_name: str) -> datetime:
    """
    Parse HTML <input type="datetime-local"> value: 'YYYY-MM-DDTHH:MM'
    Interpreted as local time in tz_name, returned as aware UTC datetime.
    """
    tz = ZoneInfo(tz_name)
    local_naive = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M")
    local_aware = local_naive.replace(tzinfo=tz)
    return local_aware.astimezone(timezone.utc)

def utc_to_local_str(dt_utc_iso: str | None, tz_name: str) -> str:
    if not dt_utc_iso:
        return ""
    tz = ZoneInfo(tz_name)
    dt_utc = datetime.fromisoformat(dt_utc_iso)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(tz).strftime("%Y-%m-%d %I:%M %p")
