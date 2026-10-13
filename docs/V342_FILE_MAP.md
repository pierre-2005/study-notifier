# Files changed in v3.4.2

| Repository path | Change |
|---|---|
| `app/static/polish342.css` | **New.** Scoped collapsed-sidebar styles, responsive card spacing, and chart polish. Loaded last. |
| `app/templates/base.html` | Load polish CSS, persist collapsed layout before paint, show navigation tooltips, distinguish quick task from New. |
| `app/templates/life_insights.html` | Explicit zero-activity states for the charts. |
| `app/static/theme.js` | Expand/collapse ARIA state, close quick-add on collapse, notify sidebar editor. |
| `app/static/customize.js` | Close nav editor on collapse and keep renamed tooltips in sync. |
| `app/meta.py` | Version 3.4.2. |
| `docker-compose.yml` | Image tag `v3.4.2-layout`, preserving existing host port and volume mapping. |
| `.github/workflows/publish-image.yml` | Image tag and new layout regression test. |
| `tests_v342_layout.py` | New Chromium geometry/responsiveness test and route smoke check. |
| `README.md` | Deployment and verification notes. |
| `docs/V342_RELEASE.md` | Root causes and checked scope. |
| `docs/NEXT_REVISION_IMPORTERS.md` | Requirements for the next syllabus and bank statement workflows. |

All other application source files are carried over unchanged from v3.4.1.
