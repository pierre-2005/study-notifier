"""Calendar precision, paging, recurring feeds and local-time validation."""
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime,timezone
from unittest.mock import Mock,patch
from zoneinfo import ZoneInfo

_tmp=tempfile.TemporaryDirectory()
os.environ.update(STUDY_NOTIFIER_DB=str(Path(_tmp.name)/'calendar.db'),SESSION_SECRET='calendar-fixture',MLO_SCHEDULER_ENABLED='false')
from app import calendar_links as links
from app.calendar_recurrence import expand_feed
from app.calendar_time import cached_start,reminder_date
from icalendar import Calendar
UTC=timezone.utc

def response(value):return Mock(json=lambda:value)

def feed(events):return Calendar.from_ical('BEGIN:VCALENDAR\nVERSION:2.0\n'+events+'END:VCALENDAR\n')

class CalendarPrecision(unittest.TestCase):
    def test_all_day_dates_keep_their_date_in_both_hemispheres_and_legacy_rows(self):
        for flag in (0,1):
            event={'provider':'google','starts_on':'2031-03-03','starts_at':'2031-03-03','is_all_day':flag}
            for name in ('America/Vancouver','Asia/Tokyo'):
                self.assertEqual(cached_start(event,ZoneInfo(name)).date().isoformat(),'2031-03-03')
            self.assertEqual(reminder_date(event),'2031-03-03')
    def test_floating_ics_and_historical_graph_clocks_have_distinct_semantics(self):
        event={'provider':'ical','starts_on':'2031-03-03','starts_at':'2031-03-03T09:00:00','is_all_day':0}
        zone=ZoneInfo('America/New_York')
        self.assertEqual(cached_start(event,zone).hour,9)
        event['provider']='microsoft'
        self.assertEqual(cached_start(event,zone).hour,4)
        self.assertEqual(reminder_date(event),'2031-03-03T09:00:00Z')
    def test_flagged_all_day_uses_personal_day_time_instead_of_provider_midnight(self):
        event={'provider':'microsoft','starts_on':'2031-03-03','starts_at':'2031-03-03T00:00:00Z','is_all_day':1}
        self.assertEqual(reminder_date(event),'2031-03-03')
        self.assertEqual(cached_start(event,ZoneInfo('America/Vancouver')).day,3)
    def test_google_pagination_and_busy_end_data(self):
        outputs=[{'items':[{'id':'primary','summary':'Primary'}]},
            {'items':[{'id':'one','summary':'Meeting','start':{'dateTime':'2031-03-03T09:00:00Z'},'end':{'dateTime':'2031-03-03T10:00:00Z'}}],'nextPageToken':'page-two'},
            {'items':[{'id':'two','summary':'Holiday','transparency':'transparent','start':{'date':'2031-03-04'},'end':{'date':'2031-03-05'}}]}]
        with patch.object(links,'_token',return_value='fixture'),patch.object(links,'_request',side_effect=[response(v) for v in outputs]) as request:
            result=links._get_events('google',{},1)
        self.assertEqual(len(result),2);self.assertEqual(result[0][6:8],('2031-03-03T10:00:00Z',0));self.assertEqual(result[1][7:],(1,0))
        self.assertEqual(request.call_args_list[2].kwargs['params']['pageToken'],'page-two')
    def test_microsoft_utc_and_next_link(self):
        outputs=[{'value':[{'id':'calendar','name':'Calendar'}]},
            {'value':[{'id':'one','start':{'dateTime':'2031-03-03T09:00:00'},'end':{'dateTime':'2031-03-03T10:00:00'},'subject':'Meeting'}],'@odata.nextLink':'https://graph.microsoft.com/v1.0/next?skip=one'},
            {'value':[{'id':'two','isCancelled':True}]}]
        with patch.object(links,'_token',return_value='fixture'),patch.object(links,'_request',side_effect=[response(v) for v in outputs]) as request:
            result=links._get_events('microsoft',{},1)
        self.assertEqual(len(result),1);self.assertEqual(result[0][3],'2031-03-03T09:00:00Z');self.assertEqual(result[0][6],'2031-03-03T10:00:00Z')
        self.assertIn('Prefer',request.call_args_list[2].kwargs['headers'])
    def test_provider_next_link_cannot_exfiltrate_bearer_token(self):
        outputs=[{'value':[],'@odata.nextLink':'https://evil.example/collect'}]
        with patch.object(links,'_token',return_value='fixture'),patch.object(links,'_request',side_effect=[response(v) for v in outputs]) as request:
            with self.assertRaises(RuntimeError):links._get_events('microsoft',{},1)
        self.assertEqual(request.call_count,1)
    def test_weekly_ics_exceptions_moves_and_cancellations(self):
        calendar=feed('''BEGIN:VEVENT
UID:lecture
DTSTART:20310303T090000Z
DTEND:20310303T100000Z
RRULE:FREQ=WEEKLY;COUNT=5
EXDATE:20310310T090000Z
SUMMARY:Lecture
END:VEVENT
BEGIN:VEVENT
UID:lecture
RECURRENCE-ID:20310317T090000Z
DTSTART:20310317T110000Z
DTEND:20310317T120000Z
SUMMARY:Moved lecture
END:VEVENT
BEGIN:VEVENT
UID:lecture
RECURRENCE-ID:20310324T090000Z
DTSTART:20310324T090000Z
STATUS:CANCELLED
END:VEVENT
''')
        result=expand_feed(calendar,datetime(2031,3,3,tzinfo=UTC))
        self.assertEqual(len(result),3);self.assertEqual(len({r[0] for r in result}),3)
        self.assertEqual({r[2] for r in result},{'2031-03-03','2031-03-17','2031-03-31'})
        self.assertEqual(next(r for r in result if r[1]=='Moved lecture')[3],'2031-03-17T11:00:00+00:00')
    def test_ics_all_day_duration_rdate_and_free(self):
        calendar=feed('''BEGIN:VEVENT
UID:holiday
DTSTART;VALUE=DATE:20310303
DURATION:P2D
RDATE;VALUE=DATE:20310310
TRANSP:TRANSPARENT
SUMMARY:Holiday
END:VEVENT
''')
        result=expand_feed(calendar,datetime(2031,3,3,tzinfo=UTC));self.assertEqual(len(result),2)
        self.assertEqual(result[0][6:],('2031-03-05',1,0));self.assertEqual(result[1][6],'2031-03-12')
    def test_dense_untrusted_recurring_feed_is_refused(self):
        calendar=feed('''BEGIN:VEVENT
UID:dense
DTSTART:20310303T090000Z
RRULE:FREQ=SECONDLY
SUMMARY:Dense
END:VEVENT
''')
        with self.assertRaises(RuntimeError):expand_feed(calendar,datetime(2031,3,3,tzinfo=UTC))
    def test_local_events_reject_ambiguous_or_missing_clocks(self):
        zone=ZoneInfo('America/New_York')
        for start,end in [('2031-03-09T02:30','2031-03-09T03:30'),('2031-11-02T01:30','2031-11-02T02:30')]:
            with self.assertRaises(Exception) as error:links._validate_event('Example',start,end,zone)
            self.assertEqual(error.exception.status_code,422)
        title,start,end=links._validate_event('Example','2031-03-03T10:00','2031-03-03T11:00',zone)
        self.assertEqual(start.astimezone(UTC).isoformat(),'2031-03-03T15:00:00+00:00')

if __name__=='__main__':unittest.main(verbosity=2)
