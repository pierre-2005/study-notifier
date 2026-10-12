# MLO v3.1 scope: what's integrated and what's not

This is a consolidation release responding to duplicate Classic Tools and disconnected old screens. It builds on v3, not the entire hundred-feature strategy report.

## Implemented

- One navigation with Today, Tasks, Projects, Calendar, Focus, Notes, Goals/Habits, Study, Work, Money, Spaces.
- One task list, imported original todos, completion mirroring, idempotent migration and deleted-record tombstones.
- One calendar reading new life tasks + existing academic deadlines/classes/events + unpaid bills/job follow-ups.
- Study, Work, Money, Spaces dashboards built over *existing source-of-truth records* rather than copying records into separate schemas.
- Quick-add tasks with correct Study or Work area directly from those areas.
- Timer management integrated with focus on one screen, original timer state preserved.
- Modern primary lists for courses, assessments, jobs, bills and shared sections.
- App-wide typography/card/input/button treatment and navigation breadcrumbs to detail pages.
- Private user-scoped projects/tasks/notes and existing collaborative sections, account phones, imports, exports, file permissions and project sharing from v3.
- A single GitHub-to-Portainer Compose file plus GHCR automated build workflow.

## Not fully implemented

- Existing specialized edit/detail forms, advanced finance dashboards and grocery planners still retain old markup, styled consistently but not individually rewritten as modern components.
- Legacy finance, school and career records cannot be shared among individual non-admin accounts because the original tables lack ownership. A safe per-user database migration is still needed.
- Automatic two-way reconciliation with external scripts writing directly to old `/todos` endpoints is not supported.
- Native offline edits/sync, integrated real third-party APIs, collaborative WYSIWYG, AI, advanced Gantt, custom professional systems, production incident monitoring and full product roadmap remain future tasks.

## Testing boundaries

Unit/integration tests and headless Chromium responsive reviews passed against throwaway test databases. Real GHCR publication, Portainer redeploy, production backup restore, external notifications and live Cloudflare routing were not tested. Do not skip production backup or v2-specific migration review.
