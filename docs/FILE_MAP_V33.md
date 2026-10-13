# MLO Studio v3.3 file map

The ZIP contains a complete project replacement, not a patch-only fragment. Extract into the **root** of the existing `study-notifier` GitHub repository.

## New/updated core files

| Repository path | Purpose |
|---|---|
| `app/static/design33.css` | NEW. Theme-aware card visual system, blue hero, responsive dashboard widths and active layout styling |
| `app/static/customize.js` | REPLACED. Reliable drag/keyboard/touch editor, per-user persistence, labels, hide/show and width controls |
| `app/templates/life_home.html` | CHANGED. Blue hero, Appearance/Arrange actions, layout status and task counters |
| `app/templates/base.html` | CHANGED. Loads versioned `design33.css` after the existing theme styles |
| `app/static/life.js` | CHANGED. Optimistic task completion and immediate dashboard task insertion/count feedback |
| `app/personalize.py` | CHANGED. Migrates and validates `widget_sizes`, preserves per-account layout settings |
| `app/lifeos.py` | CHANGED. Bounded dashboard calendar date lookups |
| `app/meta.py` | CHANGED. Version 3.3.0, cache busting |
| `app/static/manifest.webmanifest` | CHANGED. Neutral/blue app theme |
| `app/static/sw.js` | CHANGED. v3.3 versioned static cache (private data not cached) |
| `docker-compose.yml` | CHANGED. Pull v3.3 GHCR release image, preserve port and `/data` volume |
| `.github/workflows/publish-image.yml` | CHANGED. Publish v3.3 multiarch Docker image on main commits |
| `README.md` | REPLACED. v3.3 navigation and operational instructions |
| `docs/DEPLOY_PORTAINER.md` | CHANGED. Current Git stack instructions, volume safeguards and rollback |
| `docs/V3_3_RELEASE.md` | NEW. Scope/limitations |
| `docs/VERIFICATION_V33.md` | NEW. Tests and unverified environment-specific operations |
| `docs/FILE_MAP_V33.md` | NEW. This map |
| `tests_v33_browser.py` | NEW. Browser interactions exercised against an isolated FastAPI test backend |
| `tests_v32.py` | CHANGED. Adds layout width isolation checks |
| `docs/preview/*-v33.png` | NEW. Actual Chromium screenshots |

## Preserved features

All other `app/` modules, the Dockerfile, requirements, login/auth, calendar linking, projects/tasks, finance, legacy migrations, phone reminder system, and older specialized sections remain in the source. Read `docs/PRODUCT_SCOPE.md` for remaining planned features.
