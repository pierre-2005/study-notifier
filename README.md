# MLO v3.4.2: CI correction + next-release plans

This small additive patch repairs the **GitHub Action test dependency order** and adds the **free Microsoft Store publication plan** to the existing importer roadmap. It does **not** change MLO app source, database schema, Docker Compose or the published image tag.

## Fix confirmed by source inspection

`tests_v342_layout.py` imports `playwright.sync_api` and `bs4` at module import time, but the workflow tried to run the layout test **before** installing either dependency (installation occurred in the next step). A clean GitHub Actions runner therefore cannot run the layout test reliably. The fixed workflow installs both, and Chromium, **before** running the layout and contrast tests. All eight relevant test files pass locally with their dependencies installed. The precise failed GitHub step traceback still needs to be checked to confirm that this was the run's error.

## Install with your existing GitHub → Portainer setup

1. Extract this ZIP.
2. In GitHub, replace the file at `.github/workflows/publish-image.yml` with the supplied file.
3. Add/replace `docs/NEXT_REVISION_IMPORTERS.md`, and add `docs/MICROSOFT_STORE_RELEASE_PLAN.md`.
4. Commit on `main` and open **Actions → Build and publish MLO Docker image**.
5. If the smoke job succeeds and the publish job succeeds, the existing `v3.4.2-layout` image is published. **Only then** redeploy your existing stack in Portainer if you intend to apply the v3.4.2 app update.
6. If a job fails again, expand the **first red step** and provide its log excerpt, particularly the exception traceback.

**Do not** delete or rename Docker volumes, change port 8001, or copy over your current production database for this documentation/CI patch. This patch does not itself deploy the app.

## Plans

- `docs/NEXT_REVISION_IMPORTERS.md` includes syllabus/statement extraction and a new Microsoft Store section.
- `docs/MICROSOFT_STORE_RELEASE_PLAN.md` is the full free-registration, PWA packaging, security, certification, and maintenance plan.
