"""Pinned timezone data supports current Alberta rules and historical DST correctly."""
import os
# Match the Docker environment before zoneinfo is imported.
os.environ['PYTHONTZPATH']=''
from datetime import datetime,timezone
from zoneinfo import ZoneInfo,TZPATH
import unittest
import tzdata
from app.reminders import deadline


class TimezoneTests(unittest.TestCase):
    def test_packaged_database_selected(self):
        self.assertEqual(TZPATH,())
        self.assertEqual(tzdata.IANA_VERSION,'2026e')
    def test_current_edmonton_rule(self):
        self.assertEqual(deadline('2026-12-10',ZoneInfo('America/Edmonton'),'09:00'),datetime(2026,12,10,15,tzinfo=timezone.utc))
    def test_historical_fall_transition(self):
        zone=ZoneInfo('America/Edmonton')
        self.assertEqual(deadline('2025-11-01',zone,'09:00').hour,15)
        self.assertEqual(deadline('2025-11-02',zone,'09:00').hour,16)
    def test_explicit_utc_deadlines_unchanged(self):
        self.assertEqual(deadline('2026-12-10T16:00:00+00:00',ZoneInfo('America/Edmonton'),'09:00'),datetime(2026,12,10,16,tzinfo=timezone.utc))


if __name__=='__main__':unittest.main(verbosity=2)
