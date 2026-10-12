# My Life Organized (MLO) — Product Strategy, Competitive Audit & Zero-Friction Adoption
**Research cut-off:** October 12, 2026  
**Audit basis:** user-uploaded `study-notifier-main(1).zip` (August 9, 2026 archive), public GitHub listing, vendor documentation, and qualitative community feedback.  
**Core product principle (October 2026 update):** No mandatory workspace setup; first useful action in under one minute; advanced controls opt-in; genuinely useful free personal core. Detailed specification in §5.  
**Important scope limitation:** the earlier generated v2.0.0 package could not be re-opened in this session, and the public GitHub repository was older than the uploaded ZIP. Therefore "missing" below means not verified in the uploaded source, not guaranteed absent from a later private deployment. This document is a proposed product specification, not implemented software.

## 1. Verified starting point
Existing in uploaded code: courses, assignments/exams/labs, class meetings, events, job-application tracking, standalone to-dos, expenses with recurring bills, finance budgets and statement imports, basic reminder scheduling via ntfy, admin user signup/approval, sharable blank/grocery Sections, recipes and price history, count-down timers, configurable colors/themes, responsive navigation, command palette. Finance and academic tables originally have no `user_id`, non-admin account access was limited by middleware. No project module verified in ZIP; no general block editor, robust task hierarchy, complete local-first sync, native calendar integration, comprehensive API, test suite, observability, PWA manifest/service worker, or CI found in uploaded ZIP.

## 2. Full relevant capability inventory
The following list is a broad engineering backlog: each capability is independent; some should ship together for coherence.

### Foundation: privacy, accounts and collaboration [P0]
- [ ] Assign `owner_user_id` or team/workspace ID to every personal record and enforce authorization on every read, mutation, import, export, and notification.
- [ ] Separate personal spaces, team spaces and shared areas; per-project invite links and roles (owner/admin/editor/commenter/viewer/guest).
- [ ] Database migration with tested pre-upgrade backup and rollback; schema versioning.
- [ ] User settings per person: timezone, locale, quiet hours, reminders, palettes, privacy, week start.
- [ ] Multi-device management, revoke lost device, session history, forced logout, account deletion/export.
- [ ] Verified email and password recovery, passkeys/2FA, rate limiting and suspicious sign-in monitoring.
- [ ] CSRF tokens, rigorous input validation, upload virus scanning, secret rotation, HTTPS and security headers.
- [ ] Fine-grained share permissions, private-by-default content, audit trail, activity logs and version history.
- [ ] Robust notification routing per user/device/channel, delivery retries, deduplication and provider fallback.
- [ ] Backup restore drills, retention policy, encrypted backups, monitoring and incident recovery runbooks.

### Frictionless first use and fair access [P0: product-defining requirement]
- [ ] Create a useful task/note/event immediately after login with zero mandatory setup; auto-provision private Inbox and basic workspace.
- [ ] Start every new user in Simple mode, with skippable career templates and reversible Guided/Professional settings.
- [ ] Plain-language universal Quick Add, minimal first-task/project forms and context-sensitive suggestions; title-only input should always work.
- [ ] Safe imports with preview, duplicates/missing-field warning, progress/resume and undo/rollback; keep originals where possible.
- [ ] Free personal core with no arbitrary task/project/note/timer counts or surprise collaboration block cap; communicate real hosted-resource costs openly.
- [ ] Optional contextual learning, no forced tutorial or paywalled beginner features; validate novice mobile workflows independently.
- [ ] Accessibility, low-bandwidth support and transparent offline/save state treated as usability essentials.
- [ ] Instrument time-to-first-value, successful unassisted task creation and onboarding abandonment; run user tests before major release.

### Navigation, dashboard and experience [P1]
- [ ] Unified personal home with custom widgets, pinned resources, widgets per device and drag/reorder.
- [ ] Today, Upcoming, This Week, Someday, Waiting For, Assigned To Me and Completed screens.
- [ ] Universal search across tasks/projects/notes/attachments (permission-aware) with filters.
- [ ] Global quick capture supporting keyboard, mobile, share-sheet, voice and email import.
- [ ] Breadcrumbs, recent pages, favorites, saved searches, command palette actions, keyboard shortcuts.
- [ ] Universal activity/inbox center with actionable notifications and snooze.
- [ ] Empty-state sample content, templates, guided onboarding and contextual explanations.
- [ ] Consistent bulk edit, undo, optimistic UI, drag-and-drop, inline editing, keyboard navigation.
- [ ] Accessibility: WCAG 2.2 AA-oriented implementation, touch targets, contrast, focus, screen readers, reduced motion.
- [ ] PWA install with offline-safe shell, update prompts, push notifications and homescreen shortcuts.
- [ ] Responsive compact phone views distinct from dense desktop views; tablet split panes.

### Unified task engine [P1]
- [ ] Single canonical task object with owner, workspace, list, project, course, context, client and linked records.
- [ ] Inbox capture; due date vs scheduled/do date; start date; timezone; estimates; effort; energy requirement.
- [ ] Flexible statuses, custom workflows and priorities; independent importance/urgency flags.
- [ ] Nested subtasks, reusable checklists, multi-assignee option, watchers and followers.
- [ ] Dependencies (blocks/is blocked by), blockers and automatically calculated readiness.
- [ ] Recurrence with proper occurrence generation, exceptions, next-instance policy and missed-instance handling.
- [ ] Native reminders, snooze, repeat reminder, digest, escalations and device-specific preferences.
- [ ] Comments, @mentions, change history, file/link attachments, rich descriptions.
- [ ] Tags, custom fields, cross-project task relationships, task templates and bulk operations.
- [ ] Saved filtered views, list/board/calendar/timeline, smart sorting and pinned views.
- [ ] Natural-language quick add for dates and recurrence; voice capture, email to task, browser clipper.
- [ ] Automatic scheduling based on available calendar time, manual override and transparent constraints.
- [ ] Task-level time logs, billable flags, remaining estimate and planned vs actual time.
- [ ] Delegation, awaiting reply/approval, reminders on other people's deadlines and follow-up queue.

### Projects, programs, goals and portfolios [P1]
- [ ] Project creation with name, owner/team, category, template, description, cover, color, status, dates and members.
- [ ] Project home with overview, tasks, activity, notes, files, timeline, goals, decisions and reporting.
- [ ] Lists/sections/phases, milestones, deliverables, attachments and project health.
- [ ] List, Kanban, calendar, Gantt, timeline, table and resource-capacity views over the same records.
- [ ] Dependencies and critical path; baseline dates; multiple scenarios; delayed-task alerts.
- [ ] Project templates: academic capstone, engineering design, software sprint, client delivery, home renovation, event planning.
- [ ] Portfolios, initiatives, life goals, quarterly objectives/OKRs linked to projects and tasks.
- [ ] Resource workload, capacity limits, effort estimates, timesheets and work allocation.
- [ ] Project budget, expenses, billable time, timesheet export and profitability (optional by workspace).
- [ ] Risks, issues, assumptions, decisions (RAID), change requests, approvals and stakeholder register.
- [ ] Project status summaries, burnup/burndown, velocity, throughput and progress projections.
- [ ] Client portal, external share links and exportable status reports with strict permission controls.
- [ ] Project duplication, archive, version/history and trash/recovery.

### Timers and time [P1]
- [ ] Preserve existing countdown timer; add stopwatch, Pomodoro, deep work and break cycles.
- [ ] Start a focus session from any task/project/course and link logged time to the source record.
- [ ] Persistent timer using server timestamps; correct after reload, tab sleep, phone lock and timezone changes.
- [ ] Optional automatic break timer, long break after configured cycles, sound/vibration/notification settings.
- [ ] Distraction log, interruptions/pause reasons, session intention and post-session notes.
- [ ] Daily/weekly focus reports, planned vs actual hours, task estimates vs time logs.
- [ ] Manual entry editing, rounding rules, approval, weekly timesheets and CSV export.
- [ ] Billable/non-billable labeling, client/project reporting and cost rates (restricted access).
- [ ] Full-screen, mini-timer and persistent global timer; focus music opt-in; reduced-motion mode.
- [ ] Optional shared/team focus sessions and accountability, without exposing private data.

### Calendar and life planning [P1/P2]
- [ ] Combined agenda for tasks, meetings, classes, events, deadlines and time blocks.
- [ ] Day, week, month, agenda and timeline layouts; drag/reschedule with conflict handling.
- [ ] Calendar integrations: Google, Microsoft/Outlook, Apple/iCloud/CalDAV subject to provider capabilities.
- [ ] Per-calendar color and visibility; work and personal calendar privacy controls.
- [ ] Timeboxing from task lists; free-time detection, overload warning, task rollover and day shutdown.
- [ ] Scheduling links, availability buffers, recurrence exceptions, travel time (optional) and timezone support.
- [ ] Daily startup and weekly review guided flows, habit-friendly recurring routines.
- [ ] Reliable two-way synchronization with conflict handling, idempotency and granular permissions.

### Notes, documents and knowledge [P2]
- [ ] Nested pages and rich block editor: headings, paragraphs, callouts, quotes, toggles, checklists, tables and code.
- [ ] Markdown, math/LaTeX, tables, diagrams, images, video, audio, file embeds and PDF preview.
- [ ] Pages connected to projects/tasks/courses/contacts; backlinks and linked references.
- [ ] Optional graph or visual canvas for brainstorming and connected knowledge.
- [ ] Tables with properties, types, relations, rollups, formulas and multiple saved views.
- [ ] Database and page templates, reusable synced blocks, embeds and page comments.
- [ ] Revision history, autosave, conflict management, restore and portable export Markdown/PDF/CSV/JSON.
- [ ] Reading and research capture, web clipper, citation manager, bookmarks and annotated reference files.
- [ ] Semantic search/AI Q&A, with clear permissions, source citations and opt-in model providers.

### Study, learning and career [P2]
- [ ] Terms/semesters, course syllabi imports, weighted grade calculator and grade targets.
- [ ] Grade-based what-if projections, exam countdowns, assessment rubrics and study schedule generation.
- [ ] Spaced repetition, flashcards, retrieval quizzes, concept maps and revision history.
- [ ] Assignment breakdown to linked tasks/subtasks, lab checklist, group project scheduling.
- [ ] Course resources, lecture notes, reading tracker, research papers, annotations and citations.
- [ ] Internship/job CRM, recruiter contacts, application documents, follow-up schedule, interview practice.
- [ ] Skills matrix, licenses/certifications/CE records, professional development and portfolio evidence.
- [ ] Career roadmaps, job-search analytics and application stage templates.

### Home, money, health-adjacent and personal [P2]
- [ ] Habits, streaks with grace days, life goals, routines and periodic reviews.
- [ ] Personal finance accounts, reconciliations, budgets vs actual, debt, savings and net-worth tracking.
- [ ] Bills/subscription renewal dashboard, recurring expense forecasting, receipt capture and split bills.
- [ ] Meal planning, pantry/inventory with expirations, shopping optimization, household recurring chores.
- [ ] Asset inventory, home/warranty/maintenance schedule, family sharing and travel checklists.
- [ ] Personal journaling, gratitude, reading lists and optional wellbeing logs with strict private storage.
- [ ] Contacts and relationships, birthdays, follow-ups and shared event planning.

### Customization, automation and integrations [P2]
- [ ] Structured workspace templates by role, discipline, life context and company type.
- [ ] User-defined entity types, typed custom fields and reusable forms with conditional questions.
- [ ] Rule builder: trigger + conditions + actions, with versioning, dry-run, retries and execution logs.
- [ ] Open API with per-user tokens, scoped permissions, webhooks and documentation.
- [ ] GitHub/GitLab, Jira/Linear, Slack/Teams, Google/Outlook email, calendar, Drive/OneDrive and Zapier/n8n connectors.
- [ ] Importers from Notion/Trello/ClickUp/Todoist/CSV/Markdown, with mapping previews and rollback.
- [ ] AI-assisted planning, transcription/meeting actions, project summaries, extraction from documents and duplicate detection.
- [ ] Human review for consequential AI-generated mutations; provider choice, cost caps and data controls.
- [ ] Organization branding, custom domains, dashboard themes, accessibility presets.

### Professional operations and reliability [P0/P2]
- [ ] Centralized structured logging, Sentry-like errors, uptime alerts and transaction tracing.
- [ ] Automated unit, integration, UI, multi-user isolation, backup/restore and migration tests in CI.
- [ ] Versioned database migrations and pre-migration backups, tested rollback/runbooks.
- [ ] Secure deployment templates for local Docker, Portainer Git stacks and image-based deployment.
- [ ] Health and readiness endpoints, bounded worker scheduler and persistent job queue.
- [ ] Search indexing, pagination, bounded query execution and database query monitoring.
- [ ] Feature flags, staging environment, deployment verification and progressive rollout.
- [ ] Data retention, access and export policies, encryption, key rotation and secret management.

## 3. Career-specific workspace template catalog
Common primitives should be configurable, not forked as separate apps. Each template configures fields, views, default task states, intake forms and reports.

| Profession / career family | What MLO should add or preconfigure |
|---|---|
| Software / computer engineering | Issue/bug backlog, sprints/cycles, GitHub PR references, releases, CI links, architecture decisions, incidents, code-review queue. |
| Electrical engineering | Drawing/register revisions, panel/circuit schedules, equipment lists, BOM and procurement tracking, RFIs, site punch lists, inspections, commissioning. |
| Mechanical engineering | CAD/part register, design revisions, ECO/ECN, prototype build, tolerance/test plans, supplier lead times, design reviews. |
| Civil/structural engineering | Project stages, submittals, permits, inspection requests, drawing revisions, issue logs, field observations, subcontractor dependencies. |
| Biomedical/medical device engineering | Design inputs/outputs, traceability matrix, verification/validation, hazard/risk logs, change controls, quality documents and audit trail; never imply regulatory certification. |
| Chemical/process engineering | P&ID document register, HAZOP actions, plant trials, safety reviews, permit schedules, procedures, maintenance actions. |
| Manufacturing/industrial engineering | Work orders, production milestones, equipment maintenance, corrective actions, quality checks, SOPs, changeovers and capacity reports. |
| Aerospace/automotive engineering | Configuration/requirements traceability, tests, issue triage, supplier deliverables, verification gates and release baselines. |
| Data science/ML | Experiment runs, dataset/model registries, metrics, approvals, training schedules, reproducibility checklists, deployed-model maintenance. |
| Research/scientists | Experiment notebooks, hypothesis/experiment register, publication pipeline, grants, ethics approvals, citations, inventory. |
| Architects/urban planners | Client briefs, design phases, approvals, BIM links, site visits, permit checklists, drawing/issues register. |
| Construction/project managers | WBS, Gantt, critical path, RFIs, submittals, field reports, procurement and budget tracking. |
| Skilled trades (electricians/plumbers/HVAC) | Dispatch, work orders, checklists, parts usage, site photos, recurring service, quote-to-invoice and compliance documentation. |
| IT/system administrators | Tickets, asset inventory, change windows, incident logs, maintenance schedules, access reviews and knowledge base. |
| Doctors, nurses and clinicians | Shift planning, training, credential renewal, CME/CPD, checklists and personal admin; patient-specific use only after appropriate compliance/security design. |
| Pharmacists / lab technicians | Inventory, expiry checks, quality processes, SOP updates, staffing and training logs; regulated records require audited workflows. |
| Lawyers / paralegals | Matters, deadlines, client intake, document versions, conflict-check reminders, restricted access and billable time; not a substitute for approved legal case systems. |
| Accountants / auditors | Client engagements, month-end close, recurring checklists, evidence requests, review sign-offs, audit trails, timesheets. |
| Financial analysts / advisers | Research notes, model assumptions, approvals, reports, meeting follow-ups and private client workspaces. |
| Teachers / educators | Curriculum plans, lesson templates, assignment lists, grading checkpoints, parent communication, resources and professional development. |
| Students / graduate students | Courses, rubrics, exams, spaced repetition, grade projections, research logs, thesis milestones and internship applications. |
| Human resources / recruiters | Applicant pipeline, onboarding, training, policy reviews, confidential approvals and employee milestones. |
| Sales / account managers | CRM pipeline, account notes, proposals, activities, quote follow-ups, quarterly targets and forecasting. |
| Marketing / social media | Content calendar, campaign briefs, approval stages, reusable assets, analytics, post-production workflows. |
| Writers / journalists / editors | Story pipeline, sources/references, pitch tracking, editorial calendar, drafts and revision stages. |
| Designers / creators | Asset library, design briefs, proofs, approvals, mood boards, deadlines and client feedback. |
| Video producers / content creators | Shot lists, editing checklist, captions, sponsor deliverables, publishing calendar and performance analytics. |
| Entrepreneurs / freelancers / consultants | Client CRM, proposal templates, project budgets, invoicing, time tracking, deliverables and renewals. |
| Executives / team leads | Goals/OKRs, portfolio dashboard, delegation, blocked-work visibility, decisions and weekly status reviews. |
| Real estate / property management | Leads, listing checklists, appointments, viewings, tenant requests, recurring property maintenance. |
| Hospitality / restaurants / retail | Scheduling, opening/closing SOPs, inventory, incident logs, purchasing and staff training. |
| Logistics / supply chain | Procurement stages, shipment milestones, carrier contacts, delivery exceptions, supplier follow-ups. |
| Government / nonprofits | Grant lifecycle, program outcomes, stakeholder register, meeting minutes, audit logs and reporting. |
| Coaches / personal trainers | Session plans, equipment, booking, exercise templates, program tasks and client follow-ups; careful handling of sensitive health data. |
| Households / families | Joint calendar, groceries, chores, bills, school activities, emergency contacts and private/personal boundaries. |

## 4. Competitor synthesis and opportunities
- **Notion**: Learn from connected databases, customizable pages, templates, relations, backlinks, wikis, forms, AI, calendar ecosystem. Notion introduced offline editing in 2025, so MLO should not claim this is absent; aim for predictable fully supported offline projects/tasks with transparent sync status. Complaints to address include complexity, heavy mobile database UX, limitations in synced external workflows and cumbersome advanced automation.
- **ClickUp**: Learn from deep task/project hierarchy, dashboards, goals, timesheets, automation, approvals and relations. Differentiate by being lighter and quicker for simple individual tasks.
- **Todoist**: Learn from instant capture, recurring natural-language input, filters and cross-platform ease. Differentiate with notes/projects and time logs that feel native.
- **Linear**: Learn from opinionated issue triage, cycles, speed, initiatives, keyboard-first workflows. Differentiate with non-software role templates.
- **Asana**: Learn from portfolios, goals, workload, team tracking and status reports. Differentiate with a seamless personal/team boundary and built-in focus.
- **Airtable**: Learn from structured data, forms, linked records and automations. Differentiate with preconfigured everyday workflows, so users rarely build databases from scratch.
- **Sunsama**: Learn from guided realistic daily planning, task imports, manual timeboxing and end-of-day review. Differentiate with persistent deep project context.
- **Motion**: Learn from automatic time allocation, overload/due-risk warnings and rescheduling. Differentiate by making automation controllable and explainable.
- **TickTick**: Learn from habits, Pomodoro, Eisenhower, calendar, smart reminders and quick capture. Differentiate with serious project collaboration.
- **Obsidian/knowledge apps**: Learn from Markdown portability, graph/backlinks, local/offline operation and flexible knowledge capture. Differentiate with structured task execution and permissions.
- **Microsoft Planner**: Learn from grid/board/Gantt, assignment, dependencies and capacity views. Differentiate with non-enterprise ease of setup and personal productivity.

### Recurring unmet needs from qualitative community discussion
1. A fast, good mobile experience for large task/project databases.
2. Native, dependable, two-way integrations without brittle third-party chains.
3. Simple, well-defined recurrence and agenda/true timeboxing across all task sources.
4. Rich cross-record links with automations and filtered relation access.
5. Plain-language onboarding and role-specific templates that work immediately.
6. Portability: full-fidelity export/import, bulk editing and transparent backups.
7. More direct project execution: workload visibility, focus/timesheets, dependencies.
8. Better notetaking: graph links, mindmaps, annotation/handwriting where useful.
9. More transparent AI, custom choice of providers, cost and privacy control.
10. Quick capture that does not require navigating a heavy document editor.

These are **opportunities**, not claims that every competitor lacks them. Official feature availability changes and often varies by plan; community posts are qualitative signals, not representative market surveys.


### Competitive capability matrix, verified as of October 2026

| Product | Useful strengths verified in product documentation | Not a safe "missing feature" claim | MLO differentiation to pursue |
|---|---|---|---|
| Notion | Linked databases and relations, multiple views, subitems, dependencies, sprints, forms, automations, offline pages, AI search and meeting notes | Offline is **not** entirely absent; Notion added offline mode in 2025. Its scope has limitations: offline pages need caching/download, some advanced blocks need internet, and database download starts with first 50 rows of first view | Fast action-first mobile UX, task-linked timers/time records, guided role-specific workspaces, portable first-class workflows |
| ClickUp | Lists, boards, Gantt, dependencies, workloads, goal dashboards and time tracking | ClickUp is not missing comprehensive project management | Make the everyday interface lighter and give personal, student and household modules first-class status |
| Todoist | Quick task capture, recurrence, filters, calendar integrations | Recurrence and calendars are built in, but unusual recurrence patterns have sync exceptions | Tie actions, subprojects, files, timesheets, study and finances to one shared task engine |
| Linear | Issues, cycles, projects, initiatives, project updates, documents | It already provides serious software project management | Add nonsoftware engineering templates, personal life planning, timers and household workflows |
| Asana | Portfolios, workload, goals, dependency tracking, forms and rules | Asana is strong in cross-functional management | Useful solo and small-team experiences without substantial organizational setup |
| Sunsama | Guided daily planning and shutdown, timeboxing, focus, actual-vs-planned time and integrated calendars | Sunsama already does task-to-time workflows well | Richer underlying projects, documents, professional industry records and private cross-life links |
| TickTick | Habits, Pomodoro, Eisenhower matrix, countdown, quick capture and widgets | Native focus timers and habit tracking exist | Professional collaboration, engineering project planning and relational information |
| Obsidian | Local files, graph view, canvases, rich notes and extensibility | It is not missing interconnected knowledge tools | Native project execution, structured task dependency planning and permissioned collaboration |
| Coda / Superhuman Docs | Integrated tables, buttons, Packs and external app actions | Capable programmability/integrations already exist | Ready-to-use career systems and clear portability without users designing an entire app |

**Evidence:** https://www.notion.com/help/views-filters-and-sorts ; https://www.notion.com/help/customize-your-database ; https://www.notion.com/help/use-pages-offline ; https://www.notion.com/help/notion-ai-faqs ; https://www.notion.com/help/forms ; https://help.clickup.com/hc/en-us/articles/9764027803415-Create-views-for-project-management ; https://www.todoist.com/help/articles/use-the-calendar-integration-rCqwLCt3G ; https://linear.app/docs/conceptual-model ; https://asana.com/features ; https://www.sunsama.com/features/timeboxing ; https://ticktick.com/features ; https://obsidian.md/help/plugins/canvas ; https://coda.io/product/packs .

**Qualitative community signals, not survey statistics:** https://www.reddit.com/r/Notion/comments/1vd8mj6/ highlights relations/synced blocks; https://www.reddit.com/r/Notion/comments/1rm22u6/ highlights mobile friction; https://www.reddit.com/r/Notion/comments/1s752ei/ highlights capture/retrieval shortcomings; https://www.reddit.com/r/ObsidianMD/comments/1wuvhhk/ highlights interest in native calendar/tasks.

### Example: electrical engineering project workflow
A user creates **Substation Panel Upgrade** from an engineering template. The project includes drawing register, BOM, panel/circuit schedule, procurement list, vendor queries, design calculation references, permit/inspection checklists, commissioning test logs and controlled change requests. A drawing revision automatically creates a review task; an approved BOM change creates a procurement follow-up; the commissioning milestone cannot be marked ready until required predecessor tasks pass their checks. A timer against a design review logs time toward the project. Only authorized collaborators can access controlled documentation. This supplements, and must not falsely claim to replace, CAD, PLM, ERP or engineering approval systems.

### Example: academic and freelance workflows
An engineering student imports courses, creates an ACL rehabilitation capstone project, links literature notes, design milestones, lab sessions and submission tasks, plans study blocks around actual classes, and sees grade impact separately from milestone progress. The same user may have an **Internship Applications** pipeline and a **Freelance Client** workspace; per-space privacy and separate calendars prevent accidental exposure to classmates or clients. Progress and time entry operate consistently across all contexts.

## 5. Product-defining differentiator: effortless adoption, instant utility and a genuinely useful free core [P0]

> **Product promise:** *MLO should work for your life immediately. You should never have to become an expert in organizing software just to become organized.*

This is **not** an extra optional feature. It is a release-blocking product principle applying to every page, module, permission model, onboarding flow, default setting, and future pricing decision. The differentiator is **power without configuration**. MLO must be useful for someone who wants only a grocery list and remain powerful enough for a multidisciplinary engineering manager.

### 5.1 Problem, evidence and accuracy boundaries

Qualitative Notion community discussions repeatedly describe (a) a blank canvas with no obvious first action, (b) videos and hours of template research before accomplishing a simple task, (c) complicated database properties and relations, (d) polished but impractical dashboards, (e) a steep learning curve for beginners, and (f) anxiety about free-tier restrictions. One March 2025 discussion explicitly criticized templates requiring a lengthy tutorial; a June 2025 poster said they had already spent three days researching before feeling productive; another discussion names *blank-page paralysis*. These are meaningful product-discovery signals, **not** representative surveys or proof that a specific number of millions abandoned Notion.

**Verified competitor facts, October 12, 2026:** Notion already offers templates, onboarding suggestions, imports, quick databases, task dependencies, offline support and a substantial free personal plan. It is therefore inaccurate to say it has *no* onboarding or no free features. Its published Free plan includes unlimited pages/blocks for solo workspaces, but 2+ workspace owners trigger a **1,000-block** limit; file uploads are restricted to **5 MB per file**; charts are limited to **one**; and most database automations are paid features. These are specific, checkable constraints that MLO can deliberately avoid for core organization. They may change; reverify before publishing competitor marketing claims.

**Evidence:**
- Community onboarding complexity: https://www.reddit.com/r/Notion/comments/1jcw3y1/ ; https://www.reddit.com/r/Notion/comments/1lhmvig/ ; https://www.reddit.com/r/Notion/comments/1ksq0mp/ ; https://www.reddit.com/r/Notion/comments/1oq2j47/
- Notion official pricing and restrictions: https://www.notion.com/pricing ; https://www.notion.com/help/understanding-block-usage ; https://www.notion.com/help/images-files-and-media ; https://www.notion.com/help/charts ; https://www.notion.com/help/database-automations
- Notion starter templates and import: https://www.notion.com/help/start-with-a-template ; https://www.notion.com/help/import-data-into-notion
- Established interaction-design principles: https://www.nngroup.com/articles/progressive-disclosure/ ; https://www.nngroup.com/articles/recognition-and-recall/ ; https://www.nngroup.com/articles/complex-application-design/

### 5.2 Eight non-negotiable simplicity rules

1. **Value before setup.** Once someone signs in, they can enter a real task, note or event immediately; they are not first required to configure sections, databases, calendars, labels, passwords for external integrations, timers or visual themes. Cloud accounts still require proportionate authentication and data-protection setup.
2. **No blank-screen paralysis.** The first screen always has understandable actions: **Add a task**, **Write a note**, **Plan my day**, **Start a project**, and **Set a reminder**. Include optional sample content in demo mode, but do not insert fictitious tasks into a real account without clear consent.
3. **A task is a sentence, not a form.** Only the title is required. Everything else (priority, deadline, project, owner, estimate, recurrence, attachments) is optional. Natural-language interpretation is a convenience, not a requirement.
4. **Smart defaults beat mandatory choices.** New task -> private Inbox; new note -> personal Notes; new project -> simple Board with To do / Doing / Done; new timer -> default 25-minute focus. All can be changed later.
5. **Advanced does not mean hidden forever.** Offer a clear **More options**, **Customize view**, or **Advanced** entry. A beginner never sees formula builders and dependency graphs by default; a professional can reach them without rewriting the workspace. Avoid more than two levels of progressive disclosure for common workflows.
6. **One action, one connected source of truth.** Enter an assignment once and have it appear in its course, tasks and upcoming deadlines. A focus session automatically links to its parent task if launched there. Eliminate repeated manual cross-linking.
7. **Never punish users for being organized.** No arbitrary count limits for essential personal tasks, notes, projects, basic recurring tasks, calendars, or focus sessions in the proposed free core. Any cloud storage/fair-use restrictions must be visible, comprehensible and based on actual costs, not surprise blocking.
8. **Every complex decision is reversible.** Templates can be removed; sections hidden or shown; records moved; mistakes undone; imports previewed; AI suggestions rejected; data exported. Never make a user rebuild the system to try another workflow.

### 5.3 Three user journeys: immediate, gradual and expert

**Journey A: A total beginner (target: a useful first task within 60 seconds after authentication).**

1. Sign in; MLO automatically creates a private workspace and opens **Today**. No forced multi-page questionnaire or dashboard builder.
2. See a text input reading **What do you need to get done?** with examples underneath, e.g. `Submit the lab report Thursday at 5`.
3. Type something and press Enter. The task is saved in Inbox; when a date is confidently recognized, MLO previews the parsed deadline and allows correction. If ambiguous, it saves the text safely rather than inventing a time.
4. The task appears immediately. The user can check it off, edit it, add another, or close the app. All other modules remain optional.
5. Only after they have actually used a task several times, offer a dismissible tip: *Want to group these into a project?* Never block completion of the main task with training.

**Journey B: A busy person changing from existing tools (target: practical migration in a few guided steps).**

1. Choose **Use MLO right away** or **Bring in my existing work**; the first choice must work without importing anything.
2. Offer understandable import cards: Notion, Todoist, Trello, CSV, Google Calendar, Outlook, Markdown, Apple Reminders (where supported), with exact coverage/limitations and permission requests only when selected.
3. Run a preview: *52 tasks, 3 projects, 8 notes will be created*. Show any duplicates, unsupported fields, date conversion, potential attachments not carried over, and permission boundaries.
4. Let users choose **Keep my old structure** or **Organize it for me**. Automatic classification must be reversible and preserve originals/relations wherever supported.
5. Complete import in a background job with resumability, deduplication keys and a clear progress/error report. Import never overwrites or duplicates silently. Confirm before changing external calendars.
6. Show a useful **Today** view populated from the imported data, and suggest connecting calendars/notifications only when useful and explicitly consented to.

**Journey C: Engineer, professional or power user.**

1. Choose a prebuilt career workspace **or skip it**: Electrical Engineer, Student, Software Developer, Project Manager, Freelancer, Healthcare Admin, Family, etc.
2. A single **Create Project** action generates an immediately usable project overview, task list, notes, calendar and optional domain-specific registers. The user does not design schemas or relations.
3. The default view contains a few meaningful fields. **Advanced planning** exposes milestones, dependencies, resource planning, budgets, quality workflows and custom fields on demand.
4. Crucially, a professional can start with simple Today/Inbox and later add sophisticated controls without migrating data or replacing the original project.

### 5.4 Progressive complexity: the same data, three levels of interface

**Personal / Simple (default):** Today, Inbox, Projects, Calendar, Focus, Notes. Tasks show title, completion control, date and optional list/project. Project creation asks only **name**, with optional default status and deadline. This is the initial experience for *everyone*, regardless of occupation.

**Organized / Guided:** Show priorities, subtasks, recurring tasks, saved filters, daily planning, templates, goals, basic reports and shared lists. Promote these features only when users have relevant needs; optional **Customize navigation** controls what remains visible.

**Professional / Advanced:** Add dependency management, Gantt, portfolio management, resource allocation, custom fields, engineering registers, structured documents, approval workflows, advanced automations, analytics and permissions. The feature set is configurable per workspace, but the core records and APIs remain the same.

**Important technical rule:** do not create three distinct database implementations. Use shared `tasks`, `projects`, `notes`, `time_entries` and related tables; modes should control **presentation and default workflows**, not access to users' own data or data portability. A person can switch modes at any time without losing work. Avoid feature overload even in Advanced mode by grouping tools by task.

### 5.5 Zero-setup experiences, by module

| Module | First action available with zero configuration | Advanced capability revealed later |
|---|---|---|
| Tasks | Type one task into a single field; it lands in private Inbox | Custom statuses, recurrence, dependencies, rules, multiple assignees |
| Projects | Name the project; automatically get a task list and simple board | Milestones, Gantt, budget, custom fields, risk/issue register |
| Timer | Press **Focus 25 min** from Home or a task | Pomodoro cycles, stopwatch, billing, time approvals, analytics |
| Calendar | See MLO deadlines/events immediately | Two-way external sync, scheduling rules, availability and timeboxing |
| Notes | Press **New note** and type; autosave begins | Tables, backlinks, databases, templates, AI and collaboration |
| Study | Add a course or a deadline; useful defaults appear | Grade weights, exam plans, flashcards, project labs and analytics |
| Work | Create an application, client or job task | Career templates, issue queues, CRM, approvals and reports |
| Home | Add groceries/chores as simple lists | Shared household assignments, inventory and budgets |
| Finance | Add an expense or a monthly bill | Imports, categories, budgeting, reconciliation and projections |
| Notifications | Save a deadline without installing another app | Offer browser push, email or ntfy connection at first relevant reminder |
| Collaboration | Start private; choose **Share** on an individual project or list | Team roles, invitations, comments and approval rules |

**A feature is incomplete if using it requires prior learning of databases, custom fields, formulas, templates or automations.** Those constructs should make expert workflows better, not be prerequisites for basic usage.

### 5.6 Quick capture as the primary user interface

Implement **one global Add control** on desktop and mobile, usable from every screen. Initially display a compact field and five common content types; reveal advanced details only after entering text or tapping **More**. Learn from Todoist's real quick-add affordances, but keep understandable clickable actions for people who do not know shortcuts.

- **Simple deterministic input first:** `Pay electricity bill Friday`, `Finish design report Oct 21`, `Buy milk`, `Meeting notes`. Confidence-based date parsing with clear previews. Do not hallucinate deadline/date for ambiguous phrases or assume locations/permissions.
- **Smart destinations with no setup:** typed tasks -> Inbox by default, draft note -> Notes, text attached to a task -> task comments/notes; suggestions use current context (e.g. while viewing a course, suggest that course).
- **Mobile-first capture:** thumb-reachable floating Add button; large touch targets, soft keyboard handling; clipboard/share-to-MLO and quick phone widget as supported; optional microphone capture after permission granted; no forced AI/account-provider connection.
- **Keyboard-first speed:** `Q` for quick task, `/` for global search, natural-language due dates, Enter to save and Esc to close; all functions also fully operable without shortcuts.
- **Smart Inbox cleanup, not forced sorting:** Later offer **Organize my Inbox** to group related tasks. Show a preview and undo; never silently relabel, move, erase or publish content.
- **Instant feedback and reliability:** Update UI optimistically, but indicate pending/saved/failed state. Never show successful saving when storage failed. Support offline queuing and recovery when implemented.

**Reference:** https://www.todoist.com/help/todoist/features/use-task-quick-add-in-todoist-va4Lhpzz . Todoist supports fast capture and natural-language details; MLO should borrow the principle, not assert it is missing elsewhere.

### 5.7 Integrating into existing lives rather than forcing a new routine

- **Don't require app switching immediately.** Bring selected calendars, files and task sources in through explicit imports or connector sync; give a readable mapping, provenance and ability to unlink. Integration is optional.
- **Don't force a “productivity philosophy.”** Let users organize by Today, Project, Course, Area, Client, or simple list. Support personal, work, school and household in one account with private boundaries.
- **Make reminders channel-agnostic.** Start with browser/in-app reminders if feasible; support opt-in email, ntfy and push. Do not ask for device permissions during registration; ask contextually when the user creates their first reminder.
- **Use familiar words.** Prefer Tasks, Projects, Notes, Calendar and Share instead of mandatory terms such as Relations, Rollups, Properties, Views and Databases; advanced terminology remains in advanced configuration.
- **Helpful defaults with no fake automation:** Real task deadlines populate Upcoming. Daily overview reflects actual work. Missing information is marked missing. Don't invent a routine, project phase or financial category and present it as fact.
- **Accessibility is ease of use.** Support readable typography, clear color contrast, screen reader labels, keyboard navigation, reduced motion, plain language and low-bandwidth/mobile experiences. Never rely on an animation or color alone to teach a feature.
- **Contextual teaching only:** short, dismissible, just-in-time hints; no 20-step forced tutorials. Offer **Show me how**, **Undo**, and **Skip** consistently. Advanced help should have concise visual examples, not require watching a YouTube course.

### 5.8 Free-access charter: protect essential utility and trust

**Recommended promise:** *MLO's personal organization core stays genuinely functional for free; paid plans, if any, fund infrastructure-heavy and enterprise services.* This is a **proposed MLO policy**, not a claim about how MLO currently charges or a legally guaranteed lifetime commitment. Publish a stable policy before launch and be transparent about changes.

| Feature | Proposed free core | Appropriate potential paid add-on (only if needed) |
|---|---|---|
| Tasks, subtasks, lists and projects | Unlimited essential personal records; recurring tasks, basic dependencies and views | Advanced organization-wide portfolio/resource analytics |
| Notes and documents | Unlimited text notes, tags, backlinks and ordinary export | High-cost hosted storage, advanced enterprise retention/search |
| Calendar and reminders | MLO calendar, deadlines, basic reminders, common calendar connections subject to provider terms | High-volume notification sending, team-wide scheduling services |
| Timers and time entries | Unlimited Pomodoro, stopwatch, focus history and personal reports | Team timesheet approvals, organizational billing/payroll integrations |
| Personal dashboards and filters | Customizable personal Today/dashboard, saved filters and useful charts | Cross-company BI reporting, managed data warehouse/reporting |
| Collaboration | Essential household/project sharing with reasonable anti-abuse safeguards, no tiny arbitrary content cap | Managed large organizations, advanced admin/security/compliance |
| Templates and careers | Built-in personal, student, work and major career templates free | Optional bespoke implementations/training, not the ordinary templates |
| Integrations and portability | Manual import/export, open formats, selected low-cost standard integrations | Expensive continuously hosted premium provider sync where necessary |
| AI | **Not required** for core tasks, projects, scheduling or search | Costly LLM processing with explicit opt-in, quotas and visible usage charges |
| Offline/local access | Basic local access and export; robust offline edit/sync when safely implemented | Hosted high-availability/SLA offerings, not offline access itself |

**Fairness and sustainability safeguards:**
1. **Never lock existing user data behind a subscription.** Viewing, ordinary editing and exporting user-created personal data should remain available even if a paid subscription ends; exceptionally large paid-only storage can use a clearly published grace period and safe export path.
2. No surprise payment screens after a user builds 50 tasks or adds a second personal project. Don't deliberately cap useful habit formation.
3. Avoid opaque hidden workspace-size traps. If cloud files or outbound email/SMS cost real money, publish storage/bandwidth/notification quotas **in advance**, with ample warnings, compression, local-file options and export. Do not promise literally unlimited free cloud bytes or SMS.
4. Basic reminders should not require an externally billed AI agent. Server-side scheduled rules handle them.
5. **Optional self-hosting** can provide low-cost power use where practical, but document security, backups, domain/HTTPS and upgrade responsibilities; do not claim self-hosting has zero cost or risk.
6. Organization pricing, if introduced, should be for objectively incremental value: enterprise SSO, provisioning, organizational audit/retention, dedicated hosting, priority support, advanced enterprise permissions and cost-intensive AI/transcription.
7. Monetization must not punish accessibility features, password recovery, personal backups or security essentials. Maintain a clear distinction between free baseline security and enterprise-specific compliance needs.
8. If a product feature must change tiers, give advance notice, preserve export and ordinary access, and never disguise a technical failure as a payment requirement.

**Principle:** Free should mean *you can actually organize your personal life*, not *you can try organizing your life until the system becomes useful*.

### 5.9 Concrete UX details and sample copy

**First screen (after signup):**

```text
Welcome to MLO.
What do you need to get done?
[ e.g. Finish the report Friday at 3 PM                 ] [Add]

Or start with:  [New project]  [Write a note]  [Start focus]  [Plan today]

Nothing to configure. Change your setup anytime.
```

**First project dialog:** `Project name` (required); optional `deadline` and `starting layout`; **Create**. Initial sections and progress view are generated automatically. Advanced project settings should be reachable in the project, not required up front.

**First task dialog:** `What needs to be done?` (required); optional date chip and project chip. The Edit details surface can expose due date vs scheduled date, priority, checklists, time estimate, people and attachments only when needed.

**When a user asks for a harder feature:** `Need to track phases and dependencies? Turn on Advanced Planning for this project. Your current tasks will stay exactly where they are.` The action must be reversible.

**When suggesting an integration:** `Connect your calendar? This will show your events next to tasks. You control what MLO can access. Skip for now.` Ask for minimum scopes and provide disconnection and sync status.

**When explaining free plans:** `Your personal tasks, projects, notes, and focus timers stay available for free. Hosted storage and optional team/AI services may have clearly displayed limits.` Show real limits *before* users encounter them.

### 5.10 Metrics and research plan: prove ease of use

Targets below are **proposed acceptance criteria**, not measured results or guarantees. Instrument privacy-preserving aggregate events without collecting task titles, document text, health data, payment data or personally identifying content.

| Measure | Proposed initial acceptance target | Validation method |
|---|---|---|
| First-value time | Median **≤60 seconds** from authenticated first load to creation of one real task, event or note | Instrumented onboarding funnel and moderated tests |
| Mandatory setup time | **0 seconds** for tasks, notes, projects, timers and in-app calendar | Automated fresh-account end-to-end test |
| Basic task creation | **≤2 deliberate interactions** after opening quick-add, plus text input | Usability walkthroughs across mobile/desktop |
| First project setup | **≤3 required interactions** plus typing a project name | First-time-user testing |
| Beginner unassisted success | **≥90%** of test participants can add, find and complete a task without training | Representative moderated usability tests |
| Task action speed | Visual acknowledgment <100 ms, truthful saved/failed state | RUM/performance traces with network failures |
| Setup abandonment | Reduce the share of new users who leave before first useful action; benchmark first | Cohort retention and funnel analysis |
| Reorganization without loss | 100% of mode/theme changes preserve user task IDs and content | Migration/switch-mode automated tests |
| Free core parity | All documented free-core features usable in test free account | Automated entitlement matrix in CI |
| Transparent import | Every supported importer produces a record-count and failure summary; can resume without duplicate records | Fixture imports with partial failure injection |
| Accessible basic path | WCAG 2.2 AA-oriented tests, keyboard-only basic workflows and screen-reader checks | Automated + manual accessibility tests |

**User testing sample:** begin with novice users, users who abandoned Notion or another complex tool, heavy workload professionals, students, mobile-only users and accessibility participants. Ask them to accomplish concrete goals without a tutorial, rather than rate an impressive dashboard. Compare a blank account with a guided-but-skippable account and measure confusion, time and completion. Test 5–8 people per major experience as a formative starting point, then larger groups before making quantitative generalizations.

### 5.11 Implementation and architectural work needed

**P0: Simple-by-default infrastructure and first-use experience**
- Auto-provision private Inbox, Projects, Notes, Today and default preferences server-side at account creation. Make provisioning idempotent for retries and migration, with no fake personal records.
- Universal quick-add API and small, shared task-create component. Title required, other fields nullable/defaulted. Return the created record with stable ID; optimistic UI must reconcile failures.
- Minimal Today dashboard and context-sensitive empty states. Hide irrelevant tools by default, never hide essential navigation behind learning a gesture.
- Explicit data contracts for task/project/note creation, permission-scoped reads, calendar derived events and notification defaults. Centralized ownership.
- Automated free-tier entitlement tests, stable export formats and transparent usage meters for truly costly hosted services.

**P1: Guided expansion and migration**
- Optional role-based starter presets; each template must generate *usable real objects*, not just a colorful blank dashboard. Safe uninstall/hide without deleting user work.
- UX capability flags (simple/guided/advanced) stored as preferences only, not separate underlying records. An individual project's advanced mode can override personal defaults.
- Imports for CSV, Notion export, Todoist export, Markdown and calendars with previews, ID maps, conflict handling, provenance and duplicate detection; publish known limitations.
- Contextual tips, accessible Learn/help center, action-oriented search and reversible bulk actions.
- Built-in common schedule/reminder automations using deterministic logic; avoid making AI mandatory.

**P2: Embedded assistance and advanced automation**
- Optional rule-based organizing suggestions and explainable AI assistant using scoped access; suggestions are previews until approved.
- Interoperable external sync with retry and conflict states, progressive permission prompts and manual fallback.
- Continuously verify performance on low-powered Raspberry Pi hardware and budget mobile devices; a beautiful onboarding screen is not success if the app is sluggish afterward.

### 5.12 Release-blocking acceptance scenarios

1. A new user creates a task and starts a focus timer **without ever visiting Settings**.
2. A user creates a project, then a task, sees it in Today/Upcoming where appropriate, and finishes it on a phone **without constructing any database**.
3. An engineer adds an advanced dependency to an existing simple project with **no project recreation**.
4. A family member accepts an invitation and sees **only explicitly shared lists/projects**, not the inviter's private personal records.
5. A user can ignore role templates, AI, calendar connectors and notification integrations indefinitely and still get real value.
6. A free user can create many ordinary tasks, projects, notes, reminders and timers **without triggering a surprise content-count paywall**.
7. A user on a slow or unreliable connection sees exact save/sync status and can recover a failed mutation without duplicate records.
8. A user can export all ordinary personal tasks, projects, notes and time logs in open documented formats without purchasing a plan.
9. A new user can discover task creation, completion, due date editing, focus and calendar without tutorial videos or keyboard-only shortcuts.
10. The app uses a single data model across Simple, Guided and Professional modes, and automated tests prove changing modes cannot erase work.

**Strategic positioning:** *More powerful than a simple to-do list. Much easier to start than a configurable workspace builder. Useful for free, customizable forever, and professional when you need it.*

## 6. Concrete architecture plan
One consistent domain model, not separate lists that duplicate records:

`users -> memberships -> workspaces -> areas -> projects -> tasks -> task_occurrences`  
`goals -> projects`  
`tasks <-> task_dependencies / task_links / reminders / time_entries / attachments / comments`  
`projects <-> notes / documents / milestones / files / budgets / risks`  
`calendars -> external_connections -> sync_mapping / sync_events`  
`notifications -> per-device subscriptions / delivery_attempts`.

Use UUID or stable external IDs for offline-created content; timestamps and optimistic version numbers for conflicts. Centralized authorization and row-scoped queries must wrap all modules. Preserve existing record IDs with mapping during import/migration. PostgreSQL becomes attractive with larger concurrent multiuser collaboration; SQLite with WAL remains reasonable for a personal single-node system with strict writer discipline. Never run the same recurring scheduler in every Uvicorn worker; use a dedicated job process or lock/lease. Create REST/JSON endpoints and reusable UI components while keeping existing FastAPI if practical.

## 7. Performance and responsiveness implementation plan
**Measure first:** Lighthouse/PageSpeed and Chrome Performance traces; p50/p95 server response time; SQL count and time per route; real-user LCP, INP, CLS; app interaction latency; payload weight on weak mobile; timer correctness after background/resume.

**Immediate low-risk fixes:**
1. Avoid full-page form POST -> redirect -> full page for frequently used operations; return JSON/HTML fragments and update the local view optimistically with rollback on failure.
2. Avoid per-request redundant database reads for sidebar sections, active timer and user data; cache with invalidation or coalesce in one query where appropriate.
3. Index all frequent filters/sorts/foreign keys, including `(owner_id, status, due_at)` on tasks and `(project_id, position)` on boards; use query plans, not blind indexes.
4. Use server-side page limits and cursor pagination for long activities, tasks and transaction lists; virtualize only if needed.
5. Remove expensive full-page reloads for toggles, archive, status, sorting and quick add; reduce DOM replacement and layout shifts.
6. Cache fingerprinted static assets; enable gzip/Brotli; defer unrelated JS; lazy-load heavy editors/charts and images.
7. Keep timer display client-side from absolute timestamps; reconcile with server state, not a server round-trip every second.
8. Lazy-load inactive mobile panels; keep bottom navigation simple, touch targets comfortable, prevent horizontal overflow.
9. Precompute/cache dashboards with invalidation and bounded queries; no background work on page render.
10. Load-test on the actual Raspberry Pi/Portainer host at expected concurrent users, RAM and storage.

**Scale-up reliability:**
- Split reminders/exports/transcriptions/sync into durable background jobs; retries, dedupe IDs, worker visibility.
- Paginated API with ETags, idempotent mutations and per-user cache keys.
- Offline queue + sync endpoint, conflict-resolution UX, schema migrations and network recovery tests.
- If SQLite writes become a bottleneck, assess Postgres using measurements; avoid premature infrastructure complexity.
- Add structured tracing, regression budgets and accessibility/mobile tests in CI.

**Suggested product targets, not measured baselines:** first meaningful interaction under 1 second on typical warmed views where feasible; task checkbox feedback under ~100 ms; LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1 at the 75th percentile; reliable sync/notification processing with transparent retry state. Verify these on real devices.

## 8. Recommended execution order
**Phase 0: Reliability / safety AND instant usefulness:** inspect deployed version, backups, isolation of accounts, CSRF/session security, notification isolation, test and rollback coverage, deployable image for Portainer. Also create an auto-provisioned private workspace, immediately usable Today/Inbox, simple first task, free-core entitlement tests and accessible mobile onboarding. Do not add sensitive shared functions before this passes.

**Phase 1: Unified objects with progressive disclosure:** data model + migration, unified tasks, areas, projects, task lists, multiple task views, reminders, consistent global search, one-field Quick Add, zero-configuration project creation and switchable advanced project tools.

**Phase 2: Planning / focus:** task-linked timers, timesheets, calendar views and integrations, timeboxing, habits, workload, actionable dashboard, saved filters.

**Phase 3: Knowledge / professional templates / import:** notes, linked records, attachments, tables, engineering project templates with no setup required, import previews and safe migration, forms, project risk logs, reports.

**Phase 4: Smart and collaborative layer:** roles, client views, automation, two-way integrations, AI with opt-in permission model, offline sync, deeper dashboards.

**Phase 5: Advanced product depth:** portfolio resource optimization, mindmaps/whiteboards, role-specific specialized registries, public API and possible plugin marketplace.

## 9. Definition of done for an integrated user journey
A new user signs up; a private workspace, useful Today screen and Inbox are auto-created; they immediately enter a real task without configuring anything. Career templates (Software Engineer, Electrical Engineer, Student, or Personal) are entirely optional; if chosen, they generate a usable workspace rather than a blank database. The user creates a project with just its name and breaks it into tasks; the deadline appears in the combined calendar; they choose available time, start a focus timer from the task, log time automatically, attach notes/files, update status on phone while offline, and see the same state and related dashboards when back online. Collaborators see only granted projects, and reminders reach only devices assigned to recipients. All this is verified by automated tests and a backup/restore run.

## 10. Sources and limitations
Official product sources accessed October 2026:
- https://www.notion.com/pricing
- https://www.notion.com/help/understanding-block-usage
- https://www.notion.com/help/images-files-and-media
- https://www.notion.com/help/charts
- https://www.notion.com/help/database-automations
- https://www.notion.com/help/start-with-a-template
- https://www.todoist.com/help/todoist/features/use-task-quick-add-in-todoist-va4Lhpzz
- https://www.nngroup.com/articles/progressive-disclosure/
- https://www.nngroup.com/articles/recognition-and-recall/
- https://www.nngroup.com/articles/complex-application-design/
- https://www.notion.com/product/features
- https://www.notion.com/blog/how-we-made-notion-available-offline
- https://clickup.com/features
- https://www.todoist.com/help/todoist/features
- https://linear.app/features
- https://linear.app/docs/initiatives
- https://help.asana.com/s/article/all-asana-features
- https://www.airtable.com/platform
- https://www.sunsama.com/daily-planning
- https://www.usemotion.com/features/ai-task-manager
- https://ticktick.com/features
- https://obsidian.md/help/plugins/canvas
- https://support.microsoft.com/en-us/planner/compare-microsoft-planner-basic-vs-premium-plans
- https://webkit.org/blog/13878/

Qualitative community feedback used cautiously:
- https://www.reddit.com/r/Notion/comments/1jcw3y1/
- https://www.reddit.com/r/Notion/comments/1lhmvig/
- https://www.reddit.com/r/Notion/comments/1ksq0mp/
- https://www.reddit.com/r/Notion/comments/1oq2j47/
- https://www.reddit.com/r/Notion/comments/1vd8mj6/
- https://www.reddit.com/r/Notion/comments/1rm22u6/
- https://www.reddit.com/r/Notion/comments/1nfl1o3/
- https://www.reddit.com/r/Notion/comments/1i1xl6i/
- https://www.reddit.com/r/Notion/comments/1sdfho2/
- https://www.reddit.com/r/Notion/comments/1qiemub/

**Scope:** It is not possible to enumerate every job title or every missing feature in every productivity application. This is a broad, implementable taxonomy of the high-value capabilities and major professions. Vendor features and pricing change, and source inspection alone cannot establish actual deployed version or performance.
