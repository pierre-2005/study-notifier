# File placement guide

Extract the entire ZIP into one folder. All paths below are relative to that folder. **Do not copy files one by one into a running container.**

**38 new files, 6 updated files, 64 original files preserved.**

## Added files and exact locations

- `.env.production.example`
- `README.md`
- `app/backup.py`
- `app/life_files.py`
- `app/life_import.py`
- `app/lifeos.py`
- `app/phones.py`
- `app/static/life.css`
- `app/static/life.js`
- `app/static/manifest.webmanifest`
- `app/static/sw.js`
- `app/templates/life_calendar.html`
- `app/templates/life_components.html`
- `app/templates/life_devices.html`
- `app/templates/life_focus.html`
- `app/templates/life_goals.html`
- `app/templates/life_home.html`
- `app/templates/life_import.html`
- `app/templates/life_note_detail.html`
- `app/templates/life_notes.html`
- `app/templates/life_project_detail.html`
- `app/templates/life_projects.html`
- `app/templates/life_search.html`
- `app/templates/life_task_detail.html`
- `app/templates/life_tasks.html`
- `docker-compose.portainer.yml`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOY_PORTAINER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/VERIFICATION.md`
- `docs/preview/desktop-home.png`
- `docs/preview/desktop-projects.png`
- `docs/preview/mobile-home.png`
- `docs/strategy/MLO_Product_Strategy_2026_Expanded.md`
- `tests_migration.py`
- `tests_new_features.py`
- `tests_smoke.py`
- `visual_check.py`

## Existing files changed

- `app/main.py`
- `app/meta.py`
- `app/scheduler.py`
- `app/templates/base.html`
- `app/timers.py`
- `docker-compose.yml`

## Original files included unchanged

- `.env.example`
- `.gitignore`
- `Dockerfile`
- `app/__init__.py`
- `app/auth.py`
- `app/config.py`
- `app/db.py`
- `app/finance/__init__.py`
- `app/finance/budget.py`
- `app/finance/db.py`
- `app/finance/monthly.py`
- `app/finance/parser.py`
- `app/finance/routes.py`
- `app/finance/service.py`
- `app/notifier/__init__.py`
- `app/notifier/base.py`
- `app/notifier/ntfy.py`
- `app/static/apple-touch-icon.png`
- `app/static/favicon.ico`
- `app/static/theme.css`
- `app/static/theme.js`
- `app/templates/admin_users.html`
- `app/templates/classes.html`
- `app/templates/course_detail.html`
- `app/templates/courses.html`
- `app/templates/dashboard.html`
- `app/templates/edit_class.html`
- `app/templates/event_detail.html`
- `app/templates/events.html`
- `app/templates/expense_detail.html`
- `app/templates/expenses.html`
- `app/templates/finance_budget.html`
- `app/templates/finance_dashboard.html`
- `app/templates/finance_import.html`
- `app/templates/finance_monthly.html`
- `app/templates/finance_rules.html`
- `app/templates/finance_transaction_detail.html`
- `app/templates/finance_transactions.html`
- `app/templates/item_detail.html`
- `app/templates/items.html`
- `app/templates/job_detail.html`
- `app/templates/jobs.html`
- `app/templates/login.html`
- `app/templates/new_class.html`
- `app/templates/new_course.html`
- `app/templates/new_event.html`
- `app/templates/new_expense.html`
- `app/templates/new_item.html`
- `app/templates/new_job.html`
- `app/templates/new_todo.html`
- `app/templates/schedule.html`
- `app/templates/section_blank.html`
- `app/templates/section_grocery.html`
- `app/templates/section_new.html`
- `app/templates/sections.html`
- `app/templates/settings.html`
- `app/templates/signup.html`
- `app/templates/timers.html`
- `app/templates/todo_detail.html`
- `app/templates/todos.html`
- `app/timeutil.py`
- `app/workspace.py`
- `requirements.txt`
- `run_app.py`

## Do not overwrite these runtime locations

- `/data/study_notifier.db` or the custom path specified by `STUDY_NOTIFIER_DB`
- `/data/mlo_uploads/` or your custom `MLO_ATTACHMENT_DIR`
- Docker named volume holding the database
- Real `.env` with credentials/secrets

## Main implementation entry points

- `app/main.py`: FastAPI app, authentication, classic routes, new router registration.
- `app/lifeos.py`: connected life projects, tasks, notes, goals, habits, search, exports.
- `app/life_files.py`: document attachment authorization, uploads and downloads.
- `app/life_import.py`: CSV preview and deduplicated import.
- `app/phones.py`: per-user phone topics and management.
- `app/timers.py`: server-persistent countdowns plus task-linked focus time.
- `app/scheduler.py`: legacy notification jobs and new per-device reminders.
- `app/static/life.css`, `app/static/life.js`: modern responsive interface and incremental actions.
- `app/templates/life_*.html`: module pages.
- `docker-compose.portainer.yml`: Portainer stack with explicit existing-volume mapping.

Read `README.md` and `docs/DEPLOY_PORTAINER.md` before deploying.
