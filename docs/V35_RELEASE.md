# MLO Studio v3.5 – Unified Calendar & Server-Backed Windows App Preparation

## Implemented in source
- One Calendar → New event form, with explicit destination per account and calendar.
- MLO-only events saved in a new **per-user private table**, with edit/delete and calendar rendering. Existing legacy shared admin events are preserved and remain admin-visible.
- Google and Microsoft event creation uses their remote APIs; MLO cache reflects successful provider writes.
- Automatic calendar refresh via existing application scheduler, configurable cadence (default 10 minutes), bounded batch size, per-connection error state and last-attempt throttling; failed refreshes preserve previously cached data.
- First sync picked up by the background scheduler shortly after successful connection or feed addition (typically within one minute). No HTTP requests to providers are made in the connection-page request.
- Calendar account screen no longer presents routine Sync controls while automatic refresh is enabled.
- Provider account selection uses a lazily fetched list of writable calendars, keeping the initial New event page fast.
- Service worker still caches static assets only; manifest now includes 192/512 icons and shortcuts for Windows PWA packaging.
- Full test suite and GitHub Actions updated for release tag `v3.5-unified-calendars`.

## Not included / limitations
- Google's and Microsoft's push notification webhooks, delta sync and real-time updates are **not yet implemented**. An edit made externally appears after the next scheduled refresh (usually within ~10 minutes, longer if throttled, offline or the API fails).
- All-day/recurring series editing and attendee invitations remain outside the unified event form.
- App does **not** have full offline editing. Windows/Store packaging has not yet been produced or submitted. The Windows PWA remains server-backed.
- Google/Microsoft write and token refresh paths are covered by mocked API tests; no real OAuth connection or external writes were performed from this environment.
- The original admin-only legacy Events module remains for compatibility with historical records; the new MLO-only event table is private and does not erase or import those legacy events.
- For reliable production deployment with multiple web worker processes or replicas, move the scheduler into a **dedicated single-worker service** or use a shared distributed lock. The default provided deployment uses one app process.

## Files to update in GitHub
- `app/calendar_links.py`, `app/lifeos.py`, `app/main.py`, `app/meta.py`
- `app/templates/life_event_destination.html`, `app/templates/life_local_event_form.html`, `app/templates/life_calendar_connections.html`, `app/templates/base.html`
- `app/static/polish343.css`, `app/static/manifest.webmanifest`, `app/static/sw.js`, icon PNGs
- `.github/workflows/publish-image.yml`, `docker-compose.yml`, `.env.example`
- `tests_v35_calendar.py`, updated compatibility test and docs.

## Release verification
See `docs/VERIFICATION_V35.md`. Always back up your Docker data volume before deployment.
