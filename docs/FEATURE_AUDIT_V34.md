# MLO Feature and Performance Audit | v3.4

This is the code-based improvement inventory for the available MLO v3.3 source and v3.4 implementation. It is a broad actionable audit, not a claim that every possible industry feature exists. **Implemented in v3.4** and **Earlier functionality** are distinct from **Next** and **Long-term**. The latter are not delivered in the ZIP.

## Delivered in v3.4

- [x] A global, accessible quick-task dialog on signed-in pages, keyboard shortcut `N` (outside text inputs), and a phone header button. Select Inbox, Today or Tomorrow. Uses server-backed saves and feedback.
- [x] Task search with escaped literal matching, priority, area and project filters.
- [x] Task sorting by due date, priority, newest, oldest or title.
- [x] Server-side task pagination in 40-item pages with totals and next/previous navigation (no 250-task hard cut-off).
- [x] Private, named saved filters (up to 20 per account) with deletion.
- [x] Bulk multi-select task actions: complete, reopen, mark in progress/blocked, change priority. Atomic permission checks; respects unfinished dependencies and recurrence.
- [x] Viewer-only shared project records show read-only task controls in the task browser.
- [x] Insights dashboard: last 14 days' completed tasks, focus minutes, overdue and high-priority counts, project completion progress, upcoming deadlines.
- [x] Optimized area hub task queries to filter Study/Work at the database rather than fetching and filtering an arbitrary 200 rows.
- [x] Extra task/time access indexes, and task pages that fetch only the requested page.
- [x] Skip sidebar/timer database lookups on API and form POST requests that do not render the app shell.
- [x] Long-lived static asset cache for versioned paths; private/no-store responses for signed-in dynamic pages.
- [x] A one-time consistent pre-v3.4 SQLite backup at startup when an existing DB is present.
- [x] Cross-origin and cross-site write rejection for session-based form and API actions.
- [x] Desktop/tablet/mobile styling, accessible focus handling, escape-close, keyboard/focus control and small feedback notifications.
- [x] Regression tests for filtering, 5,000-task workload, saved filters, private analytics, bulk edit, permission enforcement, browser controls and responsiveness.

## Earlier functionality retained in v3.4

- [x] Blue hero dashboard, modular widgets, resize/reorder/hide, personal layouts.
- [x] Six selectable palettes, appearance modes (system/light/dark) and independent/full palette styling.
- [x] Reorder, rename and hide sidebar navigation.
- [x] Personal projects, task dependencies, recurrence, project member roles, notes, milestones, risk/issue/decision records.
- [x] Project deletion with task and attachment cascade, owner-only checks.
- [x] Shared custom sections, groceries and recipes.
- [x] Course/assignment/lab/exam, class schedule and job application hubs.
- [x] Expense and finance tools, financial imports, budgets and bills.
- [x] Countdown timers, task-linked focus sessions and time entries.
- [x] Calendar with events and read-only Google/Microsoft OAuth connectors and iCalendar feeds, subject to provider credentials; Apple through feed subscriptions, not native CalDAV.
- [x] Private per-user devices and ntfy notification topics, phone notification test.
- [x] Task CSV import preview, duplicate protection, data JSON export, installable PWA shell and cached static files (not offline edits).
- [x] Free core with no task/project count paywalls.

## Backlog: the remaining product improvements

Legend: **P1** next high-value increment, **P2** medium-term, **P3** specialized / larger scope. None of the below are claimed complete.

### First-run simplicity and navigation

- P1: One-minute guided onboarding with optional skip, setup progress, context-based defaults.
- P1: Single cross-module quick capture for tasks, notes, events, expenses and ideas.
- P1: Universal editable recent items and favorites/pinned navigation.
- P1: Better empty states with example projects that can be discarded cleanly.
- P1: Standard undo/toast design for destructive and reversible operations.
- P1: Cross-module global activity center, personal notifications feed and read/unread.
- P2: Guided weekly review and smart cleanup for overdue projects.
- P2: Configurable home panels for multiple roles and life areas.
- P2: Custom nav folders and workspaces nested more than one level.
- P2: Multi-language support, regional date/time preferences, right-to-left layouts.

### Task engine

- P1: Recycle bin for deleted tasks/projects with restore and configurable retention.
- P1: True batch move to projects/areas, due-date changes and tags (current batch supports status/priority only).
- P1: Recurring tasks with richer patterns, exceptions and timezone-aware reminders.
- P1: Keyboard-first inline task editing and drag reorder in task lists.
- P1: Assigned-to-me, delegated-to-others, waiting-for and upcoming week views.
- P1: Task comments, @mentions, read receipts and changelog.
- P1: Attachments preview / document search.
- P1: Saved view sharing within projects, not just personal saved views.
- P2: Custom field builder, calculated fields, formula columns and rollups.
- P2: Kanban swimlanes, workload labels, matrix Eisenhower and subtasks progress.
- P2: Dependency constraints, cycle visualization and automatic planning suggestions.
- P2: Inbox by email, browser extension, voice dictation and native share-sheet capture.
- P2: Versioned task event log and audit trail.

### Project management

- P1: True project duplication and flexible project templates.
- P1: Project archives and reversible project deletion.
- P1: Rich project overview editable by drag arrangement.
- P1: Deliverables, approvals, deadlines and linked documents on one project timeline.
- P1: Portfolio-wide cross-project dashboards, grouping and search.
- P2: True Gantt and dependencies with rescheduling, critical path and milestones.
- P2: Resource allocation, workload capacity and resource calendars.
- P2: Budget baselines, cost codes, earned value and timesheet approvals.
- P2: Client/guest portal with scoped sharing and approval flows.
- P2: Risk matrices, decision logs, issue escalations, RACI chart and templates.
- P3: Engineering change workflows (ECO/ECN), BOM, panel scheduling and drawing revisions.
- P3: Formal regulated review and traceability matrices, where appropriate.

### Calendar and scheduling

- P1: Background incremental provider sync with transparent sync errors, not just manual sync.
- P1: Calendar color mapping and multiple-account consolidated conflict detection.
- P1: Agenda with task drag-to-schedule and time-blocking.
- P1: Recurring external events and timezone-safe event editing.
- P2: Bidirectional Google and Microsoft sync, conflict policy and permissions.
- P2: CalDAV provider connection, including supported private Apple calendars (currently feed-only).
- P2: Scheduling assistant, working hours, availability sharing and meeting booking.
- P2: Natural-language scheduling, travel-time estimates, focus time protection.
- P3: Native mobile OS calendar integration.

### Focus, attention and wellness

- P1: Unified countdown, stopwatch and Pomodoro timer history.
- P1: Better focus-session interruptions, pauses and backdated corrections.
- P1: Task estimate vs actual, timesheet export and weekly time reports.
- P1: Low-friction break and rest prompts, optional focus notifications.
- P2: Background mobile notifications and reliable offline timer completion.
- P2: Billable vs nonbillable time, rates and invoice links.
- P2: Energy-aware workload planning and configurable personal routines.

### Notes, knowledge and research

- P1: Modern document editor with autosave, revision history and recoverable drafts.
- P1: Internal links, backlinks and universal search across content and attachments.
- P1: Rich-text tables, mentions, embeds and templates.
- P2: Real-time collaboration with conflict resolution and comments.
- P2: Research citation organizer, PDF annotation and bibliography export.
- P2: Knowledge graph, canvases/whiteboards and linked diagrams.
- P3: Knowledge database schemas with roles and property-specific views.

### Education, career and industry packs

- P1: Course and assignment/task unified record model with user-specific ownership.
- P1: Grade calculator, weighted scores, term progression and transcript summaries.
- P1: Study spaced repetition, flashcards and exam planning.
- P1: Internship and recruiting pipeline with interview notes and follow-ups.
- P1: Project templates by career, with controlled data fields and dashboards.
- P2: Research/lab notebook, experiment tracking and dataset logging.
- P2: Engineering drawing register, transmittals, RFI and vendor submission tracking.
- P2: Construction inspection/work order/maintenance checklists and asset tracking.
- P2: Sales CRM, proposals, quotes, agreements and contact histories.
- P2: Content publishing pipeline, approval and performance analytics.
- P2: Education lesson scheduling, grading and curriculum planning.
- P3: External EHR/ERP/CAD/PLM/finance integrations and regulated audit controls.

### Home and finances

- P1: Household shared reminders, chores, shopping and recurring routines.
- P1: Unified transaction/expense budgeting, monthly summaries and tagging.
- P1: File receipts, recurring payments and subscription renewal alerts.
- P2: Rules for statements, duplicates and reconcile-to-budget workflows.
- P2: Category goals, debts, amortization and sinking funds.
- P2: Meals/recipe shopping integration, pantry stock and waste reduction.
- P2: Warranty dates, home maintenance and inventory.
- P3: Bank synchronization (requires provider and security/privacy review).

### Collaboration and security

- P1: Full per-user ownership migration for legacy study, finance and job tables. Those original records are still admin-only, not generalized multi-user data.
- P1: Account recovery, password reset, sessions and trusted-device management.
- P1: Two-factor authentication/passkeys and login rate limits.
- P1: Defined permission matrix across all modules, not just projects.
- P1: Audit logging, activity history and deletion recovery.
- P1: Automated backup restore drills and disaster-recovery documentation.
- P2: Organizations, multiple workspaces, granular sharing and guest accounts.
- P2: File antivirus scanning, quotas and secure link sharing.
- P2: Privacy center, export/delete request lifecycle and consent controls.
- P3: Enterprise SSO/SAML, organization-wide controls and compliance features.

### Integrations, automation and intelligence

- P1: Provider sync status page and connection error diagnostics.
- P1: Import/export of every major module (not just tasks).
- P1: Webhook actions and human-readable automation rules with run logs.
- P2: Google Drive, OneDrive, GitHub, Teams/Slack, email, Zapier/n8n connectors.
- P2: Import from Notion/Todoist/ClickUp and export to portable formats.
- P2: AI-assisted summarization and drafting with opt-in control and visible citations.
- P2: Conflict-aware scheduling suggestions and smart project estimations.
- P3: Local on-device AI for sensitive self-hosted workloads.

### Speed, deployment, reliability and accessibility

- P1: Repeat profiling on actual Raspberry Pi with realistic database, files and multiple users.
- P1: Instrument p50/p95 latency, SQL timings, error rates and client-web-vitals.
- P1: Automated production database restore test from encrypted backups.
- P1: E2E GitHub Actions CI and release gating before image publication.
- P1: Controlled migration/rollback strategy and smoke test during Portainer redeploy.
- P1: More accessible project/editor drag controls and mobile touch targets.
- P2: FTS5 indexed cross-module search for large datasets, only after representative benchmarks.
- P2: Read/write separation, sync workers and optional PostgreSQL migration if contention justifies it.
- P2: Real offline editing with encryption, conflict resolution and resync states (current service worker caches **static assets only**).
- P2: Native OS push, widgets, and background sync.
- P2: Progressive image rendering, virtualized lists, smaller JS bundles and code splitting where profiling proves beneficial.
- P2: Full WCAG audit, screen reader testing, keyboard test matrix and reduced-motion coverage.
- P3: Horizontal scaling, rate limiting and resilient distributed job queue.

## Release prioritization

Next practical builds should focus on (1) full legacy ownership migration, (2) task trash/undo and consolidated work data, (3) true background calendar sync, (4) on-Pi performance instrumentation and deployment automation. Avoid implementing expensive AI or specialized professional systems before foundational data permissions and recovery are reliable.

## Safety and limitations

- There is no new subscription paywall.
- OAuth connections still require user-provided Google/Microsoft credentials and remain unverified against live external accounts here.
- The v3.4 regression suite verifies tested flows, not all possible external deployments or all legacy v2 database variants.
- Docker image publishing and Portainer redeploy must be performed in the user's environment.
- No support claimed for real offline data mutations or enterprise/regulated compliance.
