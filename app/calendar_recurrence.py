"""Bounded iCalendar expansion. Unsupported feeds fail without replacing the cache."""
from datetime import date, datetime, time, timedelta, timezone
from itertools import islice

from dateutil.rrule import rruleset, rrulestr


def expand_feed(calendar,at):
    components=list(calendar.walk('VEVENT'))
    if len(components)>3000:raise RuntimeError('Calendar feed has too many components')
    result=[];overrides={};seen=set()
    def as_datetime(value):return value if isinstance(value,datetime) else datetime.combine(value,time())
    def key(value):
        if isinstance(value,datetime) and value.tzinfo:return value.astimezone(timezone.utc).isoformat()
        return value.isoformat()
    for component in components:
        recurrence=component.get('RECURRENCE-ID')
        if recurrence:
            if recurrence.params.get('RANGE'):raise RuntimeError('Calendar recurrence range changes need an expanded calendar feed')
            overrides[(str(component.get('UID','')),key(recurrence.dt))]=component
    def append(component,start,ident):
        if str(component.get('STATUS','')).upper()=='CANCELLED':return
        original=component.decoded('DTSTART',None)
        if original is None:return
        end=component.decoded('DTEND',None);duration=component.decoded('DURATION',None)
        if end is not None:duration=end-original
        if duration is None and not isinstance(start,datetime):duration=timedelta(days=1)
        finish=start+duration if duration is not None else None
        if finish is not None and finish<=start:raise RuntimeError('Calendar event ends before it starts')
        stamp=start.isoformat();signature=(ident,stamp)
        if signature in seen:return
        seen.add(signature)
        result.append((ident,str(component.get('SUMMARY','Untitled event'))[:220],stamp[:10],stamp,'','Subscribed calendar',
            finish.isoformat() if finish is not None else None,int(not isinstance(start,datetime)),int(str(component.get('TRANSP','OPAQUE')).upper()!='TRANSPARENT')))
        if len(result)>3000:raise RuntimeError('Calendar feed has too many expanded events')
    for component in components:
        raw=component.get('DTSTART');ident=str(component.get('UID',''))
        if raw is None:continue
        if not ident:raise RuntimeError('Calendar event is missing its identifier')
        if component.get('RECURRENCE-ID'):continue
        start=raw.dt
        if not isinstance(start,(date,datetime)):raise RuntimeError('Unsupported calendar start time')
        rule=component.get('RRULE');rdates=component.get('RDATE')
        if not rule and not rdates:
            append(component,start,ident);continue
        origin=as_datetime(start);zone=origin.tzinfo
        lower=at.astimezone(zone).replace(tzinfo=zone) if zone else at.replace(tzinfo=None)
        lower-=timedelta(days=35);upper=lower+timedelta(days=221)
        dates=rruleset();dates.rdate(origin)
        if rule:
            if isinstance(rule,list):raise RuntimeError('Multiple recurrence rules are not supported')
            # A personal calendar is bounded to daily or slower recurrence. This
            # also prevents untrusted secondly/minutely rules exhausting a Pi.
            if str(rule.get('FREQ',[''])[0]) not in ('DAILY','WEEKLY','MONTHLY','YEARLY'):
                raise RuntimeError('Calendar recurrence must be daily or less frequent')
            if any(k in rule for k in ('BYSECOND','BYMINUTE','BYHOUR')):
                raise RuntimeError('Subdaily recurrence needs an expanded calendar feed')
            dates.rrule(rrulestr(rule.to_ical().decode(),dtstart=origin))
        for name,operation in (('RDATE',dates.rdate),('EXDATE',dates.exdate)):
            values=component.get(name,[])
            for value in values if isinstance(values,list) else [values]:
                for item in value.dts:
                    if isinstance(item.dt,tuple):raise RuntimeError('Calendar recurrence periods need an expanded calendar feed')
                    operation(as_datetime(item.dt))
        for index,occurrence in enumerate(islice(dates.xafter(lower,inc=True),3001)):
            if occurrence>upper:break
            if index>=3000:raise RuntimeError('Calendar recurrence exceeds the supported size')
            value=occurrence if isinstance(start,datetime) else occurrence.date()
            replacement=overrides.pop((ident,key(value)),None)
            if replacement:
                replacement_start=replacement.decoded('DTSTART',value)
                append(replacement,replacement_start,ident+'@'+key(value))
            else:append(component,value,ident+'@'+key(value))
    # Moved exceptions can enter the window even when their original occurrence
    # lies outside it; retain those as explicit events.
    for (ident,original),component in overrides.items():
        value=component.decoded('DTSTART',None)
        if value is not None:append(component,value,ident+'@'+original)
    return result
