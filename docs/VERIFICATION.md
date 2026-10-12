# MLO Next preview verification

## Executed in the build environment

- `python tests_migration.py`: **PASS**: representative classic courses, todos and expenses survived additive database initialization; a consistent pre-migration SQLite snapshot was created.
- `python -m compileall -q app`: **PASS**, all app Python files compile.
- `python tests_smoke.py`: **PASS**: fresh database bootstrap; Home/Tasks/Projects/Notes/Calendar/Focus/Goals/Search templates render; private task creation, status; engineering career project with 5 starter tasks; project notes; preferences; goals/habits; time entry; JSON/CSV export; read/edit sharing controls; two-account data separation; no cross-user private data in exports; focus time log is not duplicated on double completion.
- `python tests_new_features.py`: **PASS**: CSV task import preview and confirm; repeated commit rejected; imported project/tasks; document upload/download/deletion; unrelated account forbidden from downloading private files or managing the other person's phone; backup exists.
- Visual HTML/CSS snapshots generated at **1440×900 desktop, 820×1000 tablet, and 390×844 mobile** for Home/Tasks/Projects/Project detail using headless Chromium: **no horizontal overflow detected**. See `docs/preview/` for representative images.
- The visual runner used `TestClient` HTML with inline local CSS because loopback requests from Chromium were blocked by the execution environment's browser policy; it was **not a live interactive browser test against a deployed Docker container**.

## Not verified

- Docker image build on your actual Raspberry Pi, Portainer stack deployment, Cloudflare proxy TLS, or your **previous v2 database schema**.
- Real ntfy network delivery, scheduled dispatch timing, push permission UX on actual phones, reliable reminder delivery across downtime.
- Native PWA installation/offline mode on Android/iPhone, rich accessibility screen-reader audit, high-concurrency load testing, stress tests of SQLite on Pi microSD, long-lived background scheduler concurrency.
- Regulatory compliance, detailed third-party penetration testing, provider integrations or comprehensive user usability research.

## Important environment note

The build environment did not have APScheduler installed and could not access PyPI to install it. The tests intentionally replace only `app.scheduler` with a **no-op scheduler** before loading `app.main`; the source in the ZIP still declares APScheduler in `requirements.txt` and Docker's install step will fetch it when network access is available. Therefore, scheduled jobs themselves were **not executed** during this test run.

## General conclusion

This is a working and substantially tested **preview** of the core MLO Next features, not a certification that the complete report has been built, deployed or load-tested. Test first with a copy of your live data.
