# MLO Studio v3.2.0: exact changed/new files

Upload the **contents** of the `mlo-v3.2-studio/` ZIP folder into the **root** of the existing `study-notifier` GitHub repository. Do not nest the extracted folder under the repository root.

| Location | Change |
|---|---|
| `app/templates/life_home.html` | Full reference-inspired Today dashboard, modular widgets and layout controls |
| `app/static/design32.css` | New visual system for all pages and responsive dashboard layouts |
| `app/static/customize.js` | Drag/drop widget and sidebar editing, keyboard and touch reordering, autosave |
| `app/personalize.py` | Server-validated, private per-user SQLite layout preferences API |
| `app/calendar_links.py` | Encrypted multi-account Google/Microsoft OAuth and ICS calendar connections |
| `app/templates/life_calendar_connections.html` | Connect, sync and disconnect external calendars |
| `app/templates/life_calendar.html` | External event category and connection link |
| `app/templates/life_project_detail.html` | Owner-only destructive project delete confirmation |
| `app/lifeos.py` | Owner-only cascading project deletion, Today mini-calendar data and cached external events |
| `app/templates/base.html` | New sidebar layout, per-user label keys, navigation editor and new assets |
| `app/main.py` | Initializes and registers layout and calendar schemas/routes |
| `app/templates/life_projects.html` | Removes redundant instructional filler |
| `app/templates/life_import.html` | Concise practical CSV import guidance |
| `app/static/sw.js` | New versioned static asset cache, never caches private content |
| `app/static/manifest.webmanifest` | Updated colors and description |
| `app/meta.py` | v3.2.0 version |
| `requirements.txt` | Cryptography and iCalendar parsing dependencies |
| `docker-compose.yml` | Only Compose file for your existing GitHub Portainer stack, correct healthcheck and provider variables |
| `.github/workflows/publish-image.yml` | Multi-architecture GHCR Docker image tag `v3.2-studio` |
| `.env.production.example` | Optional calendar credential configuration examples |
| `.dockerignore` / `.gitignore` | Excludes private local data and unnecessary build files |
| `docs/V3_2_RELEASE.md` | Feature list, current limitations and data safety |
| `docs/CALENDAR_SETUP.md` | Google, Microsoft, Apple subscription and multiple-account configuration |
| `docs/DEPLOY_PORTAINER.md` | GitHub/Pi deployment and rollback steps |
| `tests_v32.py` | Per-user layout, permanent project deletion, calendar configuration/privacy regression |

All other original files remain in their original app folders. No second Docker Compose file is used.
