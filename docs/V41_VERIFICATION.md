# MLO 4.1 verification and CSS review

Prepared October 30, 2026. Baseline is main commit
`af1a3089cc0dfa502756716dd3fed4f4e9d3e294`, containing released v4.0.0 plus the
owner's upgrades.txt requests. The changes are on `feature/mlo-task-map-polish`.
Release acceptance requires the exact final PR/main checks. Earlier runs are
not evidence for later edits. No production server or real phone was accessed.

## Acceptance coverage

| Request | Verification |
| --- | --- |
| Completion checks | Board/list/preview state and pressed semantics; authoritative recurring counter tests; retained state on rejected saves |
| Save and return | Inspector closes; full task edit returns to originating project/view; inline settings collapse and refresh; Notes, Budget and space saves return; failed saves retain text |
| Drag cards by body | Real Chromium native drag from a task title changes its actual status; existing keyboard/touch/handle suites remain |
| Focus contrast | All six palettes in light/dark, computed timer-control colors and rendered axe checks |
| Phone layout and QR | Phone/desktop expanded cards, actual PNG loads, anonymous topic copy for both platforms; owner-only generation, tamper/expiry/deletion tests |
| Immediate quick-add | Correct To do column and no stray row; no redundant initial board GET |
| Task map | Existing IDs, parent/prerequisite edits and cycle prevention, Earlier/Later ordering, node movement, persisted personal layout, stale-tab conflicts, viewer restrictions |
| CSS | All 15 stylesheets parsed; current components at 375/768/1280/1440, all palettes, plus 59 populated module routes in dark mode |
| Speed | Seeded board/layout, enhanced redirect metadata, no full navigation for task mutations, 150-node drag keeps DOM and sends no requests until release |

Ten new service acceptance tests cover ACLs, revisions, atomic graph changes,
layout validation/limits, recurring counters, enhanced POST/session behavior,
scoped expiring pairing and additive/idempotent schema. The new browser suite
adds 16 component/width states and 110 accessibility scans. Existing 34 scripts
remain, giving 36 scripts in the complete suite. Historical assertions were
updated only for intentional new Save/return/pairing behavior; a lightweight
legacy DB fixture now includes the real updated_at field, and the old browser
HTTP bridge now provides an actual Response with the server's content type.

The 3.7.1 migration/restore rehearsal remains in the suite, preserving all 66
original tables/rows/columns, WAL, credentials, ownership, preferences and the
attachment hash. Existing 4.0 records are not rewritten to build the map. The new
metadata table is additive, its values are personal, and initialization is
idempotent. Large-map tests preserve all 2,001 fixture tasks and their true count.

## CSS review findings and corrections

The source review parsed every stylesheet, including retained compatibility
assets. Three stylesheets are current: app.css, public.css and onboarding.css.
No parse errors or duplicate declarations within a rule were found. Intentional
responsive/theme rules remain. The current shared components were reviewed as
rendered states, not by assuming source syntax guarantees a usable interface.

Corrections include the forced black focus/current-day foreground in dark mode,
neutral/amber dashboard links below 4.5:1 contrast, filled danger buttons needing
a separate background from danger text, completion-button padding/glyph rendering,
phone QR/card wrapping, mobile targets/input sizes and consistent keyboard focus.
Accessible names for dashboard navigation/day links were aligned with visible text.
Map selection raises the chosen node; automatic positions avoid saved nodes.

The first expanded run found these additional shared contrast issues. They were
fixed and the affected review was repeated. Automated accessibility covers
fixture states and does not establish certification or every device/content case.
No live SMTP/OAuth/push delivery, actual installation backup rehearsal, Store
acceptance or physical Pi performance claim is made.

## Evidence and release gate

Machine-readable source/CSS, browser, timing and regression evidence is linked
from the PR and included in its CI artifact. The final PR must pass all 36 scripts,
source checks and AMD64/ARM64 container build/start. An approved main merge then
repeats validation before image publication. See V41_SETUP.md for installation
contracts, signed-QR behavior, limits and owner rollout checks.
