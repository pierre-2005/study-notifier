# MLO Studio v3.3.0 | Polished interface and working dashboard editor

**My Life Organized (MLO)**, updated from the full v3.2 consolidated app, not a standalone UI mockup.

This version restores the **blue illustrated greeting**, keeps the **v3.1 theme/palette picker**, replaces hard-coded green accents with theme-aware cards, repairs per-account widget/sidebar customization, adds **widget width controls**, and improves task capture responsiveness. Your existing Study/Work/Money/Projects/Calendars/Focus/Spaces functionality remains in the application.

## Start here

- [GitHub → Portainer upgrade steps](docs/DEPLOY_PORTAINER.md) (specifically for the existing Portainer Git stack)
- [v3.3 changes and limitations](docs/V3_3_RELEASE.md)
- [Complete verification notes](docs/VERIFICATION_V33.md)
- [Exact file locations](docs/FILE_MAP_V33.md)
- [Google / Microsoft / Apple calendars setup](docs/CALENDAR_SETUP.md)

## What changed visually

- **Blue welcome artwork** from the original v3.1 direction, inside the compact card layout.
- **Appearance** shortcut on Today opens the existing theme configuration in Settings.
- **All six palettes** (Neutral, Ocean, Sage, Rose, Amber, Lavender) and System/Light/Dark are retained. "Independent" keeps the UI surfaces neutral; "Full theme" colors the surrounding panels.
- Dashboard, sidebar, controls, Focus card, today indicators and action buttons use the chosen palette. No fixed green app theme.
- Responsive grid panels, calmer transitions and more consistent controls.

## Arrange your dashboard

1. Open **Today → Arrange**.
2. Drag **by the card handle** on desktop. Alternatively use the **up/down arrows** in the editor (also work on touch devices).
3. Use the checkbox to hide/show a module. Use **Width** for Small, Medium, Large, Full width or Default.
4. Changes save to the signed-in account, including order, visibility and size. Click **Done**. Reload to verify.
5. **Restore defaults** clears order, hidden cards and width overrides.

Sidebar: click **Customize** in the workspace sidebar to rename, reorder and hide navigation links. Changes are also saved per account. Hidden links can be recovered in that editor; reset restores defaults.

If a card is hidden in arrangement mode it is temporarily shown dimmed so you can bring it back; leaving Arrange hides it normally.

## Responsiveness changes

- Task creation on Today updates the task card and open-task counters without a full navigation.
- Inline task completion uses optimistic feedback with rollback on error and synchronizes visible totals.
- Widget and sidebar editing no longer requires a page refresh and now saves with ordered, debounced requests.
- The previous dense grid packing, which visually hid actual widget order, has been removed.
- Major animations have been reduced to fast, functional interaction feedback; static responses remain compressed with GZip and versioned cached assets.
- Dashboard calendar lookups are bounded to the displayed month. **No production Pi performance guarantee:** evaluate against your actual storage/network with browser DevTools and container stats.

## Local test (optional)

Python 3.12+ recommended. Copy `.env.production.example` into a local `.env` and provide safe dev secrets, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The browser tests need Playwright and Chromium and use an isolated database. Run tests from the project root:

```bash
python tests_smoke.py
python tests_new_features.py
python tests_migration.py
python tests_consolidation.py
python tests_v32.py
python tests_v33_browser.py
python -m compileall -q app
```

## Data and deployment warnings

**Always back up the live `/data` volume (database, uploads and keys) before upgrading.** The existing Git stack should retain its exact current name, `docker-compose.yml`, Portainer environment variables, and `/data` mount. The Compose file refers to a volume called `study_notifier_data`; Docker volume names can be stack-prefixed. Inspect the actual current mount and adapt the Compose declaration before pushing if the names differ. Do not delete any volume and do not run two versions against one SQLite database simultaneously.

A migration from v3.2 is tested. The separately generated v2 database format remains **unverified**, so direct upgrades from v2 require separate testing on a backup first.

This release has not been pushed to GitHub or deployed to the Raspberry Pi in this environment. Real OAuth provider linking and Cloudflare deployment also remain unverified.
