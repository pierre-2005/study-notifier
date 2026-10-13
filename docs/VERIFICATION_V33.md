# MLO v3.3 verification record

All checks below used isolated test SQLite databases, never the production database.

| Check | Result |
|---|---|
| Python compilation (`compileall`) and JS syntax (`node --check`) | Pass |
| Core smoke tests (`tests_smoke.py`) | Pass |
| CSV, files, phones, backup (`tests_new_features.py`) | Pass |
| Legacy v1 representative data migration (`tests_migration.py`) | Pass |
| Consolidation regression (`tests_consolidation.py`) | Pass |
| v3.2 accounts/calendars/project deletion/layout (`tests_v32.py`) | Pass |
| v3.3 Chromium interactions (`tests_v33_browser.py`) | Pass |
| Palette switching (rose, ocean) | Pass, browser computed style changes |
| Blue hero restored | Pass, browser DOM/visual check |
| Keyboard move; desktop drag and drop; save and reload | Pass |
| Card width override, persistence | Pass |
| Card hide, per-user saved preferences, sidebar rename and reorder | Pass |
| Quick task capture without page reload | Pass |
| Phone/tablet/desktop tested screen overflow | Pass, Chromium 390/820/1440 widths |

Local development-only performance sample: 25 FastAPI `TestClient` requests for Today on an isolated SQLite database with 80 mock tasks had approximately **6.6 ms median and 12.5 ms p95** application round-trip in this environment. This is **not** an end-user network/PageSpeed benchmark, and it does **not** establish Pi speed. Production speed still depends on device, database size, storage, network and browser.

Captured screenshots: `docs/preview/desktop-v33.png`, `docs/preview/tablet-v33.png`, `docs/preview/mobile-v33.png`.

Not executed: real GitHub Actions image publishing, Docker/Portainer image startup (Docker daemon not available in this build environment), live Google/Microsoft OAuth, Cloudflare Tunnel, full offline sync or a full accessibility audit.
