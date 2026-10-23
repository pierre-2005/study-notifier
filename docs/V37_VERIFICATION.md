# MLO v3.7 verification and continuation

**Release status: draft candidate, not approved for production.** PR #1 remains on `feature/mlo-v37-interactive-workspace` against main. Nothing was merged, deployed to Portainer, published to GHCR or run against the production database. The candidate version is `3.7.0-rc1`.

The original 13 changed files and the complete attached/repository handoffs were read. The implementation and findings are in [V37_REVIEW_AND_FIXES.md](V37_REVIEW_AND_FIXES.md). The research and UI decisions are in [V37_PRODUCT_RESEARCH.md](V37_PRODUCT_RESEARCH.md).

## Verification evidence

The local regression runner executes each existing `tests*.py` script in a separate process. It preserves historical suites and adds current real-HTTP browser acceptance; older screenshot suites alone do not verify the new stylesheet. Python 3.12 and Chrome Headless Shell 156.0.8078.47 were used. No real user credentials or external notifications were used. Automated provider tests use mocks or controlled fixtures.

| Area | Evidence and practical limit |
| --- | --- |
| Core regression | All 27 available standalone scripts passed, with zero failures, in the final local run. Every script is run by `scripts/run_regression.py`; exact results/timings are in [V37_TEST_RESULTS.json](V37_TEST_RESULTS.json). |
| v3.7 API integration | Sixteen acceptance tests cover member API access, owner/editor/viewer/admin isolation, dependencies across edit paths, recurring successors, cycle/depth checks, stale edits, preferences/mutes, signup/verification/approval, reset limits/expiry/replay/encryption and personal note reminders. |
| Reminder delivery | Tests exercise tasks, project dates, local/external events, assignments/exams/labs, work tasks/follow-ups, bills, notes and focus, including private-device routing, failures/retry, disabled users, quiet hours and DST-aware date-only deadlines. Network delivery is mocked. |
| Course outlines | PDF text, DOCX, PNG, JPG, scanned PDF/OCR and text; invalid file/XML handling, ambiguous dates, editable commit, ownership, duplicate/repeated imports, source evidence and optional AI schema/error handling. AI API calls are mocked, not live-model quality tests. |
| Browser flows | Real server and real JS/CSS against a disposable database. Mouse drag, touch drag with edge scrolling, child edits/creation, parent movement, task inspector save/focus, profile preview, signup and course review/commit. Sixteen main routes at 375/768/1280/1440 pixels; no document horizontal overflow or JS errors in those checks. |
| Accessibility | Axe-core 4.14.0 ran 33 WCAG 2.0/2.1 A/AA scans, including board in all six palettes/light-dark modes, task inspector, core routes, import review and mobile signup/board. Zero reported violations in these tested states. [Machine-readable scan results](preview/v37/accessibility.json). Keyboard navigation, modal focus and reduced-motion behavior are also exercised. This is not a full accessibility certification or real screen-reader/device study. |
| Migration rehearsal | Read-only source online backup with outstanding WAL data, migration twice, original-column/row preservation across ten source tables, 64 staging tables, integrity and foreign-key checks, and restoration identical to baseline. A nonempty staging directory is rejected. This was a representative synthetic legacy database, not the user's actual staging data. |
| Existing integrations | Regression coverage retains Google/Microsoft/ICS/local calendar routes, OAuth state, credential encryption, refresh/sync errors, destinations, create/edit/delete, disconnect, Finance, imports/exports, device ownership, public legal routes, PWA manifest/service worker and account themes. Live providers and actual installed OAuth credentials remain unverified. |
| Build checks | Python compilation, ten JavaScript syntax checks, patch formatting and installed Python dependency consistency. Docker daemon/ARM64 hardware are unavailable here; the Docker image and Raspberry Pi runtime have not been built/tested locally. |

The initial baseline passed 17 of 18 service scripts; the missing signup legal links failed the public legal test. That regression is fixed. Two historical assertions were updated for deliberate behavior changes: Add task wording and owner-delivered recovery instead of administrator-known passwords. A previously blocked member API, recurrence/dependency bypasses and unsafe legacy administrator access were fixed rather than waived.

## Reviewable screens

- [Today](preview/v37/today-desktop.png)
- [Project board](preview/v37/board-desktop.png) and [dark board](preview/v37/board-dark.png)
- [Mobile board](preview/v37/board-mobile.png)
- [Course outline review](preview/v37/outline-review-desktop.png)
- [Appearance preview](preview/v37/appearance-preview.png)

These screenshots contain disposable demonstration data only. Local Chrome Headless Shell was used because the normal Chromium installer/browser executable could not run reliably in this environment.

## Remaining release gates

1. Run the documented migration/restoration rehearsal against an actual backed-up staging copy, including its existing foreign keys, historical accounts, encrypted calendar credentials, finance records and attachments. Retain the report privately. Representative tests cannot prove that an unseen production database is clean.
2. Configure/verify the real sender domain and SMTP credentials, then test inbox delivery, verification/resend and recovery with controlled real mailboxes. [Step-by-step setup](V37_EMAIL_SETUP.md).
3. Exercise real Google/Microsoft OAuth connections, refresh and calendar writes with controlled test calendars, plus ntfy pairing/delivery on actual phones. Existing provider secrets and callbacks were preserved, not exercised against live accounts here.
4. Build and inspect the approved multi-architecture image, confirm ARM64/Pi OCR memory and startup behavior, and perform installed PWA checks on iPhone/Windows and actual assistive technology. Browser emulation is partial evidence only.
5. Review the new UI and course-import behavior with the owner. Complete the latest branch's GitHub Actions run and resolve any failures before approval. Only then obtain explicit approval of the tested commit and deployment window.

Follow [V37_DEPLOYMENT.md](V37_DEPLOYMENT.md) for the staging and rollback procedure. Do not deploy merely because unit tests or a previous commit's CI is green.

## Product work still to do

The requested course-outline assessment importer and substantial shared UI improvements have been brought forward. A complete v4 UI/editor architecture rewrite, generalized cross-content linking, lecture/office-hour extraction and automatic study-block scheduling remain separate major work. No autonomous scheduler has been added. Exact assessment times imported during review are retained for reminders; date edits use the task's current date and do not invent a replacement clock time. Imported tasks appear in MLO Calendar and are not automatically bulk-written to external providers.

Finance remains the installation's historical owner-only module; this release does not silently convert its global records into multi-user finances. Other users' capabilities, approvals, private tasks/projects, device topics and existing OAuth credentials remain isolated. Further per-user Finance support requires a separately reviewed data migration.
