# MLO Studio v3.4 Enhanced | Release Notes

## Scope

A working upgrade to the consolidated v3.3 codebase. The blue welcome banner, six palettes, appearance mode, card arrangement and editable sidebar are unchanged. No major database table replacement and no existing business records are deliberately deleted.

### New functionality

1. Task finder with filters, sort, total counts and 40-item pagination.
2. Per-account saved task filters, up to 20, with removal.
3. Bulk status and priority editing with dependency and sharing permission checks.
4. Private Insights with 14-day completion/focus charts, overdue and priority counts, upcoming items and project progress.
5. Global quick-add task dialog (desktop `N`, sidebar Quick task, mobile header `+`) and Inbox/Today/Tomorrow choices.
6. Action feedback, keyboard focus management, responsive task and report views.

### Performance, deployment and safety

- Eliminates unnecessary sidebar and timer reads on POST/JSON routes.
- Study/Work hubs query matching tasks directly.
- Adds indexes useful for task/time/area workflows.
- Caches `?v=3.4.0` versioned static files for a year; all private HTML/API responses are `private, no-store`.
- On first upgrade startup with an existing SQLite database, produces `study_notifier.pre-mlo-v3.4.sqlite.backup` beside the database (once).
- Rejects cross-origin form/API writes, subject to properly configured `MLO_PUBLIC_URL` and proxy host forwarding.
- Extends automated tests, including real Chromium UI verification and a 5,000-task local benchmark.
- GitHub Actions runs smoke/privacy/migration suites before publishing the Docker image; browser tests run locally and are not part of this build gate.

### Not delivered

No live bidirectional external calendar sync, full offline editing, full migration of admin-only legacy academic/finance data to private multi-user ownership, native mobile apps, advanced Gantt/resource allocation, rich collaborative docs, native Apple ID sign-in or any regulated professional product certification. See `FEATURE_AUDIT_V34.md` for details.

## Local benchmark

In an in-process test client with 5,000 tasks on this test container, ten-request medians were approximately 13 ms for Today, 10 ms for the first Tasks page, 13 ms for page 90, 7 ms for a filtered search, and 8 ms for Insights. These are local server test times **excluding network and browser-render time** and are not Raspberry Pi performance guarantees.

## Tests

Run from project root with dependencies installed:

```bash
python -m compileall -q app
python tests_smoke.py
python tests_new_features.py
python tests_migration.py
python tests_consolidation.py
python tests_v32.py
python tests_v33_browser.py
python tests_v34.py
python tests_v34_browser.py
python tests_v34_perf.py
```

Browser tests need Playwright and Chromium in a test environment. These scripts use temporary SQLite databases; never point them at production.
