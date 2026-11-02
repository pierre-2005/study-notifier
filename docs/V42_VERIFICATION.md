# MLO 4.2 verification

This release changes the Task map presentation and browser interactions.
The task, layout and relationship APIs and their existing permission/revision
checks remain in use. There is no database schema change.

## Acceptance coverage

`tests_v42_browser.py` serves the actual application with disposable project and
account data. It covers the compact preview, lazy opening without a redundant
map GET, the large modal window, keyboard/focus return, native nested task
dialogs, saving back into the map, persistent positions, Auto arrange and Undo,
branch folding and search expansion, focused branches, connection modes,
prerequisite search and cycle validation, failed-save retry and viewer limits.

It also checks light/dark palettes, desktop/tablet/phone sizes including a short
phone, native two-finger CDP pinch, and a 150-node project whose initial branches
are folded. A drag must preserve the card DOM and issue no layout writes while
the pointer is moving. Accessibility checks use axe-core WCAG A/AA/2.1 AA tags.

The existing v4.1 browser suite opens the new window before exercising the same
task/map/phone flows. Its service and cross-account tests remain unchanged.
The installed-PWA test uses APP_VERSION when reading the current cache instead
of a literal previous release number. No test is disabled.

## Source, layout and release checks

The source checker compiles every Python source/template and checks JavaScript
syntax and current static-cache assets. CSS parsing and browser screenshots are
reviewed separately. Screenshots are actual disposable application states.

The final PR gate runs every regression script (37 scripts after adding this
suite), source checks, and AMD64/ARM64 container build/start. An approved main
merge repeats those checks before image publication. Consult the final PR checks
and delivery RELEASE_STATUS.json for actual completion; this document describes
the gate, not an assertion that a pending run passed.

Local evidence and final results are recorded in V42_RESULTS.json. Automated
checks cover fixture states, not every device/content combination or formal
accessibility certification. Production, a physical Pi and live phone/push,
SMTP/OAuth delivery were not tested by this presentation change.

## Local results

The new workspace suite passed 33 accessibility scans with zero violations and
no JavaScript errors. Existing v4.1 and v4 browser suites passed another 110 and
97 scans, with the v4 suite covering 236 populated route/width states. All ten
v4.1 task/layout service tests passed. All 16 stylesheets parsed without errors
or duplicate declarations within a rule. Source checks covered 66 Python files,
83 templates, 22 JavaScript files and 21 versioned cache assets.

The visual review corrected initial branch clipping, phone resize centering,
focus styling and phone action ordering. The Undo acceptance flow found a stale
success label during its write; saving now shows progress immediately. Native
pinch changed the measured zoom and 150-node dragging retained the DOM with no
writes during movement. The local timing and test history are retained in the
machine report. Exact-head CI must still establish the release gate.
