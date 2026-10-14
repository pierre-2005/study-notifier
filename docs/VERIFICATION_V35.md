# MLO v3.5 verification

## Passed in this execution environment
- Python source compilation (`python -m compileall -q app`).
- `tests_smoke.py`: authenticated app routes, accounts, private projects/tasks, notes and timers.
- `tests_new_features.py`: import workflow, file access, devices, backups.
- `tests_migration.py`: representative legacy schema/data migration.
- `tests_consolidation.py`: older to-do conversion and legacy Study/Work/Money views.
- `tests_v32.py`: account-specific layout/settings, connection security and project deletion.
- `tests_v34.py`: task search, pagination, bulk updates, insights and privacy.
- `tests_v343_calendar.py`: mocked Google/Microsoft API create/update/delete and permission checks.
- `tests_v35_calendar.py`: unified creation, private MLO records, edits/deletion, blocked cross-user access, correct remote target, rate-limited background sync and preservation of cached events after provider error.
- `tests_calendar_destination.py`: previous links now use the unified form and connected accounts remain private.
- `tests_public_legal.py`: public homepage, privacy/terms pages and authenticated routing.
- `tests_v341_contrast.py`: tested six palettes in light/dark mode.
- `tests_v342_layout.py`: collapsed sidebar, layout overflow and eight major pages across four viewport widths.

## Tests not completed
- An older optional `tests_v33_browser.py` test hung in the current browser-runner environment. It was not counted as a pass; GitHub workflow does not currently run that suite.
- Live OAuth authorization, provider API communication, Windows Store certification and actual Raspberry Pi/Portainer deployment were not performed here. Provider-write tests use mocked Google/Microsoft responses.
- No live Google/Microsoft webhook delivery, all-day event editing, full offline editing or conflict-merge testing. Background refresh is periodic polling only.

## Deployment prerequisites
- Make a restorable backup of the complete existing Docker `/data` volume and original Compose settings.
- Confirm your public HTTPS domain, stable encryption key, active Google/Microsoft client credentials and legal contact email are configured.
- Deploy on an existing single-process FastAPI container, or separate the APScheduler worker before scaling to multiple processes.
- Test on disposable Google/Outlook calendars before relying on real production schedules.
