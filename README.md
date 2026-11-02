# My Life Organized 4.3

MLO is a self-hosted workspace for tasks, projects, calendars, study, work, notes,
shared spaces, focus time and personal finances. FastAPI, Jinja, vanilla
JavaScript and SQLite remain the application platform. The browser and installed
PWA use the same server data.

Version 4.3 adds Task map status filters, labeled ancestor context, left-to-right
or top-to-bottom layouts, and horizontal/Shift-wheel panning. View preferences
stay specific to your account and project in this browser. Layout coordinates
and Undo remain compatible with earlier versions. Phone gestures and responsive
camera recovery keep the canvas usable as the details panel or window changes.
Saving or dismissing a task preview now clears its draft entry, fixing a false
leave-page warning when switching to Due dates or another view.

The expanded 2,000-item feature catalog is a proposed product backlog. This
release implements the map/navigation changes above; it does not implement
all of those proposals. See the [release guide](docs/V43_SETUP.md),
[verification report](docs/V43_VERIFICATION.md), and
[expansion plan](docs/EXPANSION_ROADMAP.md).

Read the [4.2 interaction and rollout guide](docs/V42_SETUP.md) and
[verification report](docs/V42_VERIFICATION.md). The [4.1 guide](docs/V41_SETUP.md),
[earlier setup](docs/V4_SETUP_REPORT.md) and
[backup/rollback procedure](docs/V4_DEPLOYMENT.md) retain existing installation
contracts. Source version or Compose tag alone does not establish image
publication or production rollout.

## Existing installation

Keep the current Portainer Git stack, `refs/heads/main`, root
`docker-compose.yml`, `study_notifier_data:/data`, `/data/study_notifier.db`,
`/data/mlo_uploads`, and `127.0.0.1:8001:8000`. Keep
`https://organizer.overvault.ca`, the registered OAuth callback, existing
accounts and all current secrets. The owner pulls/redeploys the existing stack
after verification and image publication. Do not create a second stack or a new
volume to upgrade.

Before rollout, rehearse an actual private backup using the deployment guide.
The startup snapshot supplements an independent backup and coordinated
attachment/configuration snapshot. Run one scheduler worker per database.

## Product boundaries

- Projects are private by default; their creator controls sharing. Account
  administrators do not automatically get private project/device access.
- Historical Finance, academic and job records remain bound to their original
  installation owner. This release does not expose those tables to every account.
- Statement import supports BMO and Scotiabank PDF formats. Review imported
  transactions; universal bank formats are not implemented.
- Course imports create actual tasks after source review. Optional AI requires
  configuration and per-upload consent. Arbitrary lecture recurrences and LMS
  extraction are outside the current importer.
- Google/Microsoft writes use the selected account/calendar. Ordinary ICS
  subscriptions are read-only. Background refresh continues automatically.
- Notes support a compact Markdown subset, explicit saves and stale-edit
  protection. This is not live collaborative block editing.
- The PWA caches public static assets only. Private pages, APIs and offline
  editing are not cached. Store package identities/versions are separate.

## Verification

Use Python 3.12, the pinned timezone data, Tesseract/Poppler and the dependencies
in `requirements-test.txt`. Set `PYTHONTZPATH` to an empty value. Install
Playwright Chromium and `axe-core@4.14.0`; set `MLO_AXE_PATH` to `axe.min.js` and
optionally `MLO_BROWSER` to a Chromium executable. Run:

```sh
python -m compileall -q app scripts
python -m scripts.check_source
python scripts/run_regression.py
```

Every standalone regression runs in its own process. Browser tests serve the
actual application against disposable populated data. GitHub additionally
builds/starts AMD64 and ARM64 containers before any main-branch publication.
Full evidence and installation checks are in the verification/setup reports.

Earlier release documentation is retained under `docs/` as historical context;
the v4 reports describe the current behavior.
