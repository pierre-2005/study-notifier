# MLO: 1,000 feature opportunities

Exactly 1,000 uniquely titled proposals across 40 areas. M/L/XL are relative effort triage, not implementation estimates. Candidates and shared foundations are explained in AUDIT_REPORT.md.

## Recommended shortlist

- **F0501 — SQLite full-text search indexing** (M): Search tasks and notes with ranked snippets without exposing inaccessible records.
- **F0027 — Task labels with nested taxonomy** (M): Apply multiple reusable labels and filter across permitted projects.
- **F0028 — Typed custom fields on tasks** (M): Define and validate a typed field and display it in task detail and table views.
- **F0029 — Saved cross-project task filters** (M): Save a compound task query and reopen equivalent results after signing in again.
- **F0040 — Task change activity timeline** (M): Show who changed a task and which values changed, with permission-filtered visibility.
- **F0041 — Task soft-delete recovery bin** (M): Restore an accidentally deleted task with its recoverable relationships.
- **F0240 — Note revision history with restore** (M): Compare two saved note versions and restore one without losing the current revision.
- **F0251 — Wiki-style note links** (M): Link notes by stable identity so renames do not break references.
- **F0252 — Automatic note backlink panel** (M): Show only incoming links from records the current viewer can access.
- **F0451 — Threaded task comments** (L): Create, reply to and resolve a task discussion with author and permission checks.
- **F0453 — User mentions with notification controls** (L): Notify an eligible mentioned member while respecting their notification settings.
- **F0825 — Per-member finance ledgers with legacy-owner migration** (L): Create a second private ledger without revealing or reassigning original-owner transactions.
- **F0748 — Per-member academic record migration** (M): Preserve original academic ownership while enabling new members to maintain separate records.
- **F0800 — Per-member career record migration** (M): Enable member-specific job records without copying another account application history.
- **F0276 — User-defined database schemas** (XL): Create a small custom record schema without arbitrary SQL or privilege escalation.
- **F0279 — Database relation field definitions** (XL): Link permitted records with referential integrity and explicit deletion behavior.
- **F0280 — Database relation aggregate rollups** (XL): Compute a reproducible aggregate over permitted related records.
- **F0326 — In-browser multipage PDF reader** (L): Open an authorized PDF at a specific page without a separate desktop application.
- **F0328 — PDF anchored threaded annotations** (L): Retain a page/text anchor and a discussion across document reopen operations.
- **F0337 — PDF extracted table review editor** (L): Review extracted cell values against their source page before accepting data.
- **F0526 — Visual trigger-action workflow builder** (L): Preview and test an event-triggered action with scoped permissions and a run record.
- **F0540 — Workflow test events and dry runs** (L): Show intended changes and confirm that a dry run creates no production mutations.
- **F0401 — Permission-scoped workspace Q&A** (L): Answer from authorized sources with citations and refuse inaccessible context.
- **F0951 — Scheduled encrypted backup orchestration** (L): Produce coordinated encrypted data/file backups with a visible freshness record.
- **F0952 — Automated restore rehearsal jobs** (L): Restore a disposable copy and verify records and attachment integrity without touching production.

## Capture

Current baseline: Global task capture and quick-add already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/static/capture.js#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0001 | Natural-language dates in task capture | Extension candidate | M | Scope during design |
| F0002 | Email-to-inbox addresses per user | Extension candidate | M | Scope during design |
| F0003 | Browser page clipping with source URL | Extension candidate | M | Scope during design |
| F0004 | Voice-to-task dictation | Extension candidate | M | Scope during design |
| F0005 | Screenshot-to-task capture | Extension candidate | M | Scope during design |
| F0006 | Inbox triage queue separate from tasks | Extension candidate | M | Scope during design |
| F0007 | Bulk pasted lines preview before creation | Extension candidate | M | Scope during design |
| F0008 | Capture routing rules by project | Extension candidate | M | Scope during design |
| F0009 | Duplicate capture detection | Extension candidate | M | Scope during design |
| F0010 | Inbox aging reminders | Extension candidate | M | Scope during design |
| F0011 | Mobile share-sheet destination picker | Extension candidate | M | Scope during design |
| F0012 | Bookmark-to-task conversion | Extension candidate | M | Scope during design |
| F0013 | Clipboard URL metadata preview | Extension candidate | M | Scope during design |
| F0014 | Offline capture outbox with retry | Extension candidate | M | Scope during design |
| F0015 | Capture attachment before choosing project | Extension candidate | M | Scope during design |
| F0016 | Inbox delegation to another member | Extension candidate | M | Scope during design |
| F0017 | Capture presets with parameter prompts | Extension candidate | M | Scope during design |
| F0018 | Capture from selected PDF text | Extension candidate | M | Scope during design |
| F0019 | Quick capture from calendar selection | Extension candidate | M | Scope during design |
| F0020 | Capture undo across bulk submissions | Extension candidate | M | Scope during design |
| F0021 | Forwarded email attachment preservation | Extension candidate | M | Scope during design |
| F0022 | Inbox merge of related captures | Extension candidate | M | Scope during design |
| F0023 | Inbox processing keyboard workflow | Extension candidate | M | Scope during design |
| F0024 | Capture provenance and originating device | Extension candidate | M | Scope during design |
| F0025 | Capture-to-note or task conversion | Extension candidate | M | Scope during design |

## Task planning

Current baseline: Tasks have statuses, priorities, dates, estimates, subtasks and dependencies.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0026 | Multiple task assignees with responsibility rules | Extension candidate | M | Scope during design |
| F0027 | Task labels with nested taxonomy | Extension candidate | M | Scope during design |
| F0028 | Typed custom fields on tasks | Extension candidate | M | Scope during design |
| F0029 | Saved cross-project task filters | Extension candidate | M | Scope during design |
| F0030 | Task start dates separate from due dates | Extension candidate | M | Scope during design |
| F0031 | Task deadline versus target-date distinction | Extension candidate | M | Scope during design |
| F0032 | Work-in-progress limits by status | Extension candidate | M | Scope during design |
| F0033 | Task watchers and subscriptions | Extension candidate | M | Scope during design |
| F0034 | Task checklist items independent of subtasks | Extension candidate | M | Scope during design |
| F0035 | Task effort points | Extension candidate | M | Scope during design |
| F0036 | Task confidence estimates | Extension candidate | M | Scope during design |
| F0037 | Task energy requirements | Extension candidate | M | Scope during design |
| F0038 | Task location contexts | Extension candidate | M | Scope during design |
| F0039 | Task completion approval gate | Extension candidate | M | Scope during design |
| F0040 | Task change activity timeline | Extension candidate | M | Scope during design |
| F0041 | Task soft-delete recovery bin | Extension candidate | M | Scope during design |
| F0042 | Bulk task field editing preview | Extension candidate | M | Scope during design |
| F0043 | Task splitting with effort allocation | Extension candidate | M | Scope during design |
| F0044 | Task merging with link redirects | Extension candidate | M | Scope during design |
| F0045 | Task duplicate detection by similarity | Extension candidate | M | Scope during design |
| F0046 | Task acceptance criteria fields | Extension candidate | M | Scope during design |
| F0047 | Delegation follow-up dates | Extension candidate | M | Scope during design |
| F0048 | Task aging indicators by workflow stage | Extension candidate | M | Scope during design |
| F0049 | Task snooze with automatic resurfacing | Extension candidate | M | Scope during design |
| F0050 | Task handoff acknowledgments | Extension candidate | M | Scope during design |

## Recurrence

Current baseline: Basic recurring tasks and successor protection already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/task_service.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0051 | Recurrence rule visual builder | Extension candidate | M | Scope during design |
| F0052 | Repeat on completion plus elapsed duration | Extension candidate | M | Scope during design |
| F0053 | Nth business-day task recurrence | Extension candidate | M | Scope during design |
| F0054 | Holiday-aware recurring task shifts | Extension candidate | M | Scope during design |
| F0055 | Recurrence occurrence exception editor | Extension candidate | M | Scope during design |
| F0056 | Edit only this and future task occurrences | Extension candidate | M | Scope during design |
| F0057 | Recurring task pause until date | Extension candidate | M | Scope during design |
| F0058 | Recurring task end after occurrence count | Extension candidate | M | Scope during design |
| F0059 | Recurring task seasonal windows | Extension candidate | M | Scope during design |
| F0060 | Recurring task rotating assignee schedule | Extension candidate | M | Scope during design |
| F0061 | Recurring task skip with reason | Extension candidate | M | Scope during design |
| F0062 | Recurring task catch-up policy | Extension candidate | M | Scope during design |
| F0063 | Recurring task carryover limit | Extension candidate | M | Scope during design |
| F0064 | Recurring subtask template inheritance | Extension candidate | M | Scope during design |
| F0065 | Recurring task preview calendar | Extension candidate | M | Scope during design |
| F0066 | Recurring task dependency regeneration policy | Extension candidate | M | Scope during design |
| F0067 | Recurring task per-occurrence attachments | Extension candidate | M | Scope during design |
| F0068 | Recurring task series analytics | Extension candidate | M | Scope during design |
| F0069 | Recurring task timezone-change preview | Extension candidate | M | Scope during design |
| F0070 | Last-working-day recurring deadlines | Extension candidate | M | Scope during design |
| F0071 | Alternating-week task recurrence | Extension candidate | M | Scope during design |
| F0072 | Recurring task missed-occurrence digest | Extension candidate | M | Scope during design |
| F0073 | Recurring task quota per rolling period | Extension candidate | M | Scope during design |
| F0074 | Recurring series archival without deleting history | Extension candidate | M | Scope during design |
| F0075 | Recurring task holiday calendar selection | Extension candidate | M | Scope during design |

## Projects

Current baseline: Projects support sharing, notes, files and milestone/risk records.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0076 | Cross-project portfolio dashboard | Extension candidate | M | Scope during design |
| F0077 | Project hierarchy and subprojects | Extension candidate | M | Scope during design |
| F0078 | Project baseline versus actual dates | Extension candidate | M | Scope during design |
| F0079 | Project health scoring rules | Extension candidate | M | Scope during design |
| F0080 | Project budget versus actual time | Extension candidate | M | Scope during design |
| F0081 | Project role-based responsibility matrix | Extension candidate | M | Scope during design |
| F0082 | Project resource capacity plans | Extension candidate | M | Scope during design |
| F0083 | Project decision approval workflow | Extension candidate | M | Scope during design |
| F0084 | Project risk probability-impact matrix | Extension candidate | M | Scope during design |
| F0085 | Project issue escalation policies | Extension candidate | M | Scope during design |
| F0086 | Project dependency contracts across projects | Extension candidate | M | Scope during design |
| F0087 | Project deliverable acceptance sign-off | Extension candidate | M | Scope during design |
| F0088 | Project kickoff checklist generator | Extension candidate | M | Scope during design |
| F0089 | Project closure and retrospective workflow | Extension candidate | M | Scope during design |
| F0090 | Project template parameter wizard | Extension candidate | M | Scope during design |
| F0091 | Project stage-gate transitions | Extension candidate | M | Scope during design |
| F0092 | Project stakeholder register | Extension candidate | M | Scope during design |
| F0093 | Project benefit-realization tracking | Extension candidate | M | Scope during design |
| F0094 | Project assumption change log | Extension candidate | M | Scope during design |
| F0095 | Project change-request register | Extension candidate | M | Scope during design |
| F0096 | Project status report snapshots | Extension candidate | M | Scope during design |
| F0097 | Project scope baseline history | Extension candidate | M | Scope during design |
| F0098 | Project archived read-only freeze | Extension candidate | M | Scope during design |
| F0099 | Project handover package export | Extension candidate | M | Scope during design |
| F0100 | Project scenario comparison | Extension candidate | M | Scope during design |

## Agile workflows

Current baseline: Boards have fixed status columns and real task ordering.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/workspace_api.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0101 | Configurable workflow states per project | New subsystem candidate | L | F0026, F0035 |
| F0102 | Sprint planning and backlog assignment | New subsystem candidate | L | F0026, F0035 |
| F0103 | Sprint capacity calculation | New subsystem candidate | L | F0026, F0035 |
| F0104 | Sprint carryover decision workflow | New subsystem candidate | L | F0026, F0035 |
| F0105 | Burndown chart from historical events | New subsystem candidate | L | F0026, F0035 |
| F0106 | Burnup chart with scope changes | New subsystem candidate | L | F0026, F0035 |
| F0107 | Cycle-time distribution chart | New subsystem candidate | L | F0026, F0035 |
| F0108 | Cumulative flow diagram | New subsystem candidate | L | F0026, F0035 |
| F0109 | Story-point estimation sessions | New subsystem candidate | L | F0026, F0035 |
| F0110 | Planning poker voting | New subsystem candidate | L | F0026, F0035 |
| F0111 | Sprint retrospective boards | New subsystem candidate | L | F0026, F0035 |
| F0112 | Release versions and fix-version fields | New subsystem candidate | L | F0026, F0035 |
| F0113 | Bug severity and reproduction templates | New subsystem candidate | L | F0026, F0035 |
| F0114 | Definition-of-ready validation | New subsystem candidate | L | F0026, F0035 |
| F0115 | Definition-of-done validation | New subsystem candidate | L | F0026, F0035 |
| F0116 | Board swimlanes by assignee | New subsystem candidate | L | F0026, F0035 |
| F0117 | Board column entry policies | New subsystem candidate | L | F0026, F0035 |
| F0118 | Backlog prioritization scorecards | New subsystem candidate | L | F0026, F0035 |
| F0119 | Explicit blocked reason taxonomy | New subsystem candidate | L | F0026, F0035 |
| F0120 | Release readiness checklist gates | New subsystem candidate | L | F0026, F0035 |
| F0121 | Epic grouping across task trees | New subsystem candidate | L | F0026, F0035 |
| F0122 | Service-class lanes for urgent work | New subsystem candidate | L | F0026, F0035 |
| F0123 | Team velocity trend with uncertainty | New subsystem candidate | L | F0026, F0035 |
| F0124 | Sprint scope-change audit | New subsystem candidate | L | F0026, F0035 |
| F0125 | Feature request voting portal | New subsystem candidate | L | F0026, F0035 |

## Task map

Current baseline: Expanded window, branches, focus, overview, search and arrange/undo already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/static/task-map.js#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0126 | Obstacle-aware wire routing | Extension candidate | M | Scope during design |
| F0127 | Manual connection waypoint editing | Extension candidate | M | Scope during design |
| F0128 | Snap-to-grid node placement | Extension candidate | M | Scope during design |
| F0129 | Alignment and distribution tools | Extension candidate | M | Scope during design |
| F0130 | Named map view bookmarks | Extension candidate | M | Scope during design |
| F0131 | Cross-project map portals | Extension candidate | M | Scope during design |
| F0132 | Mixed note and task map cards | Extension candidate | M | Scope during design |
| F0133 | Image and PDF canvas cards | Extension candidate | M | Scope during design |
| F0134 | Map groups with labeled boundaries | Extension candidate | M | Scope during design |
| F0135 | Draw-to-connect dependency creation | Extension candidate | M | Scope during design |
| F0136 | Dependency type labels on wires | Extension candidate | M | Scope during design |
| F0137 | Critical-path highlighting | Extension candidate | M | Scope during design |
| F0138 | Circular dependency explanation overlay | Extension candidate | M | Scope during design |
| F0139 | Time-axis map layout | Extension candidate | M | Scope during design |
| F0140 | Radial map layout | Extension candidate | M | Scope during design |
| F0141 | Map presentation slide paths | Extension candidate | M | Scope during design |
| F0142 | Map SVG export with text | Extension candidate | M | Scope during design |
| F0143 | Map PDF export with pagination | Extension candidate | M | Scope during design |
| F0144 | Collaborative map cursors | Extension candidate | M | Scope during design |
| F0145 | Independent layout undo history | Extension candidate | M | Scope during design |
| F0146 | Map layout revision comparison | Extension candidate | M | Scope during design |
| F0147 | Virtualized rendering beyond map limit | Extension candidate | M | Scope during design |
| F0148 | Map level-of-detail rendering | Extension candidate | M | Scope during design |
| F0149 | Map lasso selection and group move | Extension candidate | M | Scope during design |
| F0150 | Keyboard child-node creation shortcuts | Extension candidate | M | Scope during design |

## Calendar

Current baseline: Month/agenda, provider writes, ICS subscriptions and background sync already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/calendar_links.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0151 | Week time-grid view | Extension candidate | L | Scope during design |
| F0152 | Multi-day custom calendar ranges | Extension candidate | L | Scope during design |
| F0153 | Side-by-side team availability | Extension candidate | L | Scope during design |
| F0154 | Drag event edge to resize duration | Extension candidate | L | Scope during design |
| F0155 | Resource and room booking calendars | Extension candidate | L | Scope during design |
| F0156 | Calendar travel-time buffers | Extension candidate | L | Scope during design |
| F0157 | Per-event timezone comparison | Extension candidate | L | Scope during design |
| F0158 | Calendar conflict resolution inbox | Extension candidate | L | Scope during design |
| F0159 | Provider synchronization audit trail | Extension candidate | L | Scope during design |
| F0160 | Offline calendar change reconciliation | Extension candidate | L | Scope during design |
| F0161 | Calendar color rules by category | Extension candidate | L | Scope during design |
| F0162 | Birthday and anniversary calendars | Extension candidate | L | Scope during design |
| F0163 | Working-hours overlays | Extension candidate | L | Scope during design |
| F0164 | Holiday calendars by region | Extension candidate | L | Scope during design |
| F0165 | Event attendee response tracking | Extension candidate | L | Scope during design |
| F0166 | Calendar event attachment links | Extension candidate | L | Scope during design |
| F0167 | Multiple calendar overlay transparency | Extension candidate | L | Scope during design |
| F0168 | Calendar change notification rules | Extension candidate | L | Scope during design |
| F0169 | Provider rate-limit status dashboard | Extension candidate | L | Scope during design |
| F0170 | Calendar subscription health warnings | Extension candidate | L | Scope during design |
| F0171 | Calendar meeting cost estimates | Extension candidate | L | Scope during design |
| F0172 | Event duplicate detection across providers | Extension candidate | L | Scope during design |
| F0173 | Selected-occurrence series editing UI | Extension candidate | L | Scope during design |
| F0174 | Calendar day capacity meters | Extension candidate | L | Scope during design |
| F0175 | Calendar print layout with legible overflow | Extension candidate | L | Scope during design |

## Scheduling

Current baseline: Study blocks and calendar-linked planning provide a scheduling base.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/study_planner.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0176 | General task auto-scheduling engine | Extension candidate | L | Scope during design |
| F0177 | User-confirmed rescheduling proposals | Extension candidate | L | Scope during design |
| F0178 | Deadline feasibility warnings | Extension candidate | L | Scope during design |
| F0179 | Split tasks into schedulable work chunks | Extension candidate | L | Scope during design |
| F0180 | Scheduling by energy profile | Extension candidate | L | Scope during design |
| F0181 | Scheduling around travel constraints | Extension candidate | L | Scope during design |
| F0182 | Scheduling with task prerequisites | Extension candidate | L | Scope during design |
| F0183 | Scheduling with preferred work hours | Extension candidate | L | Scope during design |
| F0184 | Team resource leveling proposals | Extension candidate | L | Scope during design |
| F0185 | Personal booking links with availability | Extension candidate | L | Scope during design |
| F0186 | Round-robin meeting booking | Extension candidate | L | Scope during design |
| F0187 | Minimum-notice booking policies | Extension candidate | L | Scope during design |
| F0188 | Booking intake questionnaire | Extension candidate | L | Scope during design |
| F0189 | Scheduling protected deep-work windows | Extension candidate | L | Scope during design |
| F0190 | Scheduling reserve for unexpected work | Extension candidate | L | Scope during design |
| F0191 | Multi-timezone meeting suggestion ranking | Extension candidate | L | Scope during design |
| F0192 | Schedule scenario sandbox | Extension candidate | L | Scope during design |
| F0193 | Explainable scheduling decisions | Extension candidate | L | Scope during design |
| F0194 | Task interruption recovery rescheduling | Extension candidate | L | Scope during design |
| F0195 | Capacity-aware daily task commitments | Extension candidate | L | Scope during design |
| F0196 | Appointment waitlists | Extension candidate | L | Scope during design |
| F0197 | Booking cancellation and rescheduling links | Extension candidate | L | Scope during design |
| F0198 | Buffer-aware back-to-back meeting prevention | Extension candidate | L | Scope during design |
| F0199 | Shared family availability suggestions | Extension candidate | L | Scope during design |
| F0200 | Compare planned and actual scheduling | Extension candidate | L | Scope during design |

## Focus

Current baseline: Task-linked timers pause/resume/restart and log completed time.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/timers.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0201 | Pomodoro sequence configuration | Extension candidate | M | Scope during design |
| F0202 | Automatic long-break cadence | Extension candidate | M | Scope during design |
| F0203 | Focus session intention notes | Extension candidate | M | Scope during design |
| F0204 | Interruption reason capture | Extension candidate | M | Scope during design |
| F0205 | Focus session distraction tally | Extension candidate | M | Scope during design |
| F0206 | Focus audio environment library | Extension candidate | M | Scope during design |
| F0207 | Focus session desktop status indicator | Extension candidate | M | Scope during design |
| F0208 | Focus accountability partner sessions | Extension candidate | M | Scope during design |
| F0209 | Focus streak recovery policy | Extension candidate | M | Scope during design |
| F0210 | Focus time rounding rules | Extension candidate | M | Scope during design |
| F0211 | Manual correction of session intervals | Extension candidate | M | Scope during design |
| F0212 | Billable versus nonbillable focus time | Extension candidate | M | Scope during design |
| F0213 | Timesheet approval workflow | Extension candidate | M | Scope during design |
| F0214 | Time entry overlap detection | Extension candidate | M | Scope during design |
| F0215 | Idle-time detection with consent | Extension candidate | M | Scope during design |
| F0216 | Focus break stretching prompts | Extension candidate | M | Scope during design |
| F0217 | Focus session energy feedback | Extension candidate | M | Scope during design |
| F0218 | Planned versus actual task duration learning | Extension candidate | M | Scope during design |
| F0219 | Focus session calendar reconciliation | Extension candidate | M | Scope during design |
| F0220 | Focus session privacy modes | Extension candidate | M | Scope during design |
| F0221 | Task switching cost analytics | Extension candidate | M | Scope during design |
| F0222 | Focus session preflight checklist | Extension candidate | M | Scope during design |
| F0223 | Focus session resume after device restart | Extension candidate | M | Scope during design |
| F0224 | Weekly focus reflection prompts | Extension candidate | M | Scope during design |
| F0225 | Deep-work goal pacing | Extension candidate | M | Scope during design |

## Note editor

Current baseline: Markdown write/preview/split, explicit saves and conflict protection exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/static/notes.js#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0226 | Block-based note editing | Extension candidate | M | Scope during design |
| F0227 | Slash-command insertion menu | Extension candidate | M | Scope during design |
| F0228 | Note table editor | Extension candidate | M | Scope during design |
| F0229 | Code blocks with syntax highlighting | Extension candidate | M | Scope during design |
| F0230 | Mathematical equation rendering | Extension candidate | M | Scope during design |
| F0231 | Nested toggle blocks | Extension candidate | M | Scope during design |
| F0232 | Reusable synced content blocks | Extension candidate | M | Scope during design |
| F0233 | Drag block reordering | Extension candidate | M | Scope during design |
| F0234 | Note callout block styles | Extension candidate | M | Scope during design |
| F0235 | Embedded task views in notes | Extension candidate | M | Scope during design |
| F0236 | Inline task creation from selected text | Extension candidate | M | Scope during design |
| F0237 | Note footnotes and references | Extension candidate | M | Scope during design |
| F0238 | Note table of contents navigation | Extension candidate | M | Scope during design |
| F0239 | Note word-count and reading-time goals | Extension candidate | M | Scope during design |
| F0240 | Note revision history with restore | Extension candidate | M | Scope during design |
| F0241 | Rich paste cleanup preview | Extension candidate | M | Scope during design |
| F0242 | Note find-and-replace with preview | Extension candidate | M | Scope during design |
| F0243 | Note content linting for broken links | Extension candidate | M | Scope during design |
| F0244 | Audio blocks with playback timestamps | Extension candidate | M | Scope during design |
| F0245 | Note attachment inline previews | Extension candidate | M | Scope during design |
| F0246 | Drawing blocks inside notes | Extension candidate | M | Scope during design |
| F0247 | Side-by-side note comparison | Extension candidate | M | Scope during design |
| F0248 | Note heading deep links | Extension candidate | M | Scope during design |
| F0249 | Export notes to styled DOCX | Extension candidate | M | Scope during design |
| F0250 | Multi-note merge with source references | Extension candidate | M | Scope during design |

## Knowledge linking

Current baseline: Notes attach to projects; global linked knowledge is limited.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0251 | Wiki-style note links | New subsystem candidate | M | Scope during design |
| F0252 | Automatic note backlink panel | New subsystem candidate | M | F0251 |
| F0253 | Unlinked mention suggestions | New subsystem candidate | M | F0251 |
| F0254 | Global knowledge graph | New subsystem candidate | M | F0251 |
| F0255 | Typed relationships between records | New subsystem candidate | M | F0251 |
| F0256 | Knowledge graph relation filters | New subsystem candidate | M | F0251 |
| F0257 | Topic and concept pages | New subsystem candidate | M | F0251 |
| F0258 | Knowledge page ownership and verification | New subsystem candidate | M | F0251 |
| F0259 | Stale knowledge review schedules | New subsystem candidate | M | F0251 |
| F0260 | Knowledge page duplicate merge | New subsystem candidate | M | F0251 |
| F0261 | Alias names for knowledge entities | New subsystem candidate | M | F0251 |
| F0262 | Transclusion of note sections | New subsystem candidate | M | F0251 |
| F0263 | Knowledge graph orphan detection | New subsystem candidate | M | F0251 |
| F0264 | Knowledge graph community clusters | New subsystem candidate | M | F0251 |
| F0265 | Personal daily journal note automation | New subsystem candidate | M | F0251 |
| F0266 | Weekly journal aggregation | New subsystem candidate | M | F0251 |
| F0267 | Knowledge glossary extraction workflow | New subsystem candidate | M | F0251 |
| F0268 | Reference bibliography manager | New subsystem candidate | M | F0251 |
| F0269 | Citation keys across notes and files | New subsystem candidate | M | F0251 |
| F0270 | Reading notes linked to original sources | New subsystem candidate | M | F0251 |
| F0271 | Knowledge map learning trails | New subsystem candidate | M | F0251 |
| F0272 | Knowledge page quality checklists | New subsystem candidate | M | F0251 |
| F0273 | Knowledge collection publishing approval | New subsystem candidate | M | F0251 |
| F0274 | Broken-reference repair assistant | New subsystem candidate | M | F0251 |
| F0275 | Knowledge graph export to open formats | New subsystem candidate | M | F0251 |

## Flexible databases

Current baseline: Spaces offer fixed blank/checklist/grocery models rather than arbitrary databases.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/workspace.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0276 | User-defined database schemas | New subsystem candidate | XL | F0028 |
| F0277 | Database text and numeric field types | New subsystem candidate | XL | F0028 |
| F0278 | Database select and multiselect options | New subsystem candidate | XL | F0028 |
| F0279 | Database relation field definitions | New subsystem candidate | XL | F0028 |
| F0280 | Database relation aggregate rollups | New subsystem candidate | XL | F0028 |
| F0281 | Database formula expressions | New subsystem candidate | XL | F0028 |
| F0282 | Database field-level validation rules | New subsystem candidate | XL | F0028 |
| F0283 | Database saved table views | New subsystem candidate | XL | F0028 |
| F0284 | Database gallery card views | New subsystem candidate | XL | F0028 |
| F0285 | Database pivot summary views | New subsystem candidate | XL | F0028 |
| F0286 | Database grouped board views | New subsystem candidate | XL | F0028 |
| F0287 | Database conditional row coloring | New subsystem candidate | XL | F0028 |
| F0288 | Database unique-value constraints | New subsystem candidate | XL | F0028 |
| F0289 | Database computed lookup fields | New subsystem candidate | XL | F0028 |
| F0290 | Database reusable schema templates | New subsystem candidate | XL | F0028 |
| F0291 | Database bulk import mapping preview | New subsystem candidate | XL | F0028 |
| F0292 | Database schema version migration preview | New subsystem candidate | XL | F0028 |
| F0293 | Database field permission policies | New subsystem candidate | XL | F0028 |
| F0294 | Database row detail page layouts | New subsystem candidate | XL | F0028 |
| F0295 | Database field dependency diagnostics | New subsystem candidate | XL | F0028 |
| F0296 | Database default value expressions | New subsystem candidate | XL | F0028 |
| F0297 | Database attachment properties | New subsystem candidate | XL | F0028 |
| F0298 | Database view embedding across spaces | New subsystem candidate | XL | F0028 |
| F0299 | Database aggregate chart views | New subsystem candidate | XL | F0028 |
| F0300 | Database schema export and portability | New subsystem candidate | XL | F0028 |

## Forms

Current baseline: Imports and fixed record forms exist; a general intake builder is absent.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/life_import.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0301 | Visual intake form builder | New subsystem candidate | M | F0276 |
| F0302 | Conditional form field visibility | New subsystem candidate | M | F0276 |
| F0303 | Multi-step form progress saving | New subsystem candidate | M | F0276 |
| F0304 | Public form submission endpoints | New subsystem candidate | M | F0276 |
| F0305 | Authenticated internal intake forms | New subsystem candidate | M | F0276 |
| F0306 | Form attachment upload questions | New subsystem candidate | M | F0276 |
| F0307 | Form computed score fields | New subsystem candidate | M | F0276 |
| F0308 | Form response approval queue | New subsystem candidate | M | F0276 |
| F0309 | Form spam protection controls | New subsystem candidate | M | F0276 |
| F0310 | Form submission rate limits | New subsystem candidate | M | F0276 |
| F0311 | Form duplicate response policies | New subsystem candidate | M | F0276 |
| F0312 | Form response edit links | New subsystem candidate | M | F0276 |
| F0313 | Form scheduled opening and closing | New subsystem candidate | M | F0276 |
| F0314 | Form per-choice branching paths | New subsystem candidate | M | F0276 |
| F0315 | Form multilingual question variants | New subsystem candidate | M | F0276 |
| F0316 | Form accessible error summary navigation | New subsystem candidate | M | F0276 |
| F0317 | Form response export with provenance | New subsystem candidate | M | F0276 |
| F0318 | Form webhook delivery actions | New subsystem candidate | M | F0276 |
| F0319 | Form respondent confirmation templates | New subsystem candidate | M | F0276 |
| F0320 | Form anonymous response safeguards | New subsystem candidate | M | F0276 |
| F0321 | Form capacity and quota limits | New subsystem candidate | M | F0276 |
| F0322 | Form consent and retention choices | New subsystem candidate | M | F0276 |
| F0323 | Form conversion into linked task records | New subsystem candidate | M | F0276 |
| F0324 | Form reusable field libraries | New subsystem candidate | M | F0276 |
| F0325 | Form completion analytics by step | New subsystem candidate | M | F0276 |

## Documents and PDFs

Current baseline: Bounded extraction/OCR supports course and statement import, not a full document workspace.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/document_process.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0326 | In-browser multipage PDF reader | New subsystem candidate | L | Scope during design |
| F0327 | PDF text highlighting with colors | New subsystem candidate | L | Scope during design |
| F0328 | PDF anchored threaded annotations | New subsystem candidate | L | Scope during design |
| F0329 | PDF page bookmarks | New subsystem candidate | L | Scope during design |
| F0330 | PDF side-by-side version comparison | New subsystem candidate | L | Scope during design |
| F0331 | PDF redaction with verified removal | New subsystem candidate | XL | Scope during design |
| F0332 | PDF page reordering workspace | New subsystem candidate | L | Scope during design |
| F0333 | PDF document splitting and combining | New subsystem candidate | L | Scope during design |
| F0334 | PDF fillable field completion | New subsystem candidate | L | Scope during design |
| F0335 | PDF signature request workflow | New subsystem candidate | XL | Scope during design |
| F0336 | PDF clause library with source anchors | New subsystem candidate | L | Scope during design |
| F0337 | PDF extracted table review editor | New subsystem candidate | L | Scope during design |
| F0338 | PDF annotation export | New subsystem candidate | L | Scope during design |
| F0339 | PDF OCR confidence overlays | New subsystem candidate | L | Scope during design |
| F0340 | PDF searchable text-layer generation | New subsystem candidate | L | Scope during design |
| F0341 | PDF page rotation correction | New subsystem candidate | L | Scope during design |
| F0342 | Document review assignment queue | New subsystem candidate | L | Scope during design |
| F0343 | Document approval status stamps | New subsystem candidate | L | Scope during design |
| F0344 | Document version supersession links | New subsystem candidate | L | Scope during design |
| F0345 | Document citation deep links to pages | New subsystem candidate | L | Scope during design |
| F0346 | Document text-to-task selection actions | New subsystem candidate | L | Scope during design |
| F0347 | Office document preview conversion | New subsystem candidate | L | Scope during design |
| F0348 | Document structured comparison summaries | New subsystem candidate | L | Scope during design |
| F0349 | Document accessibility remediation checklist | New subsystem candidate | L | Scope during design |
| F0350 | Document reading progress across devices | New subsystem candidate | L | Scope during design |

## Files

Current baseline: Permission-checked upload/download/delete and record attachments exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/life_files.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0351 | Folder hierarchy for project files | Extension candidate | M | Scope during design |
| F0352 | File version history with restore | Extension candidate | M | Scope during design |
| F0353 | Resumable large-file uploads | Extension candidate | M | Scope during design |
| F0354 | Content hash duplicate detection | Extension candidate | M | Scope during design |
| F0355 | File preview thumbnails | Extension candidate | M | Scope during design |
| F0356 | Attachment metadata extraction | Extension candidate | M | Scope during design |
| F0357 | Attachment virus-scan quarantine | Extension candidate | M | Scope during design |
| F0358 | Attachment retention policies | Extension candidate | M | Scope during design |
| F0359 | File ownership transfer workflow | Extension candidate | M | Scope during design |
| F0360 | Temporary secure download grants | Extension candidate | M | Scope during design |
| F0361 | File upload request links | Extension candidate | M | Scope during design |
| F0362 | File collections across projects | Extension candidate | M | Scope during design |
| F0363 | File tagging taxonomy | Extension candidate | M | Scope during design |
| F0364 | File storage quota dashboards | Extension candidate | M | Scope during design |
| F0365 | File batch move with permission checks | Extension candidate | M | Scope during design |
| F0366 | File broken-reference detection | Extension candidate | M | Scope during design |
| F0367 | Attachment missing-file recovery queue | Extension candidate | M | Scope during design |
| F0368 | Attachment sidecar descriptions | Extension candidate | M | Scope during design |
| F0369 | File full-text content indexing | Extension candidate | M | Scope during design |
| F0370 | Media duration and dimensions indexing | Extension candidate | M | Scope during design |
| F0371 | File access activity reports | Extension candidate | M | Scope during design |
| F0372 | Bulk attachment export manifest | Extension candidate | M | Scope during design |
| F0373 | File lifecycle archiving tiers | Extension candidate | M | Scope during design |
| F0374 | Content-addressed storage migration | Extension candidate | M | Scope during design |
| F0375 | Encrypted attachment storage envelopes | Extension candidate | M | Scope during design |

## AI writing

Current baseline: Optional course-outline AI has per-upload consent; broad writing assistance is not established.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/outline_ai.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0376 | Selected-text rewrite suggestions | New subsystem candidate | M | Scope during design |
| F0377 | Writing tone transformation previews | New subsystem candidate | M | Scope during design |
| F0378 | Note summary drafts with acceptance controls | New subsystem candidate | M | Scope during design |
| F0379 | Meeting agenda drafting from tasks | New subsystem candidate | M | Scope during design |
| F0380 | Project update drafting from activity | New subsystem candidate | M | Scope during design |
| F0381 | Task description clarification suggestions | New subsystem candidate | M | Scope during design |
| F0382 | Acceptance criteria drafting assistant | New subsystem candidate | M | Scope during design |
| F0383 | Email reply drafts linked to context | New subsystem candidate | M | Scope during design |
| F0384 | Outline generation for long notes | New subsystem candidate | M | Scope during design |
| F0385 | Translate selected content with preview | New subsystem candidate | M | Scope during design |
| F0386 | Writing terminology consistency checks | New subsystem candidate | M | Scope during design |
| F0387 | Document title suggestion ranking | New subsystem candidate | M | Scope during design |
| F0388 | Action item extraction review queue | New subsystem candidate | M | Scope during design |
| F0389 | Decision extraction with quoted evidence | New subsystem candidate | M | Scope during design |
| F0390 | Writing factual claim citation prompts | New subsystem candidate | M | Scope during design |
| F0391 | AI text change diff before acceptance | New subsystem candidate | M | Scope during design |
| F0392 | Reusable writing prompt templates | New subsystem candidate | M | Scope during design |
| F0393 | Writing model provider selection | New subsystem candidate | M | Scope during design |
| F0394 | Per-document AI exclusion control | New subsystem candidate | M | Scope during design |
| F0395 | AI writing cost preview | New subsystem candidate | M | Scope during design |
| F0396 | AI-generated content provenance labels | New subsystem candidate | M | Scope during design |
| F0397 | Task-to-status-report narrative drafting | New subsystem candidate | M | Scope during design |
| F0398 | Study explanation drafting from selected notes | New subsystem candidate | M | Scope during design |
| F0399 | Draft shortening to explicit word limits | New subsystem candidate | M | Scope during design |
| F0400 | Personal writing style guide settings | New subsystem candidate | M | Scope during design |

## AI retrieval

Current baseline: Search and optional outline AI exist; permission-scoped cited workspace Q&A is not established.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/templates/life_search.html#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0401 | Permission-scoped workspace Q&A | New subsystem candidate | L | F0501, F0914 |
| F0402 | Paragraph citations in AI answers | New subsystem candidate | L | F0501, F0914 |
| F0403 | Document page citations in AI answers | New subsystem candidate | L | F0501, F0914 |
| F0404 | Retrieval scope selector by project | New subsystem candidate | L | F0501, F0914 |
| F0405 | Hybrid keyword and semantic search | New subsystem candidate | XL | F0501, F0914 |
| F0406 | Answer freshness indicators | New subsystem candidate | L | F0501, F0914 |
| F0407 | Answer uncertainty and abstention behavior | New subsystem candidate | L | F0501, F0914 |
| F0408 | Conversation follow-up source pinning | New subsystem candidate | L | F0501, F0914 |
| F0409 | Private versus shared AI conversation modes | New subsystem candidate | L | F0501, F0914 |
| F0410 | Saved research threads | New subsystem candidate | L | F0501, F0914 |
| F0411 | Source conflict comparison views | New subsystem candidate | L | F0501, F0914 |
| F0412 | AI answer feedback with evidence | New subsystem candidate | L | F0501, F0914 |
| F0413 | Retrieval index deletion propagation | New subsystem candidate | L | F0501, F0914 |
| F0414 | Retrieval index reprocessing queue | New subsystem candidate | L | F0501, F0914 |
| F0415 | Embedding provider portability | New subsystem candidate | L | F0501, F0914 |
| F0416 | On-device embedding option | New subsystem candidate | L | F0501, F0914 |
| F0417 | Document chunk inspection tools | New subsystem candidate | L | F0501, F0914 |
| F0418 | Retrieval quality evaluation sets | New subsystem candidate | L | F0501, F0914 |
| F0419 | Answer permission-leak regression suite | New subsystem candidate | L | F0501, F0914 |
| F0420 | Prompt injection isolation for documents | New subsystem candidate | L | F0501, F0914 |
| F0421 | Quoted-source context expansion | New subsystem candidate | L | F0501, F0914 |
| F0422 | Workspace question suggestion prompts | New subsystem candidate | L | F0501, F0914 |
| F0423 | Knowledge gap detection from failed queries | New subsystem candidate | L | F0501, F0914 |
| F0424 | Multi-document evidence comparison | New subsystem candidate | L | F0501, F0914 |
| F0425 | User-controlled AI context budgets | New subsystem candidate | L | F0501, F0914 |

## AI agents

Current baseline: No general permission-scoped agent execution platform was established.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/outline_ai.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0426 | Agent tool permission scopes | New subsystem candidate | XL | F0427 |
| F0427 | Agent plan preview before execution | New subsystem candidate | XL | F0426 |
| F0428 | Agent approval steps for external writes | New subsystem candidate | XL | F0426, F0427 |
| F0429 | Agent read-only research mode | New subsystem candidate | XL | F0426, F0427 |
| F0430 | Agent dry-run simulation | New subsystem candidate | XL | F0426, F0427 |
| F0431 | Agent execution activity journal | New subsystem candidate | XL | F0426, F0427 |
| F0432 | Agent cancellation controls | New subsystem candidate | XL | F0426, F0427 |
| F0433 | Agent checkpoint and resume | New subsystem candidate | XL | F0426, F0427 |
| F0434 | Agent per-run spending limits | New subsystem candidate | XL | F0426, F0427 |
| F0435 | Agent scheduled job definitions | New subsystem candidate | XL | F0426, F0427 |
| F0436 | Agent sandboxed tool execution | New subsystem candidate | XL | F0426, F0427 |
| F0437 | Agent secrets access mediation | New subsystem candidate | XL | F0426, F0427 |
| F0438 | Agent prompt version management | New subsystem candidate | XL | F0426, F0427 |
| F0439 | Agent evaluations against saved scenarios | New subsystem candidate | XL | F0426, F0427 |
| F0440 | Agent untrusted-content boundary labels | New subsystem candidate | XL | F0426, F0427 |
| F0441 | Agent human handoff queue | New subsystem candidate | XL | F0426, F0427 |
| F0442 | Agent task decomposition proposals | New subsystem candidate | XL | F0426, F0427 |
| F0443 | Agent duplicate action prevention | New subsystem candidate | XL | F0426, F0427 |
| F0444 | Agent failed-action retry policies | New subsystem candidate | XL | F0426, F0427 |
| F0445 | Agent memory review and deletion | New subsystem candidate | XL | F0426, F0427 |
| F0446 | Agent workspace policy enforcement | New subsystem candidate | XL | F0426, F0427 |
| F0447 | Agent output artifact comparison | New subsystem candidate | XL | F0426, F0427 |
| F0448 | Agent rollback plans for reversible writes | New subsystem candidate | XL | F0426, F0427 |
| F0449 | Agent run sharing with redacted context | New subsystem candidate | XL | F0426, F0427 |
| F0450 | Agent service account identities | New subsystem candidate | XL | F0426, F0427 |

## Collaboration

Current baseline: Project/space owner-editor-viewer sharing and stale-write checks exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0451 | Threaded task comments | Extension candidate | L | F0914 |
| F0452 | Inline note comments | Extension candidate | L | F0914 |
| F0453 | User mentions with notification controls | Extension candidate | L | F0914 |
| F0454 | Collaborative presence indicators | Extension candidate | L | F0914 |
| F0455 | Concurrent note cursor sharing | Extension candidate | L | F0914 |
| F0456 | Real-time collaborative block editing | Extension candidate | XL | F0914 |
| F0457 | Comment resolution workflow | Extension candidate | L | F0914 |
| F0458 | Suggested edits with accept/reject | Extension candidate | L | F0914 |
| F0459 | Team membership groups | Extension candidate | L | F0914 |
| F0460 | Inherited project team permissions | Extension candidate | L | F0914 |
| F0461 | Guest collaborator expiry dates | Extension candidate | L | F0914 |
| F0462 | Record-specific sharing overrides | Extension candidate | L | F0914 |
| F0463 | Shared activity feed with filters | Extension candidate | L | F0914 |
| F0464 | Reviewer assignment and due dates | Extension candidate | L | F0914 |
| F0465 | Approval requests with sign-off history | Extension candidate | L | F0914 |
| F0466 | Document ownership handover | Extension candidate | L | F0914 |
| F0467 | Cross-team dependency handshakes | Extension candidate | L | F0914 |
| F0468 | Task edit lock with expiry | Extension candidate | L | F0914 |
| F0469 | Collaborative saved-view sharing | Extension candidate | L | F0914 |
| F0470 | Comment attachment uploads | Extension candidate | L | F0914 |
| F0471 | Comment reactions | Extension candidate | L | F0914 |
| F0472 | Comment permalink navigation | Extension candidate | L | F0914 |
| F0473 | Private reviewer notes | Extension candidate | L | F0914 |
| F0474 | Team working agreement pages | Extension candidate | L | F0914 |
| F0475 | External collaborator onboarding checklists | Extension candidate | L | F0914 |

## Communication

Current baseline: Record reminders are present; integrated chat/email/meeting tools are not established.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/note_reminders.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0476 | Project discussion channels | New subsystem candidate | XL | F0453 |
| F0477 | Direct member messaging | New subsystem candidate | XL | F0453 |
| F0478 | Channel threads linked to tasks | New subsystem candidate | XL | F0453 |
| F0479 | Unified email conversation inbox | New subsystem candidate | XL | F0453 |
| F0480 | Email thread linking to projects | New subsystem candidate | XL | F0453 |
| F0481 | Mailbox account connector management | New subsystem candidate | XL | F0453 |
| F0482 | Message-to-task conversion with source | New subsystem candidate | XL | F0453 |
| F0483 | Scheduled message sending | New subsystem candidate | XL | F0453 |
| F0484 | Message reminder and resurfacing | New subsystem candidate | XL | F0453 |
| F0485 | Meeting agenda collaboration | New subsystem candidate | XL | F0453 |
| F0486 | Meeting action-item confirmation workflow | New subsystem candidate | XL | F0453 |
| F0487 | Consented meeting audio recording | New subsystem candidate | XL | F0453 |
| F0488 | Meeting transcript speaker corrections | New subsystem candidate | XL | F0453 |
| F0489 | Transcript timestamp deep links | New subsystem candidate | XL | F0453 |
| F0490 | Meeting decisions register linkage | New subsystem candidate | XL | F0453 |
| F0491 | Meeting follow-up draft review | New subsystem candidate | XL | F0453 |
| F0492 | Call recording retention policies | New subsystem candidate | XL | F0453 |
| F0493 | Meeting participant consent records | New subsystem candidate | XL | F0453 |
| F0494 | Meeting transcript search | New subsystem candidate | XL | F0453 |
| F0495 | Channel unread catch-up summaries | New subsystem candidate | XL | F0453 |
| F0496 | Notification-free announcement posts | New subsystem candidate | XL | F0453 |
| F0497 | Message delivery failure dashboard | New subsystem candidate | XL | F0453 |
| F0498 | Communication channel membership policies | New subsystem candidate | XL | F0453 |
| F0499 | Contact relationship timeline | New subsystem candidate | XL | F0453 |
| F0500 | Lightweight CRM opportunity pipeline | New subsystem candidate | XL | F0453 |

## Search

Current baseline: A basic authenticated cross-record search page already exists.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0501 | SQLite full-text search indexing | Extension candidate | M | Scope during design |
| F0502 | Typo-tolerant search suggestions | Extension candidate | M | Scope during design |
| F0503 | Faceted search by record type | Extension candidate | M | Scope during design |
| F0504 | Saved reusable search queries | Extension candidate | M | Scope during design |
| F0505 | Search query language with operators | Extension candidate | M | Scope during design |
| F0506 | Search result snippets with highlights | Extension candidate | M | Scope during design |
| F0507 | Search across attachment contents | Extension candidate | M | Scope during design |
| F0508 | Search by author and modifier | Extension candidate | M | Scope during design |
| F0509 | Search by date interval presets | Extension candidate | M | Scope during design |
| F0510 | Search result relevance tuning | Extension candidate | M | Scope during design |
| F0511 | Search autocomplete for entities | Extension candidate | M | Scope during design |
| F0512 | Search suggestions from recent work | Extension candidate | M | Scope during design |
| F0513 | Search scope permission explanations | Extension candidate | M | Scope during design |
| F0514 | Search indexing health dashboard | Extension candidate | M | Scope during design |
| F0515 | Search result grouping by project | Extension candidate | M | Scope during design |
| F0516 | Search result keyboard preview pane | Extension candidate | M | Scope during design |
| F0517 | Search within current note | Extension candidate | M | Scope during design |
| F0518 | Search within current task subtree | Extension candidate | M | Scope during design |
| F0519 | Search across archived records explicitly | Extension candidate | M | Scope during design |
| F0520 | Search exclusion rules for private folders | Extension candidate | M | Scope during design |
| F0521 | Search result bulk action selection | Extension candidate | M | Scope during design |
| F0522 | Search result export snapshots | Extension candidate | M | Scope during design |
| F0523 | Search synonym dictionaries | Extension candidate | M | Scope during design |
| F0524 | Search numeric and money ranges | Extension candidate | M | Scope during design |
| F0525 | Search latency and zero-result analytics | Extension candidate | M | Scope during design |

## Workflow automation

Current baseline: Scheduled reminders, mail retries and calendar sync exist as dedicated services.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/scheduler.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0526 | Visual trigger-action workflow builder | New subsystem candidate | L | F0914 |
| F0527 | Task status change triggers | New subsystem candidate | L | F0914 |
| F0528 | New record creation triggers | New subsystem candidate | L | F0914 |
| F0529 | Custom field change triggers | New subsystem candidate | L | F0914 |
| F0530 | Scheduled business-day triggers | New subsystem candidate | L | F0914 |
| F0531 | Incoming webhook workflow triggers | New subsystem candidate | L | F0914 |
| F0532 | Condition groups with AND and OR | New subsystem candidate | L | F0914 |
| F0533 | Workflow branch and switch actions | New subsystem candidate | L | F0914 |
| F0534 | Workflow delay-until conditions | New subsystem candidate | L | F0914 |
| F0535 | Workflow approval wait steps | New subsystem candidate | L | F0914 |
| F0536 | Workflow task creation actions | New subsystem candidate | L | F0914 |
| F0537 | Workflow record update actions | New subsystem candidate | L | F0914 |
| F0538 | Workflow notification delivery actions | New subsystem candidate | L | F0914 |
| F0539 | Workflow external HTTP request actions | New subsystem candidate | L | F0914 |
| F0540 | Workflow test events and dry runs | New subsystem candidate | L | F0914 |
| F0541 | Workflow run history with inputs | New subsystem candidate | L | F0914 |
| F0542 | Workflow failed-run recovery queue | New subsystem candidate | L | F0914 |
| F0543 | Workflow loop detection and limits | New subsystem candidate | L | F0914 |
| F0544 | Workflow idempotency keys | New subsystem candidate | L | F0914 |
| F0545 | Workflow credential scope checks | New subsystem candidate | L | F0914 |
| F0546 | Workflow definition version history | New subsystem candidate | L | F0914 |
| F0547 | Workflow reusable action templates | New subsystem candidate | L | F0914 |
| F0548 | Workflow per-user execution quotas | New subsystem candidate | L | F0914 |
| F0549 | Workflow dependency impact previews | New subsystem candidate | L | F0914 |
| F0550 | Workflow pause and maintenance windows | New subsystem candidate | L | F0914 |

## Integrations

Current baseline: Google/Microsoft calendars, ICS and ntfy are integrated; other connectors need separate work.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/calendar_links.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0551 | Notion import with block mapping | Extension candidate | L | F0575 |
| F0552 | Notion database synchronization connector | Extension candidate | L | F0575 |
| F0553 | Macro document migration importer | Extension candidate | L | F0575 |
| F0554 | Obsidian vault import with backlinks | Extension candidate | L | F0575 |
| F0555 | Todoist task migration connector | Extension candidate | L | F0575 |
| F0556 | ClickUp project migration connector | Extension candidate | L | F0575 |
| F0557 | Linear issue synchronization connector | Extension candidate | L | F0575 |
| F0558 | GitHub issue and PR linking | Extension candidate | L | F0575 |
| F0559 | GitLab issue and merge-request linking | Extension candidate | L | F0575 |
| F0560 | Slack approved notification connector | Extension candidate | L | F0575 |
| F0561 | Microsoft Teams notification connector | Extension candidate | L | F0575 |
| F0562 | Gmail selected-thread import | Extension candidate | L | F0575 |
| F0563 | Outlook selected-thread import | Extension candidate | L | F0575 |
| F0564 | Google Drive file reference connector | Extension candidate | L | F0575 |
| F0565 | OneDrive file reference connector | Extension candidate | L | F0575 |
| F0566 | Dropbox file reference connector | Extension candidate | L | F0575 |
| F0567 | Zotero reference import connector | Extension candidate | L | F0575 |
| F0568 | CalDAV writable calendar connector | Extension candidate | L | F0575 |
| F0569 | CardDAV contact synchronization | Extension candidate | L | F0575 |
| F0570 | WebDAV file synchronization | Extension candidate | L | F0575 |
| F0571 | Home Assistant task event connector | Extension candidate | L | F0575 |
| F0572 | LMS assignment import connector | Extension candidate | L | F0575 |
| F0573 | Readwise highlight import connector | Extension candidate | L | F0575 |
| F0574 | Integration connection health dashboard | Extension candidate | L | F0575 |
| F0575 | Integration permission consent ledger | Extension candidate | L | Scope during design |

## Mobile and offline

Current baseline: Responsive PWA and static-only offline caching exist; private offline editing is absent.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/static/sw.js#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0576 | Encrypted offline notes vault | Extension candidate | XL | F0904 |
| F0577 | Offline task mutation queue | Extension candidate | XL | F0904 |
| F0578 | Offline attachment download selection | Extension candidate | XL | F0904 |
| F0579 | Conflict resolution after offline edits | Extension candidate | XL | F0904 |
| F0580 | Per-device offline data wipe | Extension candidate | XL | F0904 |
| F0581 | PWA background sync for queued writes | Extension candidate | XL | F0904 |
| F0582 | Offline search index scoped to device | Extension candidate | XL | F0904 |
| F0583 | Push notification deep-link navigation | Extension candidate | XL | F0904 |
| F0584 | Mobile home-screen quick actions | Extension candidate | XL | F0904 |
| F0585 | Mobile share-extension capture | Extension candidate | XL | F0904 |
| F0586 | Mobile handwriting note input | Extension candidate | XL | F0904 |
| F0587 | Mobile document camera scanning | Extension candidate | XL | F0904 |
| F0588 | Mobile biometric unlock for local cache | Extension candidate | XL | F0904 |
| F0589 | Offline storage usage controls | Extension candidate | XL | F0904 |
| F0590 | Selective project offline availability | Extension candidate | XL | F0904 |
| F0591 | Low-bandwidth attachment modes | Extension candidate | XL | F0904 |
| F0592 | Mobile gesture customization | Extension candidate | XL | F0904 |
| F0593 | Mobile tablet split-view layout | Extension candidate | XL | F0904 |
| F0594 | Mobile keyboard-aware editor layout | Extension candidate | XL | F0904 |
| F0595 | Offline synchronization progress UI | Extension candidate | XL | F0904 |
| F0596 | Native app packaging release workflow | Extension candidate | XL | F0904 |
| F0597 | Device-specific notification schedules | Extension candidate | XL | F0904 |
| F0598 | PWA update readiness and draft protection | Extension candidate | XL | F0904 |
| F0599 | Mobile quick action widgets | Extension candidate | XL | F0904 |
| F0600 | Offline export recovery package | Extension candidate | XL | F0904 |

## Accessibility

Current baseline: Keyboard focus, responsive controls and automated accessibility checks already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/static/app.css#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0601 | User-adjustable global text scaling | Extension candidate | M | Scope during design |
| F0602 | Dyslexia-friendly font option | Extension candidate | M | Scope during design |
| F0603 | Reduced-distraction reading layout | Extension candidate | M | Scope during design |
| F0604 | High-contrast theme independent of palette | Extension candidate | M | Scope during design |
| F0605 | Color-blind status pattern options | Extension candidate | M | Scope during design |
| F0606 | Screen-reader task map outline alternative | Extension candidate | M | Scope during design |
| F0607 | Accessible drag action menus | Extension candidate | M | Scope during design |
| F0608 | Voice control labels for all actions | Extension candidate | M | Scope during design |
| F0609 | Per-user keyboard shortcut remapping | Extension candidate | M | Scope during design |
| F0610 | Shortcut conflict detection | Extension candidate | M | Scope during design |
| F0611 | Screen-reader live-update verbosity settings | Extension candidate | M | Scope during design |
| F0612 | Accessible bulk-operation progress reporting | Extension candidate | M | Scope during design |
| F0613 | Accessible long-form error summaries | Extension candidate | M | Scope during design |
| F0614 | Focus restoration regression matrix | Extension candidate | M | Scope during design |
| F0615 | Touch target size preference | Extension candidate | M | Scope during design |
| F0616 | Motor-accessible dwell action mode | Extension candidate | M | Scope during design |
| F0617 | Sticky-key support for canvas commands | Extension candidate | M | Scope during design |
| F0618 | Accessible data table header associations | Extension candidate | M | Scope during design |
| F0619 | Accessible chart text alternatives | Extension candidate | M | Scope during design |
| F0620 | Caption support for uploaded videos | Extension candidate | M | Scope during design |
| F0621 | Transcript support for audio attachments | Extension candidate | M | Scope during design |
| F0622 | Language-aware screen-reader markup | Extension candidate | M | Scope during design |
| F0623 | Bidirectional text layout support | Extension candidate | M | Scope during design |
| F0624 | Plain-language interface labels mode | Extension candidate | M | Scope during design |
| F0625 | Automated accessibility checks for custom schemas | Extension candidate | M | Scope during design |

## Personalization

Current baseline: Themes, palettes, sidebar customization, density and movable home widgets exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/personalize.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0626 | Named workspace layout presets | Extension candidate | M | Scope during design |
| F0627 | Per-project dashboard layouts | Extension candidate | M | Scope during design |
| F0628 | Custom dashboard widget builder | Extension candidate | M | Scope during design |
| F0629 | Conditional widget visibility rules | Extension candidate | M | Scope during design |
| F0630 | User-selectable startup destination | Extension candidate | M | Scope during design |
| F0631 | Role-oriented navigation presets | Extension candidate | M | Scope during design |
| F0632 | Custom icon upload and selection | Extension candidate | M | Scope during design |
| F0633 | Custom terminology for task statuses | Extension candidate | M | Scope during design |
| F0634 | User-defined date display formats | Extension candidate | M | Scope during design |
| F0635 | Custom fiscal calendar definitions | Extension candidate | M | Scope during design |
| F0636 | Customizable empty-state guidance | Extension candidate | M | Scope during design |
| F0637 | Personal notification sound selection | Extension candidate | M | Scope during design |
| F0638 | Personal accent color validation | Extension candidate | M | Scope during design |
| F0639 | Per-view column visibility presets | Extension candidate | M | Scope during design |
| F0640 | Per-view card field layouts | Extension candidate | M | Scope during design |
| F0641 | Cross-device layout preference sync | Extension candidate | M | Scope during design |
| F0642 | Workspace branding settings | Extension candidate | M | Scope during design |
| F0643 | Navigation favorite folders | Extension candidate | M | Scope during design |
| F0644 | Pinned record collections | Extension candidate | M | Scope during design |
| F0645 | Custom home greeting rules | Extension candidate | M | Scope during design |
| F0646 | Personal work-mode switching | Extension candidate | M | Scope during design |
| F0647 | Workspace layout import and export | Extension candidate | M | Scope during design |
| F0648 | Progressive feature discovery settings | Extension candidate | M | Scope during design |
| F0649 | Private experiment opt-in preferences | Extension candidate | M | Scope during design |
| F0650 | Reset selected preferences with preview | Extension candidate | M | Scope during design |

## Analytics

Current baseline: Insights summarize task completion, time and recent trends.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0651 | Custom analytics dashboard designer | Extension candidate | M | F0040 |
| F0652 | Saved report filter definitions | Extension candidate | M | F0040 |
| F0653 | Task throughput trend reporting | Extension candidate | M | F0040 |
| F0654 | Task aging cohort analysis | Extension candidate | M | F0040 |
| F0655 | Task due-date reliability reports | Extension candidate | M | F0040 |
| F0656 | Project forecast confidence intervals | Extension candidate | M | F0040 |
| F0657 | Estimate accuracy by task category | Extension candidate | M | F0040 |
| F0658 | Lead-time percentile reporting | Extension candidate | M | F0040 |
| F0659 | Blocked-time cause analytics | Extension candidate | M | F0040 |
| F0660 | Workload distribution by assignee | Extension candidate | M | F0040 |
| F0661 | Unplanned work percentage reports | Extension candidate | M | F0040 |
| F0662 | Portfolio milestone forecast reports | Extension candidate | M | F0040 |
| F0663 | Habit outcome correlation exploration | Extension candidate | M | F0040 |
| F0664 | Calendar fragmentation analysis | Extension candidate | M | F0040 |
| F0665 | Meeting versus focus balance reports | Extension candidate | M | F0040 |
| F0666 | Scheduled report email delivery | Extension candidate | M | F0040 |
| F0667 | Analytics metric definition catalog | Extension candidate | M | F0040 |
| F0668 | Report drill-down to source records | Extension candidate | M | F0040 |
| F0669 | Report snapshot comparison | Extension candidate | M | F0040 |
| F0670 | Report access permission controls | Extension candidate | M | F0040 |
| F0671 | CSV report scheduling with scoped data | Extension candidate | M | F0040 |
| F0672 | Time-zone consistent reporting periods | Extension candidate | M | F0040 |
| F0673 | Personal productivity experiment tracking | Extension candidate | M | F0040 |
| F0674 | Analytics data completeness indicators | Extension candidate | M | F0040 |
| F0675 | Analytics anomaly explanation review | Extension candidate | M | F0040 |

## Goals

Current baseline: Goals can be created, edited, completed and removed with target dates.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0676 | Hierarchical goals and subgoals | Extension candidate | M | F0678 |
| F0677 | Measurable key results | Extension candidate | M | F0678 |
| F0678 | Goal progress from linked tasks | Extension candidate | M | Scope during design |
| F0679 | Goal progress from numeric metrics | Extension candidate | M | F0678 |
| F0680 | Weighted goal contribution scoring | Extension candidate | M | F0678 |
| F0681 | Goal confidence check-ins | Extension candidate | M | F0678 |
| F0682 | Goal owner and reviewer roles | Extension candidate | M | F0678 |
| F0683 | Goal alignment map across projects | Extension candidate | M | F0678 |
| F0684 | Quarterly goal planning cycles | Extension candidate | M | F0678 |
| F0685 | Goal baseline and target history | Extension candidate | M | F0678 |
| F0686 | Goal health change notifications | Extension candidate | M | F0678 |
| F0687 | Goal experiment tracking | Extension candidate | M | F0678 |
| F0688 | Goal evidence attachment register | Extension candidate | M | F0678 |
| F0689 | Goal trade-off decision notes | Extension candidate | M | F0678 |
| F0690 | Goal review meeting agenda generation | Extension candidate | M | F0678 |
| F0691 | Goal dependency tracking | Extension candidate | M | F0678 |
| F0692 | Goal paused and abandoned states | Extension candidate | M | F0678 |
| F0693 | Goal outcome retrospective templates | Extension candidate | M | F0678 |
| F0694 | Goal public accountability pages | Extension candidate | M | F0678 |
| F0695 | Goal resource budget allocation | Extension candidate | M | F0678 |
| F0696 | Goal leading versus lagging indicators | Extension candidate | M | F0678 |
| F0697 | Goal scenario forecasting | Extension candidate | M | F0678 |
| F0698 | Goal milestone pacing chart | Extension candidate | M | F0678 |
| F0699 | Goal commitment change requests | Extension candidate | M | F0678 |
| F0700 | Goal portfolio prioritization | Extension candidate | M | F0678 |

## Habits and wellbeing

Current baseline: Daily habit checks and bounded history are implemented.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/lifeos.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0701 | Flexible habit frequency targets | Extension candidate | M | Scope during design |
| F0702 | Habit streak calendars across years | Extension candidate | M | Scope during design |
| F0703 | Habit grace days and recovery rules | Extension candidate | M | Scope during design |
| F0704 | Habit quantity and duration entries | Extension candidate | M | Scope during design |
| F0705 | Habit trigger and cue planning | Extension candidate | M | Scope during design |
| F0706 | Habit stacking relationships | Extension candidate | M | Scope during design |
| F0707 | Habit context-based reminder rules | Extension candidate | M | Scope during design |
| F0708 | Habit negative-behavior reduction tracking | Extension candidate | M | Scope during design |
| F0709 | Habit experiment comparison periods | Extension candidate | M | Scope during design |
| F0710 | Mood journal with private visibility | Extension candidate | M | Scope during design |
| F0711 | Energy check-in timeline | Extension candidate | M | Scope during design |
| F0712 | Sleep duration journal | Extension candidate | M | Scope during design |
| F0713 | Exercise session planning | Extension candidate | M | Scope during design |
| F0714 | Wellbeing trend reflection prompts | Extension candidate | M | Scope during design |
| F0715 | Habit adherence denominator explanations | Extension candidate | M | Scope during design |
| F0716 | Habit pause for holidays or illness | Extension candidate | M | Scope during design |
| F0717 | Habit buddy accountability invitations | Extension candidate | M | Scope during design |
| F0718 | Habit milestone celebrations controls | Extension candidate | M | Scope during design |
| F0719 | Habit data export with date zones | Extension candidate | M | Scope during design |
| F0720 | Habit privacy lock screen | Extension candidate | M | Scope during design |
| F0721 | Personal burnout warning thresholds | Extension candidate | M | Scope during design |
| F0722 | Rest day planning | Extension candidate | M | Scope during design |
| F0723 | Hydration target tracking | Extension candidate | M | Scope during design |
| F0724 | Medication schedule acknowledgment logs | Extension candidate | M | Scope during design |
| F0725 | Wellbeing recommendation opt-out controls | Extension candidate | M | Scope during design |

## Study planning

Current baseline: Courses, assessments, outline review and scheduled study blocks exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/study_planner.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0726 | Assignment rubric criteria tracking | Extension candidate | M | F0748 |
| F0727 | Grade target what-if calculator | Extension candidate | M | F0748 |
| F0728 | Weighted grade forecast intervals | Extension candidate | M | F0748 |
| F0729 | Exam topic coverage planner | Extension candidate | M | F0748 |
| F0730 | Study prerequisite concept graph | Extension candidate | M | F0748 |
| F0731 | Course workload heatmap | Extension candidate | M | F0748 |
| F0732 | Semester capacity planning | Extension candidate | M | F0748 |
| F0733 | Assignment group responsibility tracking | Extension candidate | M | F0748 |
| F0734 | Lab experiment notebook templates | Extension candidate | M | F0748 |
| F0735 | Office-hours question queue | Extension candidate | M | F0748 |
| F0736 | Professor feedback action tracking | Extension candidate | M | F0748 |
| F0737 | Reading assignment progress tracking | Extension candidate | M | F0748 |
| F0738 | Study group session scheduling | Extension candidate | M | F0748 |
| F0739 | Academic citation style formatter | Extension candidate | M | F0748 |
| F0740 | Assessment deadline change detection | Extension candidate | M | F0748 |
| F0741 | LMS import reconciliation review | Extension candidate | M | F0748 |
| F0742 | Course syllabus version comparison | Extension candidate | M | F0748 |
| F0743 | Study plan recovery after missed blocks | Extension candidate | M | F0748 |
| F0744 | Course material permission labels | Extension candidate | M | F0748 |
| F0745 | Assignment submission receipt storage | Extension candidate | M | F0748 |
| F0746 | Academic integrity source disclosure notes | Extension candidate | M | F0748 |
| F0747 | Study session mastery self-assessment | Extension candidate | M | F0748 |
| F0748 | Per-member academic record migration | Extension candidate | M | Scope during design |
| F0749 | Degree requirement progress checklist | Extension candidate | M | F0748 |
| F0750 | Learning accommodation planning preferences | Extension candidate | M | F0748 |

## Spaced learning

Current baseline: Study planning exists; a full spaced-repetition subsystem was not established.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/life_hubs.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0751 | Flashcard deck creation from notes | New subsystem candidate | M | F0251 |
| F0752 | Cloze-deletion flashcards | New subsystem candidate | M | F0251 |
| F0753 | Image occlusion flashcards | New subsystem candidate | M | F0251 |
| F0754 | Spaced-repetition review scheduler | New subsystem candidate | M | F0251 |
| F0755 | Flashcard answer grading controls | New subsystem candidate | M | F0251 |
| F0756 | Flashcard source citation links | New subsystem candidate | M | F0251 |
| F0757 | Flashcard duplicate detection | New subsystem candidate | M | F0251 |
| F0758 | Flashcard suspension and leech handling | New subsystem candidate | M | F0251 |
| F0759 | Flashcard deck sharing permissions | New subsystem candidate | M | F0251 |
| F0760 | Flashcard audio pronunciation clips | New subsystem candidate | M | F0251 |
| F0761 | Flashcard mathematical content support | New subsystem candidate | M | F0251 |
| F0762 | Flashcard review workload forecasting | New subsystem candidate | M | F0251 |
| F0763 | Flashcard import from Anki packages | New subsystem candidate | M | F0251 |
| F0764 | Flashcard export to portable formats | New subsystem candidate | M | F0251 |
| F0765 | Flashcard retention target tuning | New subsystem candidate | M | F0251 |
| F0766 | Practice question bank | New subsystem candidate | M | F0251 |
| F0767 | Practice exam timed sessions | New subsystem candidate | M | F0251 |
| F0768 | Mistake log linked to concepts | New subsystem candidate | M | F0251 |
| F0769 | Topic mastery confidence tracking | New subsystem candidate | M | F0251 |
| F0770 | Interleaved practice session builder | New subsystem candidate | M | F0251 |
| F0771 | Retrieval practice prompt rotation | New subsystem candidate | M | F0251 |
| F0772 | Review queue daily capacity limits | New subsystem candidate | M | F0251 |
| F0773 | Flashcard accessibility reading mode | New subsystem candidate | M | F0251 |
| F0774 | Shared study deck change review | New subsystem candidate | M | F0251 |
| F0775 | Review scheduling algorithm comparison | New subsystem candidate | M | F0251 |

## Career

Current baseline: Job application records, detail/edit flows and reminders exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/career.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0776 | Job application pipeline customization | Extension candidate | M | F0800 |
| F0777 | Resume version management per role | Extension candidate | M | F0800 |
| F0778 | Cover-letter draft approval workflow | Extension candidate | M | F0800 |
| F0779 | Interview preparation question bank | Extension candidate | M | F0800 |
| F0780 | Interview feedback journal | Extension candidate | M | F0800 |
| F0781 | Job posting change snapshots | Extension candidate | M | F0800 |
| F0782 | Job posting deadline extraction review | Extension candidate | M | F0800 |
| F0783 | Recruiter contact relationship tracking | Extension candidate | M | F0800 |
| F0784 | Referral request tracking | Extension candidate | M | F0800 |
| F0785 | Interview panel scheduling links | Extension candidate | M | F0800 |
| F0786 | Offer comparison scorecards | Extension candidate | M | F0800 |
| F0787 | Compensation package scenario models | Extension candidate | M | F0800 |
| F0788 | Skill gap mapping against postings | Extension candidate | M | F0800 |
| F0789 | Portfolio evidence library | Extension candidate | M | F0800 |
| F0790 | Professional development learning plan | Extension candidate | M | F0800 |
| F0791 | Certification renewal tracking | Extension candidate | M | F0800 |
| F0792 | Networking follow-up cadence plans | Extension candidate | M | F0800 |
| F0793 | Employment contract review checklist | Extension candidate | M | F0800 |
| F0794 | Application conversion funnel reports | Extension candidate | M | F0800 |
| F0795 | Job search weekly commitment tracking | Extension candidate | M | F0800 |
| F0796 | Application duplicate submission warning | Extension candidate | M | F0800 |
| F0797 | Employer research dossiers | Extension candidate | M | F0800 |
| F0798 | Interview thank-you draft review | Extension candidate | M | F0800 |
| F0799 | Professional accomplishment journal | Extension candidate | M | F0800 |
| F0800 | Per-member career record migration | Extension candidate | M | Scope during design |

## Transactions

Current baseline: BMO/Scotiabank PDF import, categories, rules, editing and pagination exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/finance/routes.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0801 | Additional bank parser plug-in interface | Extension candidate | L | F0825 |
| F0802 | Statement import reconciliation checklist | Extension candidate | L | F0825 |
| F0803 | Duplicate transaction review queue | Extension candidate | L | F0825 |
| F0804 | Split transaction categorization | Extension candidate | L | F0825 |
| F0805 | Transfer matching between accounts | Extension candidate | L | F0825 |
| F0806 | Refund linkage to original transactions | Extension candidate | L | F0825 |
| F0807 | Pending versus posted transaction states | Extension candidate | L | F0825 |
| F0808 | Multi-currency ledger support | Extension candidate | L | F0825 |
| F0809 | Exchange-rate provenance and overrides | Extension candidate | L | F0825 |
| F0810 | Receipt image attachment matching | Extension candidate | L | F0825 |
| F0811 | Transaction merchant enrichment review | Extension candidate | L | F0825 |
| F0812 | Category hierarchy with rollup totals | Extension candidate | L | F0825 |
| F0813 | Recurring merchant detection proposals | Extension candidate | L | F0825 |
| F0814 | Transaction import source lineage | Extension candidate | L | F0825 |
| F0815 | Transaction anomaly review queue | Extension candidate | L | F0825 |
| F0816 | Cash account manual ledger | Extension candidate | L | F0825 |
| F0817 | Account balance reconciliation | Extension candidate | L | F0825 |
| F0818 | Investment transaction classification | Extension candidate | L | F0825 |
| F0819 | Transaction dispute follow-up tracker | Extension candidate | L | F0825 |
| F0820 | Tax tag assignment with user review | Extension candidate | L | F0825 |
| F0821 | Household transaction sharing scopes | Extension candidate | L | F0825 |
| F0822 | Merchant rule simulation before apply | Extension candidate | L | F0825 |
| F0823 | Statement page-level extraction diagnostics | Extension candidate | L | F0825 |
| F0824 | Financial data correction audit trail | Extension candidate | L | F0825 |
| F0825 | Per-member finance ledgers with legacy-owner migration | Extension candidate | L | Scope during design |

## Budget and bills

Current baseline: Staged budget editing, monthly conversion and recurring bill successor protection exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/finance/budget.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0826 | Envelope funding allocation | Extension candidate | M | F0825 |
| F0827 | Budget rollover rules | Extension candidate | M | F0825 |
| F0828 | Budget zero-based planning checks | Extension candidate | M | F0825 |
| F0829 | Budget scenario comparison | Extension candidate | M | F0825 |
| F0830 | Budget versus actual category alerts | Extension candidate | M | F0825 |
| F0831 | Sinking fund goal schedules | Extension candidate | M | F0825 |
| F0832 | Debt payoff strategy comparisons | Extension candidate | M | F0825 |
| F0833 | Loan amortization projections | Extension candidate | M | F0825 |
| F0834 | Bill autopay status tracking | Extension candidate | M | F0825 |
| F0835 | Bill expected versus actual amount tracking | Extension candidate | M | F0825 |
| F0836 | Bill document attachment archive | Extension candidate | M | F0825 |
| F0837 | Variable recurring bill forecasts | Extension candidate | M | F0825 |
| F0838 | Subscription renewal cancellation windows | Extension candidate | M | F0825 |
| F0839 | Subscription price-change review | Extension candidate | M | F0825 |
| F0840 | Budget annual irregular expense planner | Extension candidate | M | F0825 |
| F0841 | Shared household budget approval | Extension candidate | M | F0825 |
| F0842 | Budget allocation change history | Extension candidate | M | F0825 |
| F0843 | Cash-flow forecast calendar | Extension candidate | M | F0825 |
| F0844 | Emergency fund runway estimates | Extension candidate | M | F0825 |
| F0845 | Savings transfer suggestion review | Extension candidate | M | F0825 |
| F0846 | Budget category overspend action plans | Extension candidate | M | F0825 |
| F0847 | Bill payment confirmation attachments | Extension candidate | M | F0825 |
| F0848 | Installment payment schedules | Extension candidate | M | F0825 |
| F0849 | Budget import from external planning tools | Extension candidate | M | F0825 |
| F0850 | Budget planned contribution versus actual transfer | Extension candidate | M | F0825 |

## Household

Current baseline: Grocery lists, recipe ingredients, prices and shared spaces already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/workspace.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0851 | Household chore rotation schedules | Extension candidate | M | Scope during design |
| F0852 | Household inventory locations | Extension candidate | M | Scope during design |
| F0853 | Pantry stock quantity tracking | Extension candidate | M | Scope during design |
| F0854 | Pantry expiry date alerts | Extension candidate | M | Scope during design |
| F0855 | Meal plan calendar | Extension candidate | M | Scope during design |
| F0856 | Meal plan to grocery list generation | Extension candidate | M | Scope during design |
| F0857 | Recipe nutrition metadata | Extension candidate | M | Scope during design |
| F0858 | Recipe dietary restriction filters | Extension candidate | M | Scope during design |
| F0859 | Recipe portion scaling with unit conversion | Extension candidate | M | Scope during design |
| F0860 | Grocery aisle ordering per store | Extension candidate | M | Scope during design |
| F0861 | Grocery price comparison by store | Extension candidate | M | Scope during design |
| F0862 | Grocery budget prediction from list | Extension candidate | M | Scope during design |
| F0863 | Grocery receipt purchase reconciliation | Extension candidate | M | Scope during design |
| F0864 | Household shopping assignment claims | Extension candidate | M | Scope during design |
| F0865 | Household maintenance asset register | Extension candidate | M | Scope during design |
| F0866 | Appliance warranty and service reminders | Extension candidate | M | Scope during design |
| F0867 | Home repair project estimates | Extension candidate | M | Scope during design |
| F0868 | Household document emergency binder | Extension candidate | M | Scope during design |
| F0869 | Shared household packing checklists | Extension candidate | M | Scope during design |
| F0870 | Utility usage readings and trends | Extension candidate | M | Scope during design |
| F0871 | Household supply reorder thresholds | Extension candidate | M | Scope during design |
| F0872 | Recipe substitution preference rules | Extension candidate | M | Scope during design |
| F0873 | Grocery allergen warning labels | Extension candidate | M | Scope during design |
| F0874 | Household contact and service directory | Extension candidate | M | Scope during design |
| F0875 | Household shared errand route planning | Extension candidate | M | Scope during design |

## Publishing

Current baseline: Member/project sharing exists; public publishing requires a separate scoped model.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/workspace.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0876 | Public read-only note publishing | New subsystem candidate | M | F0882 |
| F0877 | Public project status pages | New subsystem candidate | M | F0882 |
| F0878 | Custom public page slugs | New subsystem candidate | M | F0882 |
| F0879 | Public page access passwords | New subsystem candidate | M | F0882 |
| F0880 | Public page expiration dates | New subsystem candidate | M | F0882 |
| F0881 | Public page unpublish and revocation | New subsystem candidate | M | F0882 |
| F0882 | Publish review and approval queue | New subsystem candidate | M | Scope during design |
| F0883 | Publish preview versus live version diff | New subsystem candidate | M | F0882 |
| F0884 | Public page search indexing controls | New subsystem candidate | M | F0882 |
| F0885 | Published knowledge collection navigation | New subsystem candidate | M | F0882 |
| F0886 | Public page custom domain mapping | New subsystem candidate | M | F0882 |
| F0887 | Public page change subscription feed | New subsystem candidate | M | F0882 |
| F0888 | Public changelog builder | New subsystem candidate | M | F0882 |
| F0889 | Public roadmap with moderated votes | New subsystem candidate | M | F0882 |
| F0890 | Embeddable read-only task views | New subsystem candidate | M | F0882 |
| F0891 | Published page accessibility validation | New subsystem candidate | M | F0882 |
| F0892 | Published asset permission isolation | New subsystem candidate | M | F0882 |
| F0893 | Download permission for public attachments | New subsystem candidate | M | F0882 |
| F0894 | Public page view analytics with consent | New subsystem candidate | M | F0882 |
| F0895 | Public page content license labels | New subsystem candidate | M | F0882 |
| F0896 | Static export of approved pages | New subsystem candidate | M | F0882 |
| F0897 | Public form and knowledge portal linking | New subsystem candidate | M | F0882 |
| F0898 | Client portal per-project access | New subsystem candidate | M | F0882 |
| F0899 | Public page localization variants | New subsystem candidate | M | F0882 |
| F0900 | Link leakage and revocation audit | New subsystem candidate | M | F0882 |

## Security

Current baseline: Session login, approval, verified recovery, cross-site guards and scoped sharing exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/auth.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0901 | Passkey registration and login | Extension candidate | L | Scope during design |
| F0902 | TOTP multifactor authentication | Extension candidate | L | Scope during design |
| F0903 | Recovery code generation and rotation | Extension candidate | L | Scope during design |
| F0904 | Session device management UI | Extension candidate | L | Scope during design |
| F0905 | Suspicious login notification policies | Extension candidate | L | Scope during design |
| F0906 | SSO via OpenID Connect | Extension candidate | L | Scope during design |
| F0907 | Enterprise SAML authentication | Extension candidate | XL | Scope during design |
| F0908 | SCIM user provisioning | Extension candidate | XL | Scope during design |
| F0909 | IP allowlist policies by workspace | Extension candidate | L | Scope during design |
| F0910 | Per-token API scopes | Extension candidate | L | Scope during design |
| F0911 | Reauthentication for sensitive exports | Extension candidate | L | Scope during design |
| F0912 | Attachment download authorization tests | Extension candidate | L | Scope during design |
| F0913 | Tamper-evident administrative event log | Extension candidate | L | Scope during design |
| F0914 | Data-change audit trails beyond auth events | Extension candidate | L | Scope during design |
| F0915 | Security event export to SIEM | Extension candidate | L | Scope during design |
| F0916 | Configurable session idle timeout | Extension candidate | L | Scope during design |
| F0917 | Concurrent session limits | Extension candidate | L | Scope during design |
| F0918 | Service-account credential rotation | Extension candidate | L | Scope during design |
| F0919 | Malware scanning integration policy | Extension candidate | L | Scope during design |
| F0920 | Content security policy enforcement reports | Extension candidate | L | Scope during design |
| F0921 | Automated dependency vulnerability review | Extension candidate | L | Scope during design |
| F0922 | Secret exposure scanning in uploads | Extension candidate | L | Scope during design |
| F0923 | Permission change impact previews | Extension candidate | L | Scope during design |
| F0924 | Emergency account access recovery runbook | Extension candidate | L | Scope during design |
| F0925 | Tenant isolation regression test matrix | Extension candidate | L | Scope during design |

## Privacy and governance

Current baseline: Privacy pages and account protections exist; governance workflows are limited.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/account_security.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0926 | User data access request export | New subsystem candidate | XL | F0914 |
| F0927 | Account deletion and erasure workflow | New subsystem candidate | XL | F0914 |
| F0928 | Record retention schedules by category | New subsystem candidate | XL | F0914 |
| F0929 | Legal hold preservation policies | New subsystem candidate | XL | F0914 |
| F0930 | Field-level sensitive data classification | New subsystem candidate | XL | F0914 |
| F0931 | Personal versus team data boundary labels | New subsystem candidate | XL | F0914 |
| F0932 | AI data-processing consent ledger | New subsystem candidate | XL | F0914 |
| F0933 | Third-party integration data transfer register | New subsystem candidate | XL | F0914 |
| F0934 | Per-connector retention and deletion controls | New subsystem candidate | XL | F0914 |
| F0935 | Redacted support diagnostic export | New subsystem candidate | XL | F0914 |
| F0936 | Access review certification workflow | New subsystem candidate | XL | F0914 |
| F0937 | Data owner assignment policies | New subsystem candidate | XL | F0914 |
| F0938 | Data residency configuration report | New subsystem candidate | XL | F0914 |
| F0939 | Encryption key inventory and lifecycle | New subsystem candidate | XL | F0914 |
| F0940 | Backup retention and deletion verification | New subsystem candidate | XL | F0914 |
| F0941 | Privacy-preserving usage analytics settings | New subsystem candidate | XL | F0914 |
| F0942 | User activity log visibility controls | New subsystem candidate | XL | F0914 |
| F0943 | Sensitive record redaction previews | New subsystem candidate | XL | F0914 |
| F0944 | Export watermarking policy | New subsystem candidate | XL | F0914 |
| F0945 | Deidentified research dataset export | New subsystem candidate | XL | F0914 |
| F0946 | Guest access expiry review queue | New subsystem candidate | XL | F0914 |
| F0947 | Data lineage from imports to derived records | New subsystem candidate | XL | F0914 |
| F0948 | Consent withdrawal propagation workflow | New subsystem candidate | XL | F0914 |
| F0949 | Privacy incident response tracking | New subsystem candidate | XL | F0914 |
| F0950 | Subprocessor documentation register | New subsystem candidate | XL | F0914 |

## Reliability

Current baseline: SQLite startup snapshots, bounded workers, CI and container checks already exist.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/backup.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0951 | Scheduled encrypted backup orchestration | Extension candidate | L | Scope during design |
| F0952 | Automated restore rehearsal jobs | Extension candidate | L | Scope during design |
| F0953 | Backup freshness alerting | Extension candidate | L | Scope during design |
| F0954 | Database integrity monitoring dashboard | Extension candidate | L | Scope during design |
| F0955 | Attachment-to-database consistency checks | Extension candidate | L | Scope during design |
| F0956 | Operational health and readiness endpoints separation | Extension candidate | L | Scope during design |
| F0957 | Queue depth and age monitoring | Extension candidate | L | Scope during design |
| F0958 | Background job dead-letter queue | Extension candidate | L | Scope during design |
| F0959 | Calendar sync retry backoff metrics | Extension candidate | L | Scope during design |
| F0960 | Notification delivery observability dashboard | Extension candidate | L | Scope during design |
| F0961 | Structured request correlation IDs | Extension candidate | L | Scope during design |
| F0962 | Per-route latency percentile dashboards | Extension candidate | L | Scope during design |
| F0963 | Slow database query diagnostics | Extension candidate | L | Scope during design |
| F0964 | Storage capacity forecasting | Extension candidate | L | Scope during design |
| F0965 | Graceful scheduler leader election | Extension candidate | L | Scope during design |
| F0966 | Multiple-worker background job deduplication | Extension candidate | L | Scope during design |
| F0967 | Zero-downtime database migration rehearsal | Extension candidate | XL | Scope during design |
| F0968 | Release rollback readiness checks | Extension candidate | L | Scope during design |
| F0969 | Versioned configuration validation | Extension candidate | L | Scope during design |
| F0970 | Dependency outage status pages | Extension candidate | L | Scope during design |
| F0971 | Resource usage budgets on Raspberry Pi | Extension candidate | L | Scope during design |
| F0972 | Disaster recovery restore wizard | Extension candidate | L | Scope during design |
| F0973 | Synthetic user workflow probes | Extension candidate | L | Scope during design |
| F0974 | Upgrade compatibility preflight checks | Extension candidate | L | Scope during design |
| F0975 | Long-running job cancellation and recovery | Extension candidate | L | Scope during design |

## Developer platform

Current baseline: Internal v4 APIs and compatibility adapters exist; a public extension platform is not established.

[Source anchor](https://github.com/pierre-2005/study-notifier/blob/d4e459a337fb36507b985f32e302b4b5f06bf1a6/app/workspace_api.py#L1). Candidate status applies to every entry.

| ID | Proposed capability | Scope | Effort | Prerequisite examples |
| --- | --- | --- | --- | --- |
| F0976 | Public versioned API documentation | New subsystem candidate | XL | F0910 |
| F0977 | Personal access token management | New subsystem candidate | XL | F0910 |
| F0978 | OAuth app registration for developers | New subsystem candidate | XL | F0910 |
| F0979 | Webhook subscription management | New subsystem candidate | XL | F0910 |
| F0980 | Signed webhook payload verification | New subsystem candidate | XL | F0910 |
| F0981 | Webhook replay and delivery logs | New subsystem candidate | XL | F0910 |
| F0982 | Cursor-based public API pagination | New subsystem candidate | XL | F0910 |
| F0983 | API rate-limit headers and budgets | New subsystem candidate | XL | F0910 |
| F0984 | API idempotent mutation support | New subsystem candidate | XL | F0910 |
| F0985 | API change deprecation notices | New subsystem candidate | XL | F0910 |
| F0986 | Typed client SDK generation | New subsystem candidate | XL | F0910 |
| F0987 | Extension permission manifest format | New subsystem candidate | XL | F0910 |
| F0988 | Sandboxed dashboard widget extensions | New subsystem candidate | XL | F0910 |
| F0989 | Custom record type extension hooks | New subsystem candidate | XL | F0910 |
| F0990 | Integration test fixture toolkit | New subsystem candidate | XL | F0910 |
| F0991 | Migration dry-run tooling for extensions | New subsystem candidate | XL | F0910 |
| F0992 | Portable workspace package specification | New subsystem candidate | XL | F0910 |
| F0993 | Plugin installation compatibility checks | New subsystem candidate | XL | F0910 |
| F0994 | Plugin disable and rollback controls | New subsystem candidate | XL | F0910 |
| F0995 | Developer event stream subscriptions | New subsystem candidate | XL | F0910 |
| F0996 | Public API permission scope explorer | New subsystem candidate | XL | F0910 |
| F0997 | CLI bulk import and export tools | New subsystem candidate | XL | F0910 |
| F0998 | Automation definition interchange format | New subsystem candidate | XL | F0910 |
| F0999 | Database schema migration contract tests | New subsystem candidate | XL | F0910 |
| F1000 | Extension marketplace review workflow | New subsystem candidate | XL | F0910 |
