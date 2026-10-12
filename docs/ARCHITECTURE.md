# Architecture and security overview

## Server and storage

- **FastAPI + Jinja2** server-rendered pages and lightweight JS enhancements; existing `app/main.py` remains the application entrypoint.
- **SQLite** file under `STUDY_NOTIFIER_DB`, WAL activated by legacy `init_db`. Connections are per action; domain schemas are created at startup with `CREATE TABLE IF NOT EXISTS`.
- **Uvicorn 1 worker** runs a background APScheduler for classic reminders and day-of `life_tasks` reminders. Do not scale to multiple workers without a separate leased job process.
- File attachments live in `MLO_ATTACHMENT_DIR` (default: folder beside database). Randomized server filenames, bounded upload size, extension allowlist, download through authorization route and forced `application/octet-stream`.
- No external AI dependencies and no JavaScript framework build pipeline. `theme.css/theme.js` are inherited; `life.css/life.js` layer adds new responsive components.

## New tables

- `life_preferences`: user experience mode, owner-only.
- `life_projects`: owner, area, status, optional career starter category.
- `life_project_members`: project ID + approved user ID and `editor`/`viewer` permission.
- `life_tasks`: optional parent/project, status, priority, date, recurrence, estimated duration, owner.
- `life_task_dependencies`: validated directed prerequisite graph.
- `life_notes`, `life_goals`, `life_habits`, `life_habit_days`, `life_time_entries`.
- `life_project_records`: milestone, issue, risk, decision and deliverable register items.
- `life_files`: attachment metadata; stored bytes separate.
- `life_import_previews`: owner-scoped import preview with SHA checksum and confirmed flag.
- `life_devices` and `life_task_notification_log`: per-user ntfy topics and due-notification deduplication.
- Original `users`, `timers` and legacy tables are preserved. `timers` adds `task_id` and `kind` columns on first v3 startup.

## Authorization model

1. Signed browser session resolved in FastAPI middleware; inactive/unapproved users redirected to login.
2. New life views/handlers call the shared user resolver.
3. A standalone task or note is visible only to its owner.
4. A project item is visible to a project owner or an explicitly added active member; viewer cannot edit.
5. Project membership is checked both on reads and writes, including file downloads, time-session task linking, reminders and search.
6. Legacy courses/jobs/finance/academic and basic to-dos remain restricted to admins because the original schema does not yet isolate their rows by user.
7. `life_devices` and temporary imports are strictly scoped by account.
8. For production expose via HTTPS, set `COOKIE_SECURE=true`, supply long unique session keys and protect public-facing Portainer. Public ntfy topics are not suitable for highly confidential content without authenticated relay setup.

**Known limitations:** Existing code has not had a full third-party security audit, lacks built-in 2FA, CSRF tokens on every legacy form, configurable per-user timezones, row-level database policy independent of application checks, server-side email recovery and advanced enterprise audit logs. It is not certified for regulated datasets.

## UX and speed

- Jinja pages render server-side for reliable baseline use even without JS.
- Common task checkboxes update visually before fetch completion, with rollback and error indication.
- Indexed filters and 150/250-item limits bound expensive page queries. Larger pagination and full-text search indexes remain future work.
- Static assets version-tagged with 7-day cache headers; gzip enabled for large responses; private life pages explicitly `no-store`.
- Installable web app and asset-only service worker. **No offline persistence of private personal tasks**.
- Three experience modes use the **same tables** and default to simple controls, revealing additional options in advanced views.

## Data lifecycle

- On startup `app.backup.pre_v3_backup` makes a consistent SQLite backup if a database file exists and the backup isn't already present. It happens before initialization/migration.
- New v3 schema is additive (timers get two new columns) and original domain tables are retained.
- CSV preview is committed only after user confirms; same file checksum prevents duplicate committed imports for that user.
- Owner-scoped JSON export is not a full re-importable instance backup and does not contain attachment binary data. Use volume backup for complete restoration.

## Next architecture work

Alembic/explicit versioned migrations; unified old/new task ownership and data; robust CSRF defence; durable notification queue; true offline sync with revision IDs and conflicts; and PostgreSQL when measured SQLite write contention requires it.
