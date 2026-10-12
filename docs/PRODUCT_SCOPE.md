# Product scope: shipped preview vs. expanded strategy

**Read this before expecting every feature in the full strategy.** The user's expanded strategy is included verbatim under `docs/strategy/`. It is a multi-release product vision with hundreds of individual requirements; this ZIP is a substantial, working **v3 developer preview**, not a certification that the whole vision is complete.

## Implemented and tested in this preview

- [x] Private multi-user new task/project/note/goal/habit/phone data.
- [x] Approved account onboarding (existing auth); admin approval.
- [x] Useful Today page immediately after login; one-field task capture.
- [x] Responsive desktop, tablet, phone navigation; PWA install metadata; motion accessibility.
- [x] Simple/Guided/Professional user preference; professional view expands advanced creation controls while keeping one data model.
- [x] New unified life task objects, Inbox, open/today/upcoming/overdue/completed, subtasks, priority, estimate, weekly/monthly/daily recurrence, due dates, task dependencies with cycle prevention.
- [x] New projects with name-only setup; boards/list/dated-item views; milestone/risk/issue/decision/deliverable registers; owner/editor/viewer project sharing.
- [x] Optional ready-made project checklists for 35+ work, educational and household roles.
- [x] Project notes and private personal notes with save/edit/delete; file attachments.
- [x] Permissions-checked 10 MB document/image uploads and forced file downloads.
- [x] Deadline calendar for *new life tasks*, with month switching.
- [x] Focus timers with task links, countdown persistence inherited from existing timer service, manually logged time and recent time sessions. Completed focus counts time; breaks and ordinary unlinked timers do not.
- [x] Goals and daily habit check-ins with week counts.
- [x] Cross-project/task/note keyword search within granted access.
- [x] CSV preview, confirmation and safe bounded import (title, due, status, priority, project, area); task CSV export and account-owned JSON export.
- [x] Per-account ntfy phone topics, multiple devices, test/pause/remove actions and daily due-task dispatch job.
- [x] Pre-v3 SQLite backup, versioned assets, gzip response compression, safe paths, account-scoped authorization and smoke tests.
- [x] Existing classic finance/jobs/course/class/reminder/workspace modules carried forward unchanged as protected legacy screens.
- [x] Self-hosting Dockerfile, basic Docker Compose and separate prebuilt-image Portainer stack configuration.
- [x] No billing integration, feature-count paywall or mandatory AI.

## Partial or limited

- [~] **Data integration**: New life tasks are unified within v3, but existing classic `todos`, `items`, jobs and academic events are **not automatically synchronized or migrated**. Their historical screens remain separate. This must be addressed in a version-aware migration.
- [~] **Offline**: PWA install and static asset caching are available. **Private content is not cached for offline reading/editing**, and there is no conflict resolver or offline mutation queue.
- [~] **Career-specific templates**: The report's career families are represented by starter project checklists, **not** full discipline-specific modules, version control, compliance tools, BIM/CAD viewers or managed regulatory systems.
- [~] **Project controls**: milestone/risk/decision records exist, but no calculated critical path, resource optimization, true Gantt UI, deliverable approval chains or advanced custom fields.
- [~] **Time**: task-associated focus and manual time logs work; no native stop-clock timesheet approval/invoicing workflow. Reminders use server timezone and per-day due reminders, not arbitrary task scheduling.
- [~] **Notes**: safe plain-text editing and file attachments, not a block-based WYSIWYG multiuser document editor; no bidirectional backlinks/graph or full-text index.
- [~] **Collaboration**: project-level viewer/editor access with manual username add, not workspace RBAC, per-task role overrides, invitation acceptance, audit-grade history, live cursors or presence.
- [~] **Notifications**: per-user ntfy topics and day-of reminders work at code level; **physical push delivery and scheduler integration need testing on the deployed Pi**. Public ntfy topics are not end-to-end encrypted.
- [~] **Performance**: compressed HTML, client-side optimistic task completion, sensible indexes and static asset cache; not a load-tested guarantee or fully client-rendered SPA.
- [~] **Account protection**: existing signed-cookie sessions and password hashes; no passkeys, native 2FA, dedicated account recovery, enterprise SSO or full security audit.
- [~] **Backup**: consistent pre-upgrade SQLite backup and account-data export; no scheduled tested offsite restore service. Attachments must be separately backed up.

## Not implemented in this release

- [ ] Google Calendar, Microsoft Outlook, Gmail, Drive, Slack, GitHub, Teams, Todoist, Notion, Trello or other live API connectors and two-way sync.
- [ ] Native Android/iOS apps, OS-level widgets, native share sheets, voice capture and real-time collaboration.
- [ ] AI planning/summarization/semantic search/chat, transcription, and AI scheduling.
- [ ] Notion-style relational databases, formula fields, rollups, multiuser rich-text live editor, knowledge graphs, whiteboards and synced blocks.
- [ ] Advanced Gantt resource planning, workloads, burn-down, critical paths, portfolio budgeting and time approvals.
- [ ] Comprehensive custom CRM/invoicing, inventory, engineering drawing/BOM database, medical device QMS, clinical EHR or legal case management.
- [ ] Import directly from other services with OAuth, full Notion HTML/Markdown export import or ZIP attachment import, duplicate record merge tools and background resumable import jobs.
- [ ] Enterprise controls (SSO/SCIM, retention legal hold, full audit trail, organization SLA, encryption key rotation and compliance certification).
- [ ] Production continuous-integration pipelines, Sentry, real uptime alerts, background job leasing/multiworker safety, external penetration testing.
- [ ] Comprehensive cross-platform WCAG audit, real-device performance benchmark, localization and timezones per user.

## Release plan to finish the vision

**Next engineering priority:** validate your actual deployed v2 database, migrate old personal/academic todos into the unified life task model without duplicates, and make one canonical task calendar/reminder pipeline.

**Next product priority:** complete project/task quick-capture and accessibility testing, strengthen permissions and calendar/reminders, then add **reliable offline read/edit/sync**, advanced role templates and data interoperability.

**Later:** full workspace and multi-device sync, real connectors, professional-grade role extensions, automation, AI as opt-in and enterprise hardening.

**Promise to protect:** no complex mandatory onboarding or arbitrary core-content count limits. Offer paid infrastructure add-ons only if they have real operating costs; never lock users out of viewing/editing/exporting their ordinary personal data.
