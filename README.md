# My Life Organized | MLO Next v3.0.0-preview.1

A **working, installable preview** of the next MLO application, built on the uploaded Study Notifier **v1.4.1** codebase. It includes a redesigned, mobile-responsive Life OS alongside the preserved classic course, expense, finance, jobs, events, sections and timer screens.

> **Important:** This is **not** the full several-hundred-feature product described in `docs/PRODUCT_SCOPE.md`. The connected core is implemented and tested, while enterprise collaboration, deep professional integrations, full offline synchronization, AI, rich live document editing and regulated-industry functionality remain future work. It has **not** been validated as a drop-in migration from the separately discussed v2 package, which was unavailable in this session. Test on a copy of your live database before replacing a deployed v2 system.

## What works now

- **Instant-on Home/Today:** no onboarding questionnaire; type one task and press Enter; active priorities and project cards.
- **Unified new task engine:** personal Inbox, open/done/upcoming/today/overdue filters, details, subtasks, priorities, dates, recurrence, estimates, dependencies, completing tasks without a full page refresh.
- **Projects:** name-only creation, optional starter templates across 35+ career/household categories, status, notes, shared members with viewer/editor permissions, board/list/due-date views, milestones, risk/issue/decision/deliverable registers, task counts and time summaries.
- **Notes:** personal and project-linked notes with an accessible plain-text editor, attachments and private-by-default account ownership.
- **Calendar:** monthly visual representation of linked **task deadlines** (not yet a Google/Outlook two-way calendar).
- **Focus:** link timers to tasks, Pomodoro-duration presets, session history, automatically logged completed focus time, manual time entries, weekly totals. Break timers don't count as work.
- **Goals & habits:** account-private goals, check-ins, seven-day counts.
- **Search:** tasks, notes and projects with permission-aware search.
- **Phones:** each user can generate one or more hard-to-guess ntfy topics, pause/remove/test devices, and receive account-owned task due-day notifications.
- **Import/Export:** preview and commit a CSV task import; CSV export and owner-scoped JSON export. No hidden pricing restrictions or forced third-party accounts.
- **Responsive UI:** desktop/sidebar, tablet and mobile dock, appearance themes inherited from classic MLO, reduced motion, accessibility focus outlines, installable PWA shell (assets-only offline cache).
- **Compatibility:** original academic, jobs, expenses, finance, timers and shared sections are retained under Classic tools. Legacy data is **not** yet automatically synchronized into the new task engine. Legacy personal tools remain administrator-only for privacy until migration/ownership is complete.
- **Safety:** pre-v3 SQLite database snapshot, signed login sessions, private new records, permission checks, bounded uploads, security headers, gzip and versioned static assets.

## Run locally on Windows / Linux / macOS

Use Python 3.12 (matching the Dockerfile).

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.production.example .env  # Windows: copy .env.production.example .env
```

Set `SESSION_SECRET`, `APP_USERNAME`, `APP_PASSWORD` and `COOKIE_SECURE=false` **only if testing over local HTTP**. Generate a secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Start:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/login`, sign in, and open **Today** (`/life`). Other users create accounts under `/signup`; admin approves under `/admin/users`.

## Docker / Portainer

**Read [`docs/DEPLOY_PORTAINER.md`](docs/DEPLOY_PORTAINER.md) before touching an existing installation.** Its steps explicitly preserve your current Docker volume and work around Portainer's opaque `Failure [object Object]` failures when build contexts are absent.

- Fresh local compose: `docker compose --env-file .env up -d --build` after setting a real `.env` file.
- Existing Portainer setup: build `mlo-next:v3-preview` **on the Pi** from the extracted package, then deploy `docker-compose.portainer.yml` pointing at the *existing exact volume*.
- Do **not** delete or recreate the old volume just to fix a deployment error.
- For Cloudflare Tunnel / HTTPS leave `COOKIE_SECURE=true`; HTTP on a LAN may fail to log in with a Secure cookie.

## Tests

With dependencies installed, run:

```bash
python tests_smoke.py
python tests_new_features.py
python -m compileall -q app
```

The test suites substitute a no-op reminder scheduler, so they cover HTTP, schemas and account isolation but do not simulate real scheduled jobs or message delivery over ntfy. See `docs/VERIFICATION.md`.

## Document map

- `docs/DEPLOY_PORTAINER.md`: step-by-step safe deployment, `.env`, backups, rollback.
- `docs/PRODUCT_SCOPE.md`: implemented, partial, not yet implemented vs. expanded strategy report.
- `docs/ARCHITECTURE.md`: data ownership, features, imports and scheduling.
- `docs/FILE_MAP.md`: exact file locations.
- `docs/VERIFICATION.md`: tests, what was and wasn't tested.
- `docs/strategy/MLO_Product_Strategy_2026_Expanded.md`: original full strategy report included as a reference, **not a claim that every item shipped**.

## Operational cautions

- The **database backup does not include the separate attachment directory** (`/data/mlo_uploads`). Back up the **entire Docker data volume** to preserve both.
- The public `ntfy.sh` relay is not suitable for sensitive confidential content without appropriate server authentication/encryption and deployment controls. Treat random topics as secret identifiers, not cryptographic end-to-end encryption.
- Local storage, provider quotas and hosted infrastructure cost real money. This project currently has **no billing code** or arbitrary task/project limits, but it does not provide unlimited hosted storage.
- Only **one** Uvicorn worker should run the in-process scheduler. A multi-worker deployment requires moving scheduled reminders to a dedicated job service with locking.
- Self-hosted app security, network access, HTTPS and backups remain the operator's responsibility.
