# MLO v3.7 Work Mode continuation and technical handoff
**Prepared:** 2026-10-22  
**Repository:** https://github.com/pierre-2005/study-notifier  
**Feature branch:** `feature/mlo-v37-interactive-workspace`  
**Production branch:** `main` (deliberately unchanged)  
**Working domain:** https://organizer.overvault.ca

## 0.1 Latest CI result (October 22, 2026)
**PASS:** GitHub Actions run [39909456901](https://github.com/pierre-2005/study-notifier/actions/runs/39909456901) on commit `df0353a1b2c7ecc1c9556c406c14b4377c5570e7` completed successfully. It ran Python compileall, four new v3.7 unit tests, and the selected existing smoke, device isolation and appearance tests. A server-rendered fallback was restored after smoke regression exposed asynchronous-board-only HTML. This is not proof of production readiness: remaining full regression suite, real browser/touch, per-category reminder delivery, and staging DB backup/restore tests are still required.

## 1. IMPORTANT: Truthful status and action needed
A first-pass **source integration has been committed to a separate GitHub feature branch**. This is NOT yet a production-ready or deployed v3.7 release. The author of this handoff had authenticated read/write access to GitHub and inspected repository paths, but could not clone the repository into the local execution container because external Git DNS was unavailable. Repository-wide tests and an actual running browser environment were therefore not available locally. A new PR-specific CI workflow was added. Review the PR check results, inspect the code, run a staging migration and verify live behavior before merging into `main`.

**Work Mode's first job:** Open the v3.7 PR, inspect changes and CI failures, fix defects with repository-wide access, then test on a staging copy of the SQLite /data volume. Do not directly modify production database or ship until all gates pass.

## 2. User intent (the original instructions, fully preserved)
The user is transforming MLO from a student organizer into an interactive multi-user workspace. In the immediate v3.7 revision: deeply nested parent/subtask display rather than subtasks appearing as independent Kanban cards; drag-and-drop cards between To do, In progress, Blocked and Done; per-user editable reminder templates for ordinary members, not only administrators; mobile/tablet-responsive cards, columns and typography; animated signup/onboarding with name, username, verified-recovery email, password and selected workspace modules; for EACH module selected in Step 2, Step 3 has independently configurable “Reminder 1” timing dropdown, an “Add reminder” button that makes Reminder 2, Reminder 3, etc., and remove controls. Final step should preview appearance, sidebar modules, board/list/calendar/table view, and compact/comfortable density. User wants a Notion-like interactive feel and to study current concepts from Notion, Coda, Obsidian, Anytype and AFFiNE for extensibility, databases, formulas, backlinks, local-first notes and whiteboard, while avoiding indiscriminate copying.

The **NEXT major revision v4** is a complete UI redesign plus AI-powered importing of PDF/DOCX course outlines, due-date extraction with source-page provenance and user approval, Google/Microsoft/local calendar event creation and conflict-aware study time-block recommendations. v4 importer and actual scheduling are **NOT implemented in this branch**. No fabricated AI extraction or automatic blocking should be implied.

## 3. Existing platform: facts confirmed in GitHub source
- Python FastAPI 0.137, Pydantic 2.13, Starlette, Jinja templates, SQLite.
- Server runs on Raspberry Pi 4 through Docker/Portainer with GitHub Actions multiarch GHCR image on pushes to `main`. Public host uses Cloudflare Tunnel.
- Existing workflow `.github/workflows/publish-image.yml` triggers only on main; it installs dependencies, runs many regression tests, then publishes tagged image `ghcr.io/pierre-2005/study-notifier:v3.6.5-user-themes`. It does not publish from the v3.7 feature branch.
- `app/main.py` has signed cookie authentication and middleware for cross-site write origin/fetch-site checks. Private routes use `request.state.current_user`, with approval, active and auth_version checks.
- `app/auth.py` `create_pending_user(...)` creates unapproved members; administrator approval is required. Email already exists on users; recovery email verification is separately managed by `app/account_security.py`.
- `app/lifeos.py` contains existing access(conn,uid,project_id,edit), task_access(...), Task/project routes. Crucially `life_tasks` ALREADY contains `parent_id`, `position` and status CHECK values `todo`, `doing`, `blocked`, `done`. The earlier prototype expected incompatible names `parent_task_id`, `board_position`, `in_progress`; NEVER run its migration directly.
- `app/personalize.py` stores per-account theme, palette and palette_style in `life_appearance`; supported palettes neutral/ocean/sage/rose/amber/lavender, themes system/light/dark.
- `app/scheduler.py` previously delivered task due-today notifications via per-account `life_devices`; existing legacy administrator-only reminder templates remain in `app/templates/settings.html`. The user demands ordinary users manage personal rules.
- Multi-account Google/Microsoft calendars are supported in `app/calendar_links.py` with automatic syncing configuration; retain current OAuth redirect `https://organizer.overvault.ca/life/calendars/callback`.
- Existing public `/signup` uses pending approval, and `/settings` previously restricted legacy reminder template edit to admins.

## 4. GitHub changes made on branch
1. **`app/v37.py` (new):** authenticated `/api/v37` routes for project Kanban board, status/reordering moves, reparenting/nesting with cycle guard, and per-user setup/reminder persistence. Database `init_v37_schema` creates `v37_workspace_preferences`, `v37_reminder_rules`, `v37_board_moves`, `v37_task_notifications` as additive tables. No migration of original `life_tasks` columns. Board tree nests subtasks and counts total/done descendants. Project ACL applied on every board operation. Move checks task prerequisites on Done and mirrors legacy task state, with recurring-task generation.
2. **`app/main.py` (modified):** registers `init_v37_schema()` after existing life and layout schema startup; registers v37 router; uses new signup wizard template; accepts `v37_setup` form JSON, validates before creating pending user, and saves preferences into new account's rows. Adds authenticated `/life/onboarding` route for existing users. Previous signed-session flow and pending account approval remain intact.
3. **`app/templates/life_project_detail.html` (modified):** replaces only board visualization with authenticated asynchronously loaded board root, leaving project notes, records, sharing, files and project deletion untouched. List and calendar views currently retain existing flat tasks and need follow-up nested rendering.
4. **`app/static/v37-board.js`, `v37-board.css` (new):** live board via fetch, HTML5 drag/drop, status dropdown and move up/down buttons, expandable nested subtasks, search, responsive columns horizontally scrolling on narrow viewports. Native HTML5 drag/drop may need touch-specific fallback or pointer support and keyboard testing.
5. **`app/templates/v37_onboarding.html`, `app/static/v37-onboarding.js`, `v37-onboarding.css` (new):** five-step signup/profile wizard; independent reminder dropdown rows and add/remove per selected module; summary/preview; reduced-motion CSS; form POST for new accounts, authenticated JSON PUT for current users; existing account credentials are not stored in preference tables. Existing users can open it from Settings.
6. **`app/templates/settings.html` (modified):** all users see personal reminders/onboarding entry point, legacy admin settings kept separately.
7. **`app/scheduler.py` (modified):** custom per-account task reminder worker every 10 minutes; date-only task deadlines currently treated as 09:00 in each user's selected time zone, respects quiet hours and tracks user/device/task/day/offset idempotency; legacy due-today behavior bypasses onboarded accounts. Note 24-hour grace-window semantics need review. **Only custom TASK reminders are wired**, not project, study/exam, work, calendar, bill, notes or focus, although their preferences can be stored.
8. **`tests_v37_workspace.py` (new):** initial unittest coverage for nested display, user preference separation, invalid reminder offsets and modules.
9. **`.github/workflows/v37-validation.yml` (new):** compileall and initial/test smoke checks for PRs, isolated from the main publishing workflow.

## 5. Security architecture and key cautions
- Every task move/read must validate project owner/member ACL, not grant admin automatic access to private user projects.
- Avoid duplicating legacy `life_tasks` columns; use original `parent_id`, `position`, `doing` values.
- Session cookies + origin/fetch-site checks protect same-site JSON writes. Examine older clients with absent origin headers and CSRF threat model.
- Tasks in shared projects may have a different `owner_id` from project owner; current scheduler joins device to task owner and verifies membership. Confirm expectations for collaboration and who should be reminded.
- Pending signup currently stores preferences on account creation; approval, email verification, forgot password and recovery still follow existing original app flow. Verify no duplicate usernames, failed preference writes and rollbacks, and accessibility before public rollout.
- `v37_task_notifications` is additive; schema is initialized on FastAPI startup, not during module import. Staging backup mandatory.
- The current `app/v37.py` data layer and templates are first-pass and may have semantic bugs, missing tests, or usability gaps. Running py_compile locally was not possible with the remote-only checkout; CI will be authoritative until Work can check out.
- Current per-user theme persisted through `life_appearance`; wizard colors blue/violet/teal/coral map respectively to ocean/lavender/sage/rose. Preview is an illustration with fake entries, not a live copy of personal information.
- Do not claim PWA becomes a native offline app or bypasses FortiGuard. FortiGuard blocks the domain and changing to Tauri/Electron will not itself bypass network filtering. Separate network categorization/authorized access from a future Tauri + locally bundled frontend/offline cache roadmap.
- Keep production canonical `https://organizer.overvault.ca`; user explicitly declined paid Cloudflare ACM to enable `www.organizer.overvault.ca`.

## 6. Review and verification checklist (must be completed)
A. Fetch exact PR diff, review every changed file and run `python -m compileall -q app`, `python tests_v37_workspace.py`, existing smoke, account, device, calendar, theme and finance tests.
B. Fix any test/CI failures. Verify both signed-in requests and nonmember/malicious moves return 401/403/404 as appropriate, no cross-tenant leakage.
C. Run staging with a COPY of the production DB using SQLite backup API; verify schema initialization is safe, idempotent and does not truncate/corrupt data.
D. Existing users: open `/life/onboarding`, select modules, per-module repeated reminders, change preview, save, refresh and verify persistence. New signup: complete account, await admin approval, sign in and compare saved choices.
E. Kanban board: four columns, drag within/between, dropdown move and keyboard fallback, nested subtasks, progress, blocked dependencies, recurring task generation, collaborative editor vs viewer vs outsider, tiny screen, large project and concurrent changes.
F. Reminders: account isolation, per-user quiet hours/timezone, no duplicate delivery, 0 offsets, negative/invalid offsets rejection, changes to due dates, multiple devices and user-chosen muted templates. Extend scheduling to other categories before representing those notifications as working.
G. Ensure any new .css/.js load under the versioned PWA and cached client, Test Windows installed PWA and Android/iOS responsive interface.
H. MLO's existing `v3.6.5-user-themes` GHCR image reference needs a future planned update only after QA. Preserve Portainer data volume and all secret environment variables; avoid any reinitialization of the production database.
I. Do not merge to main before all checks and a tested rollback plan. Main pushes can trigger publishing and production redeployment.

## 7. Deployment plan, after tests (NOT YET DONE)
1. Keep feature PR as review-only.
2. Back up persistent Docker `/data`, SQLite with WAL consistency, plus uploads. Verify restore on clone.
3. Reconcile Portainer image tag/compose workflow (current GitHub Actions hardcodes `v3.6.5-user-themes`). Do not rely on a v3.7 version label alone to change production.
4. Test on local/staging URL and isolated secrets, then review release note and migrations.
5. Merge PR only after checks, run normal GH Actions image build on main, verify digest and Portainer update.
6. Smoke-test homepage, signup, admin approval, logins, tasks, nesting, board, reminders, calendar OAuth, finance, files and devices.
7. Roll back container image if app fails; restoring database from backup may be needed if data/schema changes are not backward-compatible.
8. Leave Microsoft Store app working as server-backed PWA; PWABuilder/Store certification proceeds separately.

## 8. Further work still requested but not yet implemented
- Complete user-specific reminder delivery across event, assignment, exam, lab, bill, work and project modules; mapping to real source events, time-of-day, calendar APIs and notification permission; add in-app editing controls for reminders outside onboarding.
- Full tree rendering in list and calendar task views; subtask create/reparent controls and accessible touch-friendly drag reorder.
- Design polish, responsive sidebars/resize panes, customizable databases/views, rich block editor, structured field relations and formulas, backlinks, local-first notes and whiteboard, all properly versioned.
- AI course-outline import (PDF/DOCX), OCR where necessary, LLM extraction with source citations, duplicate handling, validation, review/approve, create events/tasks and time-block study intelligently respecting connected calendars and conflicts.
- User privacy, retention/deletion/export, admin/user permission audit, backups, monitoring, PWA install/store lifecycle, Google OAuth production verification, Microsoft Entra, domain security and FortiGuard classification review.
- Public user isolation of older legacy academic and finance tables remains an independent security gate before broad adoption.

## 9. Exact Work-mode continuation prompt
“Open the connected GitHub repository `pierre-2005/study-notifier`. Inspect the draft PR from branch `feature/mlo-v37-interactive-workspace` into `main`. This is a first-pass integration, not deploy-ready. Review CI and every changed file, fix bugs, improve the onboarding and responsive task board, complete all per-user reminder delivery with proper existing permissions and idempotency, and verify against existing and new test suites with a staging database. Do not merge/publish to main or alter live Portainer data until passing tests and I approve deployment. Update this handoff with exact SHA, test evidence, deployment steps, and remaining v4 AI import work.”

## 10. Source and document provenance
Connected repository read using GitHub connector on October 22, 2026. Prior MLO product handoff dated October 17, 2026 and v3.7 prototype ZIP dated October 21, 2026 were used to confirm intended behavior. This document intentionally distinguishes committed code, untested execution and future plans. 
