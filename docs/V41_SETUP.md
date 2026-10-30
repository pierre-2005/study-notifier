# MLO 4.1 setup and rollout

Prepared October 30, 2026. This source targets version 4.1.0. The current PR's
exact checks and actual main publication determine release status; the version
string and Compose tag alone do not establish publication or deployment.

## What changes for users

- Task completion has one consistent check drawing, an accessible pressed state,
  immediate feedback and rollback on failure. Recurring-task counters account
  for a newly created successor rather than incorrectly reducing open work.
- Quick capture updates the current board immediately, including empty boards.
  It uses the same task IDs as List, Table and the map. New task positions append
  consistently to their real sibling/status group.
- Board cards drag from their title or body. Checkboxes, menus, inputs and selects
  keep their normal actions. On a phone, hold a card until the columns highlight,
  then drag it across. The handle, touch controls and keyboard alternatives
  remain. Pending writes briefly disable conflicting task controls; task previews
  wait for their own pending status write before reading an editing revision.
- Save closes a task preview or inline editor. A clean full-page save returns to
  the view that opened it, including its query and scroll position. Directly
  opened editors use a sensible module fallback. Failed saves, expired sessions,
  stale revisions and text typed while a save is pending keep the editor open.
  This applies to Save buttons and custom Budget, Notes, preferences and planner
  saves. Ordinary Add/Delete/Start actions retain their own workflows. Navigation
  context contains URLs/scroll only, is session/account scoped and expires after
  12 hours; it never stores draft amounts or note contents.
- Focus plus/minus controls use theme-aware text and borders, with larger phone
  targets. Shared dashboard-link, current-day, destructive-action, focus and
  pairing styles also received contrast and responsive corrections.

## Project task map

Open a project and choose **Task map**. Pan the canvas, zoom, search, fit or arrange.
Drag a node, or focus it and use arrow keys, to move it. Enter opens its preview.
Add tasks/subtasks directly; Relationships edits the real parent and prerequisites
atomically. Earlier/Later changes the real sibling order. Parent depth, dependency
cycles, completion prerequisites, stale revisions and project roles are enforced
on the server. A project viewer cannot change tasks or relationships.

Canvas positions are private to the account. They save automatically to the new
additive `mlo_task_map_layouts` table, keyed by the existing user/project IDs, with
conflict detection. Viewers may arrange their own view. No task copy or competing
status store is introduced. Deleting a user/project removes its layout metadata.

The interactive map supports up to 2,000 tasks; larger projects retain their real
counts and all existing tasks and direct users to List/Board. Layout payloads
are bounded and validate finite coordinates and membership before writing. This
limit protects browser responsiveness; it is not a task deletion or project cap.

## Phone pairing without a second sign-in

The device owner still signs in on the computer to generate/view private QR codes.
Each iPhone/Android code opens a signed, scoped, 15-minute copy page on the phone.
No MLO login is needed on that scan page. Copy the topic/server into ntfy; Android
also has the ntfy subscription deep link. Expiry affects the scan link, not the
created subscription. Refresh QR codes if a scan link expires.

Keep the QR/topic private. A scan link grants access only to that phone's topic,
not its owner's account or workspace. Tampering, expiry, device removal/topic
change, or owner deactivation invalidates the relevant link. QR images remain
owner-only. Copy pages use no-store, no-referrer and no-index headers. The previous
owner-only iPhone guide remains available for old bookmarks.

Keep `MLO_PUBLIC_URL=https://organizer.overvault.ca` and the existing HTTPS ntfy
base URL. No new secret is needed; signed links use the existing `SESSION_SECRET`.
Do not rotate it during upgrade. QR pairing needs an HTTPS public URL; manual
subscription remains available when it is not configured. Real phone camera,
clipboard permissions and push delivery still require a controlled phone check.

## Performance work

Board data and per-account layout preferences are included in the authenticated
HTML, avoiding redundant boot requests and sidebar/layout flicker. Task writes
update the current view, with targeted refreshes where filters must be applied.
Enhanced POSTs return redirect metadata, so Save does not fetch a discarded editor
page before returning. Cookies/session changes are preserved. Map drags use
animation-frame transforms and update only incident lines; layout writes are
coalesced after movement. The map script loads only in its project view.

Versioned assets and the static-only service worker advance to 4.1.0. Private
HTML, task APIs, pairing pages and drafts remain outside the offline cache.
Local fixture timing is evidence about that test environment, not Pi performance
or an internet-latency guarantee. Test a representative project on the actual Pi.

## Existing-stack rollout and rollback

1. Confirm the exact PR head passes all 36 scripts and both container checks.
   After an approved merge, wait for the main validation/publication workflow.
2. Record the actual published `ghcr.io/pierre-2005/study-notifier:v4.1.0` digest
   and Linux AMD64/ARM64 manifests. Preserve the running stable image digest.
3. Follow [the existing backup/rehearsal and rollback procedure](V4_DEPLOYMENT.md).
   Take an independent coordinated backup of the actual database, uploads and
   private configuration before rollout; the prior one-time v4 startup snapshot
   is not a fresh backup of the current 4.0 installation.
4. Redeploy the existing Portainer Git stack from main. Keep the existing volume,
   `/data/study_notifier.db`, `/data/mlo_uploads`, `127.0.0.1:8001:8000`, session and
   credential keys, OAuth clients/callback and canonical hostname. Do not activate
   the deferred www hostname or create a second stack. Run one application worker.
5. Check health, login, existing records/files, task completion/creation/drag,
   save/return, maps and a real iPhone/Android scan plus personal test notification.
   Reload an installed PWA and confirm current assets. SMTP/OAuth/live-phone and
   physical Pi acceptance remain operator checks; no production access was used.

If rollback is needed, quiesce writes and restore the matched backup/config/files
and recorded stable digest using the existing guide. Preserve new writes for
reconciliation and retain the upgraded snapshot. Do not delete the original volume.
