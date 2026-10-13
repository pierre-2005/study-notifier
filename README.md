> **v3.4.3 note:** [Calendar read/write setup, sidebar and deployment](docs/V343_CALENDAR_AND_SIDEBAR.md). Read before connecting provider accounts.

# My Life Organized Studio v3.4.2 — Layout & Usability Release

This release fixes the sidebar collapse, spacing between cards, and empty charts without replacing existing modules or changing their data model.

## What was fixed

- Collapsed sidebar: navigation icons stay visible, labels/group headings and reordering controls hide correctly, and no horizontal scrollbar appears.
- Mobile: the drawer still opens fully even when the desktop sidebar preference is "collapsed".
- Navigation accessibility: sidebar links keep meaningful tooltips after renaming, collapse toggle gets an updated accessibility state, and the editor closes when the sidebar collapses.
- Stable loading: the saved sidebar preference applies before the first paint, minimizing layout jumps.
- Insights: separate chart and project rows with real gaps, allow headings to wrap, and improve mobile date-label readability.
- Empty Insights: show a clear, visually quiet empty state instead of fourteen inactive columns.
- Other modules: the core card spacing and page widths are checked on Tasks, Calendar, Study, Work, Money, Projects, Spaces and Focus.
- Versioned CSS added last so the rules cannot accidentally be overridden by older design layers.

The pre-existing six palette choices, light/dark modes, welcome art, project functionality, multi-user accounts, notifications, calendar accounts, tasks, and finance/academic tools are preserved. The database schema is unchanged.

## Deployment: existing GitHub → GitHub Actions → Portainer

1. **Back up your production data volume** and verify the backup before making changes. Include both `study_notifier.db` and any uploaded files in `/data/mlo_uploads`.
2. Extract this archive. **Copy the contents of `mlo-v3.4.2/` into the root of your existing GitHub repository**, including `.github/workflows/publish-image.yml`.
3. Commit to the `main` branch. Wait for the GitHub Actions **Test application** and **Publish multi-architecture Docker image** jobs to succeed.
4. Verify that your existing Portainer stack is configured to read `docker-compose.yml` from `refs/heads/main`, and that the published image is `ghcr.io/pierre-2005/study-notifier:v3.4.2-layout`.
5. In the **existing** Portainer Git stack, click **Pull and redeploy**. Do **not** create a second stack, switch port 8001, or delete the existing `study_notifier_data` volume.
6. Hard-refresh your browser if an older cached stylesheet remains visible.

> **Caution:** The Compose file still names `study_notifier_data`; confirm this matches the volume actually used by your production stack before redeploying. Docker volume names can be scoped by the stack/project name. Do not assume matching YAML names guarantee matching physical volumes. If your stack was renamed, inspect the mounted volume in Portainer first.

## Run locally

Use a Python environment satisfying `requirements.txt`, configure `.env` from `.env.example`, then run `python run_app.py`. Never commit your real `.env` secrets or databases to GitHub.

## Verification

- Python compilation and existing account/permissions, migration, consolidation, calendar, tasks and contrast tests.
- New `python tests_v342_layout.py`: Chromium checking collapsed/expanded sidebar, visible icons, scrollbar suppression, saved visual geometry, separated Insights cards, and responsive behavior across four viewport sizes. It also checks major route responses.

See [Release notes](docs/V342_RELEASE.md), [File map](docs/V342_FILE_MAP.md), and [planned importers](docs/NEXT_REVISION_IMPORTERS.md).

## Scope

This is a targeted, thoroughly tested quality release, not a claim that every possible legacy form has been independently redesigned or that the app has been benchmarked on your Raspberry Pi. Calendar OAuth remains subject to external provider credentials and verification. The syllabus/statement intelligent import workflows are **planned for a future version**, not implemented here.
