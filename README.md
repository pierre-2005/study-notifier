# My Life Organized (MLO) Studio v3.4 Enhanced

A practical, self-hosted personal productivity app integrating task management, projects, timers, study, work, money, notes, calendars and shared workspaces.

**This is a source-code release, not a deployed service.** It upgrades the v3.3 application and preserves its blue dashboard artwork, modular card arrangements, sidebar customization and independent theme controls.

## New in this release

- Global quick task: click **Quick task**, tap `+` in the mobile header, or press `N` outside a text field. Pick Inbox, Today or Tomorrow.
- Tasks: search, filter by project/priority/area, sort, paginate and save named private filter presets.
- Select several tasks to change their completion/status/priority together (permissions and dependencies checked).
- Insights: 14-day completion/focus trends, project progress, overdue and high-priority items.
- Faster area queries, fewer unnecessary per-request database operations and versioned cached assets.
- Safety: pre-upgrade SQLite snapshot, cross-site write protection and automated privacy/interaction tests.

## Documentation

- [Every audited feature and the honest remaining backlog](docs/FEATURE_AUDIT_V34.md)
- [Release notes, performance figures and test commands](docs/RELEASE_V34.md)
- [Exact GitHub → Portainer instructions](docs/DEPLOY_V34_PORTAINER.md)
- [Previous calendar-provider setup guide](docs/CALENDAR_SETUP.md)
- [Previous MLO release architectural notes](docs/V3_3_RELEASE.md)

## Local setup

Requirements: Python 3.12+ recommended, SQLite, dependencies in `requirements.txt`.

```bash
pip install -r requirements.txt
# Set SESSION_SECRET, APP_USERNAME, APP_PASSWORD and COOKIE_SECURE appropriately
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Read the deployment guide before upgrading an existing Docker volume. Keep secrets out of Git. See `docs/FEATURE_AUDIT_V34.md` for what is and is not implemented.
