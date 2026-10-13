# MLO Studio v3.4.2 — Release & verification

## User-reported issues

| Issue | Root cause | Fix |
|---|---|---|
| Sidebar appears broken when collapsed | Broad `.sidebar-collapsed .nav-item span` selector hid span-based navigation *icons*; newer Workspace/Customize/Spaces headings kept their expanded widths. | Explicit desktop collapsed rules hide labels and headers while showing glyph spans, clipping horizontal scroll, retaining scrollable nav, and centering footer actions. |
| Sidebar changes jump on first page load | Saved collapsed state applied only after DOMContentLoaded. | Apply persisted collapsed state in early head script before CSS loads. |
| Insights cards touch or overlap | No vertical gap between sibling `.mlo-two` containers. | Explicit vertical rhythm on Insights with a responsive flex-column layout and spaced grids. |
| Hard-to-read chart dates | 14 labels squeezed into narrow chart columns. | Hide alternating labels on small screens; retain individual tooltip text and chart summaries. |
| Charts look unfinished with no data | Rendered 14 empty columns even with no activity. | Neutral empty-state panel; full chart preserved when data exists. |
| Existing UI feels inconsistent | Incremental older/newer stylesheet layers | Small, final `polish342.css` correction layer using theme tokens, no hard-coded new accent color. |
| Brief unreadable buttons while switching themes | Background colors animated after text colors changed immediately. | Disable background-color transitions on core actions so theme switches remain readable. |

## Scope of app audit

The v3.4.2 browser test exercised the core eight screens at desktop, compact desktop, tablet, and mobile widths and checked page-wide horizontal overflow. It also checked rendering and response status for the primary 23 destination routes across academic, work, money, spaces, admin and settings. It did *not* prove that every legacy edit form and every workflow is defect-free.

## Deployment verification

The package keeps the existing external entry port 8001, `/data/study_notifier.db`, `/data/mlo_uploads`, and the original Compose volume name. It uses image `ghcr.io/pierre-2005/study-notifier:v3.4.2-layout` and the existing GitHub Actions → GHCR → Portainer deployment strategy. No new environment variables are needed.

## Test commands

```bash
python -m compileall -q app
python tests_smoke.py
python tests_new_features.py
python tests_migration.py
python tests_consolidation.py
python tests_v32.py
python tests_v34.py
python tests_v33_browser.py
python tests_v34_browser.py
python tests_v341_contrast.py
python tests_v342_layout.py
```

The browser tests require `playwright`, `beautifulsoup4` and Chromium. The GitHub workflow installs these before running the new test.
