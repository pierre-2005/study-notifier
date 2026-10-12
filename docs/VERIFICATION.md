# v3.2 verification

- All four previous regression suites passed in an isolated local database.
- New `tests_v32.py`: private layout persistence, calendar account isolation, ICS allowlist, project deletion permissions and database cascade passed.
- `compileall` and `node --check app/static/customize.js` passed.
- Chromium rendering at 1440, 820 and 390 pixels for Today/Projects/Task views: no horizontal overflow.
- New desktop and mobile dashboard previews in `docs/preview/desktop-home-v3.2.png` and `docs/preview/mobile-home-v3.2.png`.
- GitHub Actions publication, live Portainer deployment, real Google/Microsoft authorization, live iCloud calendar sync and full screen-reader accessibility audit **were not performed here**.

# v3.1 verification report

Executed against isolated local SQLite test databases; not against a live Portainer deployment.

- `python -m compileall -q app`: passes.
- All HTML templates: Jinja syntax parsing passes.
- `python tests_smoke.py`: passes, multi-account isolation, project permissions, goals, notes, focus time, exports and academic routes.
- `python tests_new_features.py`: passes, CSV import idempotency, private attachments, per-user phone topics and backup.
- `python tests_migration.py`: passes, representative old data survival and backup.
- `python tests_consolidation.py`: passes, one-time legacy todo import, deleted import tombstone, original todo status mirror, new area routes and calendar, redirects, cross-account privacy and pre-v3.1 backup.
- Headless Chromium HTML/CSS snapshot check at **1440**, **820**, **390** pixel viewport widths across Today, Study, Work, Money, Calendar, Focus. No horizontal document overflow reported. Screenshots under `docs/preview/`.

**Not claimed:** full accessibility audit, live external notification tests, actual Raspberry Pi performance benchmarks, full v2 database migration compatibility, real GitHub Container Registry publication, Portainer rollout or exhaustive custom professional workflow QA.
