# MLO 4.3 verification

The focused navigation regression was reproduced against the original 4.2.1
scripts: a saved task-preview due-date edit left a removed form in the global
draft Set. Clicking Due dates produced a native beforeunload warning. The fixed
scripts passed the same sequence. Tests additionally verify dismissing a preview,
retaining protection for a real unsaved task-page edit, and saving/returning.

`tests_v43_browser.py` uses a disposable loopback fixture. It covers all six map
status choices, ancestor context for a completed child under an open parent,
empty search, two orientations, orientation changes without layout writes,
coordinate compatibility after moving, Undo across direction changes, browser
preference persistence and project isolation, pixel/line/page wheel units,
Shift-wheel panning, actual browser horizontal wheel input, Ctrl-wheel zoom,
375/390/768/1440 widths, dark mode, 150-task layout non-overlap, finite edge
coordinates, JavaScript errors and accessibility scans.

The historical `tests_v42_browser.py` passed after correcting a phone gesture
regression found during this work: selecting a card on the first touch opened
the details panel and changed the canvas height before the second touch. It now
selects after the interaction, preserving native pinch behavior. This suite also
covers folded-layout Undo, save/retry/conflict, viewer permissions, six sizes,
DOM preservation while dragging and 33 accessibility scans.

Full 38-script regression and final CI results are recorded in the delivery
metadata after completion. No local or CI fixture establishes production latency,
real-mouse driver compatibility, or native vendor-format/API compatibility.
Horizontal input tests use browser-generated horizontal wheel events; testing the
owner's particular mouse after rollout remains useful. No production database,
workplace application or Portainer environment was accessed.
