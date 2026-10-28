# MLO 4.0 screen and workflow review

Reviewed October 27, 2026 against the populated disposable fixture, with fresh
screenshots from the current application. The v4 suite rendered 59 routes at
375, 768, 1280 and 1440 pixels: 236 route/width states. Every expected page
returned 200; the deliberate missing-page route returned the styled 404. No
document-level horizontal overflow or JavaScript errors occurred. Intentional
horizontal navigation/board scrolling remains available within its container.

Desktop and phone captures cover every route below. Contact sheets were
visually inspected for shared spacing, readable hierarchy, field/action placement,
mobile stacking and shell consistency. Budget and notes were also inspected as
full-size images. Automated layout checks cover the intermediate widths. This
is a bounded fixture review, not every possible real user's content or device.

## Module inventory

| Module | Reviewed screens and workflows |
| --- | --- |
| Shared shell / Today | Blue greeting, populated widgets, capture, private appearance/sidebar and movable layout; inherited customization and keyboard/browser checks retained |
| Tasks / Projects | Task list, project list, board and task detail; inherited drag/touch, keyboard status, nested children, inspector, sharing and deletion flows |
| Notes | List/detail, Write/Preview/Split, formatting, safe links/raw HTML, save, unsaved later typing, stale-tab conflict, viewer reader and attachments/review controls |
| Calendar / Focus | Month, phone agenda, explicit agenda, destinations/connections, new event, focus timer; inherited planner/calendar/provider/date tests |
| Goals / Insights | Populated goals/habits, editable/completion/history controls and insights; owner/local-day service checks |
| Study | Hub, planner, outline import, courses, assessment and class lists/new/detail/edit; inherited review/apply/undo/OCR flows |
| Work | Hub, applications list/new/detail and follow-up reminders |
| Finance | Overview, filtered and paged transactions, transaction edit, staged/quick Budget, monthly view, rules/import and Bills navigation |
| Bills / Saved events | New/detail/edit, timezone hints, pending reminder shifts, sent history, recurrence successor and tombstone protection |
| Spaces | List/new, blank content/checklist, separate owner settings/sharing, editor/viewer ACL and version protection |
| Groceries | Shopping, recipes, price history and settings; finite quantities/prices, date checks and existing links/history |
| Settings / Security | Personal settings, calendars, devices/iPhone owner-only pairing, security/password, administrator users, import/search |
| Public / Auth / Errors | Home, privacy, terms, sign in, signup, forgot-password, reset-code, resend verification and styled missing page; API denials keep JSON |
| PWA | Actual v4 desktop/phone install screenshots; manifest/icon/pairing checks; real localhost service-worker upgrade, static-only cache and unrelated-cache retention |

## Interaction and adverse-state review

Budget tests move backward/forward without losing draft amounts, create a category
inside the picker, move it between expense stages, preserve Weekly frequency,
remove/restore it, use quick edit, save/reload, and compare visible monthly totals.
A deliberate 503, stale 409 and expired-session 401 each retain entered values.
With JavaScript disabled, all stages and saved calculations render and invalid
submitted money remains visible. Phone picker Escape restores trigger focus.
No budget amounts are written to localStorage.

Note tests render only the supported Markdown DOM, reject dangerous links/raw
HTML, retain text typed during an in-flight save, report another-tab conflicts,
and deny viewer mutation controls. Both Budget and Notes receive 12 light/dark
palette audits. Read-only project and note screens receive separate phone audits.

Finance paging checks exactly 50 then 22 rows from 72 transactions, and 18 matching
filtered grocery rows. Service checks separately exercise atomic money validation,
rule deletion persistence, parser bounds/timeouts, partial-space settings,
unchecked sharing roles, goal/habit permissions, invalid local dates, CSV formula
protection and sanitized document-worker environments.

The first expanded run exposed two sharing-select labels and a pairing-topic
contrast failure only after more fixture users/devices were added. Both labels
and the contrast were corrected; the final 97 v4 axe scans and 47 inherited
scans have zero violations. This does not establish WCAG certification.

## Rendered route ledger

Each entry below passed at all four widths. Screenshot filenames in the CI
`v4-verification` artifact use the listed index and either `375` or `1440`, for
example `test-results/v4/screen-19-375.png` for the initial phone Budget.

| Index | Route | HTTP |
| --- | --- | --- |
| 00 | `/life` | 200 |
| 01 | `/life/tasks` | 200 |
| 02 | `/life/projects` | 200 |
| 03 | `/life/projects/1?view=board` | 200 |
| 04 | `/life/tasks/1` | 200 |
| 05 | `/life/notes` | 200 |
| 06 | `/life/notes/1` | 200 |
| 07 | `/life/calendar` | 200 |
| 08 | `/life/calendar?month=2026-11&view=agenda` | 200 |
| 09 | `/life/focus` | 200 |
| 10 | `/life/goals` | 200 |
| 11 | `/life/insights` | 200 |
| 12 | `/life/study` | 200 |
| 13 | `/life/study/planner` | 200 |
| 14 | `/life/study/import` | 200 |
| 15 | `/life/work` | 200 |
| 16 | `/finance` | 200 |
| 17 | `/finance/transactions` | 200 |
| 18 | `/finance/transactions/1` | 200 |
| 19 | `/finance/budget` | 200 |
| 20 | `/finance/monthly` | 200 |
| 21 | `/finance/rules` | 200 |
| 22 | `/finance/import` | 200 |
| 23 | `/expenses` | 200 |
| 24 | `/expenses/new` | 200 |
| 25 | `/expenses/1` | 200 |
| 26 | `/courses` | 200 |
| 27 | `/courses/new` | 200 |
| 28 | `/courses/1` | 200 |
| 29 | `/items` | 200 |
| 30 | `/items/new` | 200 |
| 31 | `/items/1` | 200 |
| 32 | `/classes` | 200 |
| 33 | `/classes/new` | 200 |
| 34 | `/classes/1/edit` | 200 |
| 35 | `/jobs` | 200 |
| 36 | `/jobs/new` | 200 |
| 37 | `/jobs/1` | 200 |
| 38 | `/events` | 200 |
| 39 | `/events/1` | 200 |
| 40 | `/life/spaces` | 200 |
| 41 | `/sections/new` | 200 |
| 42 | `/sections/1` | 200 |
| 43 | `/sections/1?view=settings` | 200 |
| 44 | `/sections/2?view=list` | 200 |
| 45 | `/sections/2?view=recipes` | 200 |
| 46 | `/sections/2?view=prices` | 200 |
| 47 | `/sections/2?view=settings` | 200 |
| 48 | `/life/calendars` | 200 |
| 49 | `/life/calendars/new` | 200 |
| 50 | `/life/devices` | 200 |
| 51 | `/life/devices/1/pair-iphone` | 200 |
| 52 | `/settings` | 200 |
| 53 | `/account/security` | 200 |
| 54 | `/account/password` | 200 |
| 55 | `/admin/users` | 200 |
| 56 | `/life/import` | 200 |
| 57 | `/life/search` | 200 |
| 58 | `/missing-page` | 404 |

Additional evidence includes `budget-mobile.png`, `budget-save-failure.png`,
`budget-dark.png`, route JSON, accessibility JSON and JavaScript-error JSON in
the same artifact. The current PWA install previews are source assets named
`dashboard-v4-desktop.png` and `dashboard-v4-mobile.png`; older asset URLs remain.
Historical screenshot files in `docs/preview` are not labeled as new v4 evidence.

Live SMTP/OAuth/phone delivery, installed PWA/Store behavior, actual production
backup rehearsal and physical Pi performance require the owner steps in
[V4_SETUP_REPORT.md](V4_SETUP_REPORT.md) and
[V4_DEPLOYMENT.md](V4_DEPLOYMENT.md).
