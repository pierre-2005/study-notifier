# MLO 4.3.0: map display controls and navigation correction

Prepared November 2, 2026. This guide describes the release candidate. A source
version or Compose tag does not establish image publication or deployment.

Open a project, choose Task map, and open the preview window. **Show** offers
All tasks, Open tasks, Completed tasks, To do, In progress, and Blocked. Open
includes To do, In progress and Blocked. Completed corresponds to Done; MLO
does not have a separate closed status. Filtered views expand matching branches
and retain nonmatching ancestors with a dashed border and an Ancestor label.
They report matching and context counts separately. Choose All tasks to fold
branches manually again. Search continues to highlight matching names.

**Layout** switches between Left to right and Top to bottom. Switching is a view
change: existing personal card positions and shared task structure stay intact.
The API continues to use the original horizontal coordinate space. A moved card
is converted to that space before saving, so switching directions, reopening and
Undo do not turn automatic placements into manual coordinates. Auto arrange
remains the explicit action for resetting personal positions.

Use the side/tilt wheel to move horizontally, the main wheel to move vertically,
and Shift with the main wheel as a horizontal alternative. Ctrl or Command with
the wheel zooms. Pixel, line and page wheel units are normalized. Touch selection
waits until a single-finger tap or drag ends, so opening the details panel cannot
move the canvas from under a second finger during a pinch. A large resize brings
a task back into view if the camera would otherwise show only empty space.

The filter and direction persist in local browser storage under the account and
project IDs. They do not sync between browsers. If browser storage is blocked,
the controls still work for the current page. Task edits, project membership and
layout-save permission checks retain their existing server behavior.

The due-date navigation correction removes a closed task preview from the global
draft tracker. Saving a due date and then opening Due dates, Board or another tab
no longer produces a false warning. Real unsaved edits in a connected form still
trigger the existing unload protection. Dismissing a preview discards its edits,
as before.

## Rollout

The proposed image tag is `ghcr.io/pierre-2005/study-notifier:v4.3.0`. Confirm the
final CI and publication evidence before pulling it. Use the existing Portainer
Git stack and volume mapping. Do not create a replacement stack or database
volume. The owner handles Portainer rollout. No database migration is added by
this release; a current database/attachment backup remains part of the existing
upgrade procedure in [V4_DEPLOYMENT.md](V4_DEPLOYMENT.md).

The PWA static cache version advances to 4.3.0. Authenticated pages and APIs are
still fetched from the server. After rollout, reopen the installed app and verify
the displayed version, map controls, a saved due date, and navigation back to the
project. The previous published 4.2.1 image remains available for rollback; keep
the same data volume.

## Expansion scope

The new catalog adds 1,000 proposals to the earlier 1,000. They are research and
planning artifacts, not shipped capabilities. The first engineering pilot should
use drawing registers, issued revisions and one reviewable export adapter before
expanding into deeper coordination workflows. This release has no native AutoCAD,
Navisworks or Bluebeam connector and accessed no workplace account or files.
