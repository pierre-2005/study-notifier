# MLO release plan and provisional effort

Prepared November 2, 2026, against MLO 4.2.1 and the 4.3 working release.

## What the next version actually contains

4.3.0 implements the requested due-date navigation correction, map status filters (All, Open, Completed, To do, In progress, Blocked), labeled ancestor context, left-to-right/top-to-bottom views, user/project-specific browser view preferences, horizontal wheel and Shift-wheel panning, wheel unit normalization, layout/Undo compatibility across orientations, stable two-finger gestures and responsive camera recovery. It does not implement the 2,000-item backlog. The release keeps the existing data schema and saves map coordinates in the original coordinate space.

## Immediate work estimates

| Batch | Provisional focused effort |
|---|---|
| Diagnose and fix due-date false warnings | 1–3 hours |
| Map filters, orientations and wheel controls | 4–8 hours |
| Release regression, responsive and accessibility checks | 2–4 hours plus external CI queues |
| Research, curate and package another 1,000 proposals | 8–16 hours |
| Shared records/search/history/permission/automation foundations | 4–10 weeks for a first useful slice, not all depth |

These ranges are planning estimates for focused engineering and verification, not a stopwatch, guaranteed AI completion time or calendar commitment. A week means roughly five focused working days. No timesheet was measured. Approval waits, CI queues, account setup, vendor licensing, hosting changes and production rollout are excluded. Batch ranges below assume usable foundations and explicitly approved specifications; the largest items can exceed them. The total cannot be obtained by adding overlapping rows. The full backlog is a many-month to multi-year program for a small team, depending on retained scope.

## Sequence that preserves speed and clarity

1. 4.3: map/navigation fixes and their regression coverage. Validate this release before merging and publishing; the owner handles Portainer.
2. A foundation release: task activity and recoverable deletion, permission-scoped full-text search, typed fields, saved views, note history/backlinks and restore verification. First useful slice: 4–10 weeks.
3. A flexible record release: record schemas, relation fields, imports with dry-run/reconciliation, files and audit history. First useful slice: 6–12 weeks, overlapping foundation work.
4. An engineering pilot: drawing register, issued revisions, imported markup-to-task links and one controlled export adapter. First useful pilot: 4–8 weeks after foundations and anonymized real exports.
5. Coordination depth: transmittals, design review, RFIs, submittals, clash follow-up, equipment/wire references and commissioning evidence, one end-to-end workflow per release.
6. Broader client/resource/portfolio workflows and optional AI or offline capabilities, selected only after measuring actual use and load.

Proposed later versions are sequencing buckets, not frozen version numbers or release dates. Each release needs working flows, authorization tests, migration/rollback evidence if applicable, and measured latency.

Catalogs: [original 1,000](roadmap/ORIGINAL_1000.md) and [additional 1,000](roadmap/ADDITIONAL_1000.md).

## Original catalog: 40 major work batches

| Area (25 proposals each) | Provisional full-batch range |
|---|---|
| Capture | 3–8 weeks |
| Task planning | 4–10 weeks |
| Recurrence | 3–8 weeks |
| Projects | 4–10 weeks |
| Agile workflows | 4–10 weeks |
| Task map | 4–12 weeks |
| Calendar | 6–16 weeks |
| Scheduling | 6–16 weeks |
| Focus | 3–8 weeks |
| Note editor | 6–16 weeks |
| Knowledge linking | 4–10 weeks |
| Flexible databases | 8–20 weeks |
| Forms | 4–12 weeks |
| Documents and PDFs | 8–24 weeks |
| Files | 4–12 weeks |
| AI writing | 6–16 weeks |
| AI retrieval | 8–20 weeks |
| AI agents | 12–30 weeks |
| Collaboration | 8–24 weeks |
| Communication | 12–30 weeks |
| Search | 4–12 weeks |
| Workflow automation | 10–24 weeks |
| Integrations | 12–30 weeks |
| Mobile and offline | 12–30 weeks |
| Accessibility | 4–12 weeks |
| Personalization | 3–8 weeks |
| Analytics | 6–16 weeks |
| Goals | 3–8 weeks |
| Habits and wellbeing | 4–12 weeks |
| Study planning | 6–16 weeks |
| Spaced learning | 8–20 weeks |
| Career | 6–16 weeks |
| Transactions | 8–20 weeks |
| Budget and bills | 6–16 weeks |
| Household | 4–12 weeks |
| Publishing | 8–20 weeks |
| Security | 8–24 weeks |
| Privacy and governance | 8–24 weeks |
| Reliability | 8–24 weeks |
| Developer platform | 12–30 weeks |

## Additional catalog: 40 major work batches

| Area (25 proposals each) | Provisional full-batch range |
|---|---|
| Drawing register | 3–6 weeks |
| Transmittals | 4–10 weeks |
| Design review rounds | 4–10 weeks |
| Markup coordination | 4–10 weeks |
| Drawing comparison | 6–16 weeks |
| Equipment register | 4–10 weeks |
| Wire and cable tracking | 4–10 weeks |
| Terminals and connectors | 4–10 weeks |
| Panel fabrication | 4–10 weeks |
| Engineering procurement | 4–10 weeks |
| PLC and instrumentation | 4–10 weeks |
| Electrical checking | 4–10 weeks |
| Model coordination | 4–10 weeks |
| Clash triage | 4–10 weeks |
| Viewpoint evidence | 4–10 weeks |
| Construction sequencing | 4–10 weeks |
| Field punch and inspections | 4–10 weeks |
| Requests for information | 4–10 weeks |
| Submittal management | 4–10 weeks |
| Engineering change control | 4–10 weeks |
| Commissioning | 4–10 weeks |
| Asset handover and maintenance | 4–10 weeks |
| Quantity takeoff coordination | 4–10 weeks |
| Document package handover | 4–10 weeks |
| Engineering import adapters | 6–16 weeks |
| Relationship intelligence | 3–8 weeks |
| Opportunity delivery pipeline | 3–8 weeks |
| Customer support operations | 3–8 weeks |
| Client delivery operations | 3–8 weeks |
| Revenue workflow quality | 3–8 weeks |
| Portfolio decision governance | 3–8 weeks |
| Resource and skills planning | 3–8 weeks |
| Commercial time and cost | 3–8 weeks |
| Product quality delivery | 3–8 weeks |
| Workflow assurance | 3–8 weeks |
| Data quality operations | 3–8 weeks |
| Analytical exploration | 3–8 weeks |
| Navigation and interaction polish | 2–6 weeks |
| Performance engineering | 4–12 weeks |
| Workspace operating model | 3–8 weeks |

## Pilot acceptance and dependencies

The drawing pilot should import a sample register without altering original files; flag conflicting drawing/revision keys; freeze an issued revision; attach an imported review comment to a real task; preserve external IDs, page coordinates and source hashes; show review/closure evidence; and reconcile a second import without duplicating records. Test access as owner, editor, viewer and unrelated user. A rollback must remove the imported batch without damaging unrelated work.

Before a working AutoCAD Electrical, Navisworks or Bluebeam adapter can be declared compatible, obtain anonymized real exports from the versions used at work, identify available export formats and define who owns the data. API write-back additionally depends on vendor access, licensing and explicit authorization. No connector account was accessed during this work.

Preserve existing legacy-owner finance, academic and career boundaries while migrating those subsystems. New records must use explicit ownership and membership scopes; enabling a feature is not a reason to expose another member’s existing data.

## Performance acceptance proposal

Record hardware, browser, dataset and cold/warm conditions. Target p95 under 100 ms for local UI feedback, under 250 ms for warm in-app transitions where feasible, and 60 Hz gesture rendering when hardware permits. These are proposed budgets, not claims already verified in production. Track p95 server latency, query counts, payload/DOM size, long tasks and memory across repeated map opening. Start with 150 and 500 tasks, then test the 2,000-task limit on the target Raspberry Pi before promising that scale.

Do not add every subsystem to the main navigation. Use role/module profiles and progressive disclosure; load previews, maps, PDF tools and external data only when needed. Profile bottlenecks before applying caching, workers or virtualization.
