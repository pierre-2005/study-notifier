# MLO 4.2: a roomier Task map

The project Task map starts as a compact preview. Click anywhere in the preview,
or focus it and press Enter, to open a large workspace. Close or Escape returns to
the same project page. Reopening keeps the camera, selected task and folded
branches for the current page. The background stays inactive while the window is
open. Task previews and add/connection dialogs open above the workspace; closing
or saving them returns to the map.

## Finding your way

- Cards are larger, with readable titles, status, dates and subtask counts.
  Drag empty canvas to pan, drag a card to move it, and use the overview to jump
  to another part of the map. Fit map shows the whole visible layout.
- Use plus/minus or pinch to zoom. Ctrl/Command plus scroll also zooms; ordinary
  scrolling pans. The percentage button returns to actual size. Arrow keys pan
  the canvas or move a focused card; Shift moves farther, Enter opens the task,
  and F fits the map.
- Search centers a matching task at a readable size. If it is inside a folded
  branch, its ancestors unfold. An unmatched search shows a clear message.
- Click a subtask count to fold or unfold that branch. Larger hierarchies start
  with the top tasks and their immediate children, with deeper branches folded.
  The window reports how many tasks are shown. Show all tasks unfolds everything.
  Folding is only a view operation: it never deletes or moves a real task.
- Focus this branch keeps a selected task, its visible descendants, its ancestors
  and its direct prerequisite neighbors in view. Show entire map exits this view.

## Connections and editing

The default connection view shows the task structure and any prerequisites of
the selected task. Select All connections for the complete web, or Prerequisites
only to concentrate on dependencies. Structure lines are solid; prerequisite
lines are dashed and have arrowheads. Lines use rounded right-angle routes and
separate ports/lanes so sibling connections are easier to follow. Selecting a
card highlights its immediate connections and softens unrelated wires.

The task panel groups details and actions. Open task edits the actual record.
Add subtask creates a real child. Connections distinguishes Subtask of from
Must finish first, and searches the prerequisite list while keeping checked
choices visible. Earlier/Later changes actual sibling order in other project
views. Existing project permissions, task revisions, parent depth/cycle rules
and prerequisite validation still apply.

Auto arrange gives the visible hierarchy generous spacing. It affects only
your personal map positions. Undo arrange restores the preceding positions;
a subsequent manual move or added task clears that one-step undo. Normal drag
positions save to the same per-account/project layout as before. Save failures
retain local positions and offer Retry; a conflicting second tab requires an
explicit reload of the saved layout. Unsaved positions still protect navigation.

## Size, speed and account boundaries

The preview uses actual project names, task names and counts. Full card/line DOM
is created when the window first opens, using the existing server-seeded data.
Opening does not make a redundant map fetch. Panning/zooming changes a transform;
dragging keeps the card DOM and updates only attached wires on animation frames.
Layout writes happen after movement, not for every pointer event. Map CSS/JS load
only with the project map. Current versioned static assets use cache 4.2.1.

Read-only project collaborators can navigate and arrange their own layout, with
shared task edits unavailable. Branch visibility is a current-page preference;
stored coordinates remain personal to the signed-in account. All tasks remain
real project records. The existing 2,000-task map limit retains true counts and
offers List/Board for larger projects. No database migration, key rotation, account
change or new service is required by this release.

## Existing installation rollout

After approval to merge, confirm the main release workflow passes all regression
scripts and both Linux container architectures and publishes
`ghcr.io/pierre-2005/study-notifier:v4.2.1`. Record the actual published digest;
source version and Compose tag alone do not establish publication.

Follow [the existing backup and rollback guide](V4_DEPLOYMENT.md). Preserve the
current running image reference, independently back up the real database,
attachments and private configuration, then redeploy the existing Portainer Git
stack from main. Keep the existing volume, paths, bind port, canonical hostname,
session/credential keys and OAuth configuration. Do not create a second stack.

Check existing records, login, the compact/expanded map, task editing/creation,
drag/save/reload, connections, folded branches, keyboard return and phone layout.
Reload an installed PWA to receive the new static version. Real installation/Pi
performance and physical phone acceptance remain operator checks; local timings
describe disposable fixtures. Production has not been accessed or redeployed.

The 4.2.1 patch preserves automatic positions when Undo follows Auto arrange on
a folded hierarchy. Its fresh static version updates installed PWAs. Use the
verified final digest recorded with the patch delivery.
