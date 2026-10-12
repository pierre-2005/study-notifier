# MLO Studio v3.2.0

**New UI and calendar release.** Start with [v3.2 release notes](docs/V3_2_RELEASE.md), [calendar connection setup](docs/CALENDAR_SETUP.md), [GitHub → Portainer upgrade](docs/DEPLOY_PORTAINER.md) and [file map](docs/FILE_MAP_V32.md).

The v3.2 update preserves the consolidated v3.1 source and database model, adds a server-side account-specific layout store, reference-inspired Today interface and optional read-only calendar linking.

---

# My Life Organized | MLO v3.1.0 Consolidated

This release directly addresses v3's duplicated "Classic tools" navigation and disconnected legacy features. It is built on the same existing FastAPI/SQLite Study Notifier source, **not a separate starter prototype**.

## The actual change

The app now has **one** Today dashboard, Tasks module, Calendar and Focus/Timers screen. Legacy to-dos are imported once into `life_tasks`, retaining the original records as recovery history. Study, Work, Money and Spaces are purposeful areas that **use existing academic, finance, jobs and shared-section data**, rather than creating second sets of those records.

- **Today:** regular tasks/projects, plus upcoming coursework, bills and career follow-ups for the admin account.
- **Tasks:** one primary task view. Old To-Do is hidden/redirected. Original to-dos are imported once; completion is mirrored back for compatibility with legacy reminder/digest history.
- **Study:** courses, assessments, weekly classes, Study tasks, Study projects. Academic items continue to be managed in their existing source-of-truth tables.
- **Work & Career:** projects, Work tasks, job applications and follow-ups in one space.
- **Money:** expenses and subscriptions, outstanding balances, links into existing full statement/transaction/budget features.
- **Spaces:** personal/shared projects and existing shared sections, recipes, groceries and checklists.
- **Calendar:** task due dates plus coursework, weekly classes, calendar events, unpaid bills and job follow-ups (admin-only legacy data remains private).
- **Focus & time:** saved timers, countdown controls, task-linked focus and timesheets on the same screen.
- **Design:** one navigation, one command switcher, mobile More navigation, reworked principal list screens, unified CSS styling and contextual back links for detailed legacy screens.

Old course/assessment/job/expense/finance records **are not duplicated or deleted**. Their existing form workflows and notifier behavior remain. Secondary accounts are not shown administrator-owned legacy personal data. The *full report roadmap* is not implemented by this consolidation.

## GitHub → Portainer installation (your actual deployment method)

**Important:** Keep your Portainer Git stack configured with repository `https://github.com/pierre-2005/study-notifier.git`, branch `refs/heads/main`, Compose file `docker-compose.yml` and existing secrets. No Web Editor or Raspberry Pi image-building step is required.

1. **Before pushing, back up the entire current Docker volume and keep an off-device copy.** Ensure the actual existing stack name and volume mapping match `docker-compose.yml`. If the current volume name/path differs from `study_notifier_data:/data`, copy the original declaration into the new file. Otherwise Compose can start with an empty database. See `docs/DEPLOY_PORTAINER.md`.
2. Extract this ZIP and copy its **contents into the root** of your `study-notifier` GitHub repository, not into a second nested folder. Replace the app code/templates/static, Dockerfile, `requirements.txt`, `docker-compose.yml` and `.github/workflows/publish-image.yml`.
3. Commit/push to `main`, then wait for the **Build and publish MLO Docker image** GitHub Action to complete successfully. The workflow publishes multi-architecture `ghcr.io/pierre-2005/study-notifier:v3.1-consolidated`. Ensure the image is publicly accessible to Portainer or configure registry credentials separately. Publishing and making the image public are separate steps.
4. In your **existing Git repository stack**, click **Pull and redeploy** only after GitHub has published the image. Keep port `127.0.0.1:8001:8000`. Do not launch a second MLO stack on the same port or share one SQLite file between two live containers.
5. Test Today, Study, Work, Money, Calendar, Tasks, Focus, user permissions and original records. Verify the pre-v3.1 SQLite backup beside the live database. For problems, roll back to your backed-up database **and** previous Docker image; don't run old code against an already-migrated database without an appropriate rollback.

**Upgrade caveat:** This release is tested against a representative old v1 and packaged v3 database. The separately mentioned v2 database version has **not** been verified as a direct upgrade target, and no actual live Raspberry Pi deployment was performed in this environment.

## Build/run outside Portainer (optional)

Use Python 3.12, copy `.env.production.example` to `.env`, configure secrets, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use `COOKIE_SECURE=false` only when accessing a local HTTP test server. Keep `COOKIE_SECURE=true` with your normal HTTPS/Cloudflare endpoint. Avoid committing `.env` or passwords to GitHub.

## Validation

```bash
python tests_consolidation.py
python tests_smoke.py
python tests_new_features.py
python tests_migration.py
python -m compileall -q app
```

Tests use isolated databases and mock the reminder scheduler. They check rendering, migration idempotency, legacy status mirror, account isolation, migration backup, existing data retention, private files and team sharing. Browser render checks were also performed at mobile/tablet/desktop sizes. Network push delivery, Cloudflare routing, GitHub Actions and Portainer itself are not executed by those tests.

## Navigation and reference

- `docs/DEPLOY_PORTAINER.md`: safe Git/Portainer replacement and rollback.
- `docs/CONSOLIDATION.md`: mapping of duplicated vs unique modules, migration and known limitations.
- `docs/PRODUCT_SCOPE.md`: shipped versus future features.
- `docs/FILE_MAP.md`: exact files and locations.
- `docs/VERIFICATION.md`: automated and browser checks.
- `docs/strategy/`: longer MLO feature roadmap.

**Privacy notice:** the original course, expense, job and statement tables predate private multi-user ownership; they are deliberately visible only to approved administrators. Do not enable them for all accounts without a user ownership/data migration.
