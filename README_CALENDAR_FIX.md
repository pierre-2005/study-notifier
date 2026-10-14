# MLO Calendar Event Destination Fix

## Problem
The main MLO Calendar's “New event” button previously opened `/events/new`,
which only inserted a record into MLO's local `events` database table. It
never called Google Calendar or Microsoft Graph.

## Fix
All major “New event” links now open `/life/calendars/new`, where the user
**explicitly chooses the destination**:
- A connected Google account (read/write OAuth required)
- A connected Microsoft/Outlook account (read/write OAuth required)
- MLO-only event (admin accounts; explicitly does *not* sync externally)

External events use the existing provider API creation endpoint and are
cached in MLO's unified calendar after the provider responds successfully.
There is no new background sync, and this patch does not retroactively upload
old local events into Google.

## Install into GitHub → Portainer
1. Back up the running MLO `/data` Docker volume before any deployment.
2. Copy all `app/...` files from this ZIP to those exact locations in your
   repository, replacing the corresponding files, and ADD the new template.
3. Commit to `main`. This patch does **not** replace Docker Compose,
   GitHub Actions, .env, or the public legal page routes.
4. Wait for the existing image publish Action to succeed before clicking
   Pull and redeploy in your existing Portainer Git Stack.
5. Verify the image has updated. The existing tag can be rebuilt in-place
   if your current workflow uses a fixed tag; use Re-pull image in Portainer
   if it does not automatically update the image.
6. Open MLO → Calendar → New event. Choose your Google account, then
   a writable calendar. Create a clearly named test event and verify it
   appears on calendar.google.com for that account.

**Note about base.html**: the included base template retains the public
Privacy/Terms footer supplied in the previous legal-pages patch. If you've
independently customized your `base.html` since then, merge ONLY its link
change (`href="/events/new"` → `href="/life/calendars/new"`) rather than
replacing that entire file.

## Tests
- `python tests_calendar_destination.py`
- `python tests_v343_calendar.py`
- `python tests_smoke.py`

## Troubleshooting
- No Google account shown: authorize in Connected Calendars first.
- “Reconnect to enable editing”: reconnect that Google account with the
  Calendar event write scope, or Microsoft with Calendars.ReadWrite.
- Account shown but provider rejects writes: use the error returned from
  the provider and check the selected calendar's Google access role.
- If an event was created earlier using MLO-only, it will **not** appear in
  Google until manually recreated there; no automatic backfill exists yet.
- Changes made directly in Google Calendar still need manual Sync in
  MLO v3.4.3 to refresh the local event cache.
