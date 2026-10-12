# MLO Studio v3.2.0 | Release notes

Built directly from **MLO v3.1 Consolidated**, not from the earlier pre-consolidation source.

## Finished changes

- Refreshed desktop/tablet/mobile dashboard inspired by the supplied Timeyfi visual reference, with original vector landscape art, a date mini-calendar, focused task capture, in-dashboard focus timer, task/project areas and personal stats.
- More consistent white surfaces, sage/mint accents, restrained animation, light/dark styles and simplified sidebar typography across the existing app.
- Dashboard cards are reorderable with desktop drag-and-drop or keyboard/touch up/down controls; widgets can be hidden and restored. Layout is stored in SQLite **per user**, not shared browser storage.
- Sidebar navigation entries and pinned space shortcuts can be individually renamed (personal display alias), reordered and hidden. Actual shared-space names are unchanged for other collaborators; space owners can still rename them through Space settings.
- Project owners can **permanently delete a project with all project tasks, subtasks, notes, files, members and project records**. The deletion requires typing the exact project name. Logged minutes remain but lose the project reference.
- Added `/life/calendars` calendar account management supporting several separately linked Google accounts and Microsoft accounts, plus HTTPS iCalendar subscriptions including iCloud shared-calendar links.
- Google/Microsoft OAuth2 tokens and calendar feed URLs are encrypted at rest with `MLO_CREDENTIAL_KEY`. Account details, event caches and sync actions are isolated per MLO user.
- Synced external events appear on the existing consolidated Calendar, alongside tasks and original school/work events. Normal page views make no external API requests. Sync is manually triggered on the connection screen.
- Removed redundant instructional/marketing microcopy from the Today and Project pages, while retaining practical instructions and error states.
- Retained Simple, Guided and Professional display settings under Today → Customize; all three use the same underlying project/task data.
- Updated the service worker assets and fixed malformed Compose health-check quoting present in the v3.1 package.

## Calendar integration status and limitations

**Google**: Real OAuth2 authorization, permits connecting multiple Google accounts. The manual sync reads the Google Calendar API for accessible calendars, and caches events locally in read-only mode.

**Outlook / Microsoft 365**: Real OAuth2 authorization, permits multiple Microsoft personal and work/school accounts. Manual sync uses Microsoft Graph's calendar view APIs, read-only.

**Apple / iCloud**: Accepts a provider-issued HTTPS published iCalendar subscription URL. This is **not Apple ID sign-in or authenticated CalDAV**. Shared calendars may be accessible to anyone with the link; do not publish sensitive calendars. Apple CalDAV sign-in is future work.

Event synchronization is one-way and manual, not live push notifications or two-way editing. Repeating iCalendar events are not expanded into future occurrences, while Google/Microsoft requests use the providers' expanded event endpoints. Provider responses are capped for performance. Calendar credentials/consents have not been tested with live personal Google, Microsoft or Apple accounts in this offline build environment.

## Out of scope for this release

- Genuine Apple sign-in/CalDAV sync, two-way edits, background sync and provider webhooks
- Real-time cross-user live collaborative editing
- Full offline editing and conflict reconciliation
- Full replacement of all historic finance/grocery/academic detail forms
- Live Portainer and third-party OAuth deployment verification

## Data safety

No legacy task, finance or course table is deleted. New tables are additive. The upgraded deployment must use the existing `/data` volume. **Backup the whole volume** (including file attachments), not just the SQLite database, before upgrading. In particular, v2 databases must be tested in a separate copy before any production upgrade.
