# MLO 4.0 setup report

Prepared October 27, 2026. Source work is in
[PR #3](https://github.com/pierre-2005/study-notifier/pull/3). Consult its exact
revision/checks and the verification report before releasing. No production
server, database, Portainer, DNS, mailbox, phone or live OAuth account was
accessed during this work. The owner handles the Portainer redeploy after the
verified image is published.

## What changes

Budget now has Income, Essentials, Flexible spending, Savings and Review stages,
plus quick edit over the same saved rows. Back/Continue preserve the draft.
Funded/common rows appear first; the picker restores additional categories and
creates custom ones without leaving the draft. Expense groups can be moved.
Removing a row sets its planned amount to zero and retains the category/history.
Existing payment frequencies are preserved. Monthly equivalents use 12 months,
52 weekly or 26 biweekly payments; entered money is rounded to cents before the
save transaction. Save failures and stale revisions keep the entered values.
Draft amounts are not stored in localStorage. JavaScript-disabled forms show
server-calculated saved totals, all stages and a normal submit path.

Finance has one persistent navigation bar including Bills, SQL transaction
pagination/search, validated transaction/date/month edits, and merchant rule
deletions that remain deleted after restart. Statement uploads accept at most
10 PDFs, 10 MB each and 60 pages per statement. Parsing runs in a process with a
45-second timeout, bounded output/text and, on Linux, CPU/address-space limits.
At most two document workers run concurrently per application process. Parser
environments exclude session, SMTP, OAuth and AI credentials. BMO/Scotiabank
formats remain the supported scope. Existing source formats and transaction
identities are not silently converted into a new bank ledger.

Record screens share field, heading, action and reminder components. School,
career, bills and stored-event routes are separated from application composition.
Bills can be fully edited; moving a due date shifts pending reminders and leaves
sent history intact. A durable successor relation prevents a paid recurring bill
from generating another successor after reopening/renaming, including a deleted
successor. Existing recurring-bill matches are reused at the first v4 transition.
Courses, assessments and saved events have consistent edit/detail controls.
Dates reject malformed, nonexistent and ambiguous local clocks. Record forms
show their installation timezone; personal calendars/reminders retain account
zone preferences.

Notes add Write, Preview and Split views, a small formatting toolbar, explicit
Save/Ctrl-S, unsaved feedback and version conflicts. Preview builds DOM nodes
with text content; raw note HTML is not trusted. Later typing during an in-flight
save remains an unsaved draft. Project viewers stay read-only. Existing note
files and private review reminders remain available.

Goals/habits can be edited and removed. Completion and history use the account's
local day and bounded seven-day window. Task prerequisites can be removed with
the task's edit permission. Board, full edit and compatibility mutations retain
the shared dependency/recurrence service.

Spaces separate Content from Settings & sharing. Grocery spaces have Shopping
list, Recipes, Price history and owner settings views. Content-only saves do not
overwrite settings from stale hidden fields. Versions detect concurrent edits;
only owners can change settings/sharing, and an unchecked Can edit control
creates a viewer. Quantities/prices must be finite and real purchase dates are
validated. Existing grocery items, recipe links, prices and sharing survive.

Calendar adds a readable agenda, with an automatic phone view and explicit
Month/Agenda selection. Existing connected-account destinations, provider
writes, background refresh, all-day dates and planning remain integrated.
The shared shell uses one canonical stylesheet and current script names. The
blue greeting, account palettes, sidebar customization and movable cards remain.
Old asset paths and `/api/v37` stay available for installed clients; current
scripts use `/api/v4`. Old internal database names are not renamed for branding.
Unused classic dashboard/to-do/schedule/section/signup templates are removed;
old bookmarks and to-do mutations adapt to actual current tasks.

## Preserve these installation values

| Item | Keep |
| --- | --- |
| Host | `https://organizer.overvault.ca` |
| Deferred host | Do not activate `www.organizer.overvault.ca` |
| Git stack | Existing stack, `refs/heads/main`, root Compose |
| Port | `127.0.0.1:8001:8000` |
| Database | `/data/study_notifier.db` in the existing volume |
| Uploads | `/data/mlo_uploads`, including original file identities/content |
| Session key | Existing `SESSION_SECRET` |
| Calendar encryption | Existing `MLO_CREDENTIAL_KEY` |
| Bootstrap credentials | Preserve `APP_USERNAME` / `APP_PASSWORD`; no routine reset |
| OAuth callback | `https://organizer.overvault.ca/life/calendars/callback` |
| Calendar clients | Existing Google/Microsoft IDs, secrets, registrations and tokens |

The only new persistent table is `mlo_bill_successors`, with original expense IDs
and nullable successor IDs. Budget revision/group metadata uses
`finance_settings`. Existing note/space update timestamps provide conflict
versions. No destructive Finance/account/content migration is performed.
Startup creates and checks a one-time online `.pre-mlo-v4.sqlite.backup` before
initialization. Backups close SQLite connections before rename on Windows and
Linux. See the separate deployment/rollback guide for an independent backup and
actual-installation rehearsal.

## Account email

Use the installation's SMTP provider. Enter credentials privately in the
existing Portainer environment, never in Git or a public report.

| Variable | Setting |
| --- | --- |
| `MLO_PUBLIC_URL` | `https://organizer.overvault.ca` |
| `MLO_SMTP_HOST` | Provider's submission host |
| `MLO_SMTP_PORT` | Provider's port, commonly 587 or 465 |
| `MLO_SMTP_STARTTLS` | `true` for STARTTLS submission on 587; 465 uses implicit TLS |
| `MLO_SMTP_USER` | SMTP username |
| `MLO_SMTP_PASSWORD` | Private SMTP credential |
| `MLO_SMTP_FROM` | Authorized, verified sender |
| `MLO_LEGAL_CONTACT_EMAIL` | Monitored support/privacy address |
| `COOKIE_SECURE` | `true` on production HTTPS |

Follow the provider's current exact SPF/DKIM/domain-verification records and
review DMARC alignment. Preserve unrelated DNS/mail records. Disable account
mail link/open tracking where offered. No particular paid provider is required
by this code. The earlier [email walkthrough](V37_EMAIL_SETUP.md) explains the
existing contract; verify provider-specific examples before using them.

New accounts require email verification and administrator approval. Existing
eligible accounts retain their earlier eligibility rules. Recovery uses a
six-digit, one-use code sent to the verified address, with ten-minute expiry,
five attempts and session revocation on success. New codes supersede old queued
codes. Administrators request user-delivered recovery; they cannot choose a
member password or redirect it to an administrator mailbox. Encrypted queued
mail is retried by the scheduler until its expiry/attempt limit.

Before inviting people, use controlled mailboxes for signup, inbox/spam receipt,
verification, approval, login, resend, reset, expiry/replay rejection and old
session invalidation. A mocked mail test or SMTP acceptance does not prove inbox
delivery. Missing SMTP configuration cannot deliver a verification message.

## Calendars and planning

Preserve `MLO_GOOGLE_CLIENT_ID`, `MLO_GOOGLE_CLIENT_SECRET`, `MLO_MS_CLIENT_ID`,
`MLO_MS_CLIENT_SECRET`, `MLO_CREDENTIAL_KEY` and the registered callback above.
Retain `MLO_CALENDAR_AUTO_SYNC=true`, the existing refresh interval (normally 10
minutes), and modest batch size (normally 3). Do not reconnect working accounts
or change provider registrations simply for this update.

Use a controlled Google and Outlook account to verify connect/refresh,
create/edit/delete, background refresh, disconnect and study conflict avoidance.
Manual refresh remains a recovery action. Plain Apple/iCalendar feeds remain
read-only. Provider verification/testing/tenant status was not inspected here.

Study planning uses private availability, estimates minus logged focus, due
dates and cached commitments. Preview before Apply. Pin/manual edits protect
sessions; Clear and guarded Undo retain their existing rules. Automatic planning
remains opt-in. A stale/failed/incomplete calendar connection blocks an unsafe
new plan. Generated study events remain private MLO events; the planner does
not silently write a set of bookings to external accounts.

## Optional AI extraction

Local extraction/OCR work without an AI key. Only if desired, set
`MLO_OUTLINE_AI_ENABLED=true`, a private `OPENAI_API_KEY`, and
`MLO_OUTLINE_AI_MODEL` to a model supported by the installation's API project.
Choose AI per upload. Only extracted outline text/year context is sent with the
existing constrained response contract; no tools or calendar credentials are
supplied. AI suggestions start unselected and require source review. Live paid
model quality/billing was not tested. Keep local extraction available as fallback.

## Reminders, phones and installed apps

Keep `MLO_SCHEDULER_ENABLED=true` for normal operation and one application worker
per database. Keep the current ntfy base URL and account-owned device topics.
`MLO_ENABLE_LEGACY_GLOBAL_NTFY` remains false by default. A public ntfy topic is a
secret subscription destination; stronger private-server authentication is a
separate operator choice.

Android pairing retains its ntfy deep link. iPhone pairing retains its
owner-authenticated page and copy/subscription flow. Test a real phone's
permissions/background delivery and one personal due reminder; emulator/mocked
results do not establish actual delivery. Check an installed Windows/iPhone PWA
after rollout. Web/PWA data continue to live on the same server. Static caches
update to `mlo-static-v4.0.0`; activation removes only old MLO static caches and
keeps unrelated origin caches. Private responses are never cached. The Microsoft
Store package identity/version is not changed by the backend version string.

## Installation acceptance still requiring the owner

1. Rehearse a real private backup and matched attachments/configuration.
2. Confirm actual Docker architecture. CI covers AMD64/ARM64; it does not prove a
   32-bit Pi OS can run an ARM64 image or measure physical Pi/OCR performance.
3. Verify live SMTP, Google/Microsoft, actual phone delivery and installed PWAs.
4. Check health, administrator/member login, an original Finance record, original
   attachment, shared viewer/editor behavior and calendar data after rollout.
5. Follow the existing-stack rollout and rollback guide. No production volume,
   secret, DNS or Portainer change is implied by the source PR.

Remaining product boundaries are explicit in the README: historical owner-only
Finance, supported statement formats, reviewed assessment extraction, a compact
Markdown subset, no true offline editing or live collaborative block editor,
and no claim of competitor feature parity or universal accessibility/device
certification.
