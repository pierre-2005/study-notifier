# MLO product and interface research

Research date: October 23, 2026. This review uses public product demos, official help, official mobile screenshots, and first-person reviews. It is not a paid-account usability study or a representative survey. Vendor capabilities below are vendor claims unless identified as directly visible in a demo. Review observations are anecdotes, sometimes about older versions. No competitor code or visual assets were copied into MLO.

## Macro: the strongest reference

Macro's public [Tasks demo](https://macro.com/tasks/) shows a task title, status, priority and people together, with discussion and references beside the working document. The important design choice is keeping the task and its source context close together. Its [getting-started guide](https://docs.macro.com/getting-started) describes keyboard navigation, a command launcher, linking content, preview and split views. These provide a coherent interaction model across different content types.

The [official mobile screenshots](https://apps.apple.com/us/app/macro-app/id6743133649) show a dark, compact inbox with small type, subdued separators, an amber Signal/Noise switch, and a persistent bottom action rail. The second screenshot presents work through linked content rather than independent dashboards. Dense desktop tools can be effective, but mobile needs a clearer hierarchy and fewer simultaneous panes. Macro's [Apps guide](https://docs.macro.com/apps) distinguishes desktop splits from a single mobile block and limits some shortcuts to desktop.

Visible App Store feedback praises convenience and responsiveness to feedback. Other reviewers describe difficult creation/deletion, clipped layouts and nonworking iPad shortcuts. The listing showed only ten ratings when checked; these are specific failure examples, not prevalence estimates or claims about the current release. The MLO response is testable: visible creation controls, contained horizontal board scrolling, keyboard alternatives to dragging, and browser checks at phone/tablet/desktop widths.

For MLO, this means a contextual task inspector, shared task state across views, source evidence alongside outline edits, and persistent server-side preferences. It does not justify adding chat, email, a code editor, calls or a CRM just to resemble Macro. MLO's existing calendar, tasks and notes already cover the requested workflows. Its permissions remain explicit even where competitor collaboration defaults differ.

## Notion

Notion's [subtask/dependency guide](https://www.notion.com/help/guides/tasks-manageable-steps-sub-tasks-dependencies) and [current help](https://www.notion.com/en-gb/help/tasks-and-dependencies) show indented child records, disclosure arrows, property columns, timeline dependencies and several views of one database. The linked official screenshot was inspected: neutral canvas, restrained status color, small inline metadata, and horizontal timeline bars. Parent/child and prerequisite relationships are distinct.

First-person discussions about [sorting subtasks](https://www.reddit.com/r/Notion/comments/173szea) and [combining Notion with dedicated task tools](https://www.reddit.com/r/Notion/comments/13qzmd2/anyone_here_use_notion_for_project_management_but/) illustrate configuration and daily-execution friction. They do not establish that Notion is unsuitable for projects. MLO should offer useful defaults, nested tasks without database configuration, and consistent completion rules. It should not introduce a generic formula/database builder into a release focused on personal organization.

## Muse from Meta

Meta's [announcement](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/) describes work continuing in the background, explicit connection access, activity history, and approval before sensitive actions. Its official [App Store screenshots and reviews](https://apps.apple.com/us/app/muse-from-meta/id6760173601) were inspected. The interface uses a light canvas, familiar chat bubbles, generous spacing and embedded document cards. The demonstrated interaction moves from an artifact to a proposed action and then a visible result.

Some reviewers praise organization, remembered preferences and getting work done; another reports incorrect retrieved information and repeated correction. These are individual experiences, not a comparative accuracy benchmark. For MLO, the useful lesson is to show source evidence, uncertainty and a reviewable action. The importer therefore keeps AI optional, unselects AI suggestions by default, and requires an explicit reviewed commit. MLO does not claim autonomous agent parity or silently give AI calendar credentials.

## Other useful references

| Product and primary source | Interface/workflow lesson | MLO decision |
| --- | --- | --- |
| [Linear](https://linear.app/features) | Restrained dense lists, predictable status and project structure | Keep metadata compact and status changes consistent; avoid adding issue-tracker jargon to personal tasks |
| [Todoist](https://www.todoist.com/help/todoist/get-started/get-started-with-todoist-OgNNJR) | Immediate capture and progressively revealed task details | Preserve quick capture and keyboard access; expose fuller editing in context |
| [Sunsama](https://www.sunsama.com/) | Calm daily planning with tasks beside calendar commitments | Keep Today and Calendar connected; defer automatic study-block scheduling until conflict/undo rules are designed |
| [Coda connected views](https://help.coda.io/hc/en-us/articles/39555897467021-Create-connected-table-views) | Several views over shared records | Course assessments create real tasks, not a disconnected second task system |
| [Obsidian](https://obsidian.md/) | Linked notes and user control over information | Preserve export and existing attachments; add personal note-review reminders |
| [Anytype](https://anytype.io/faq/) | Strong ownership/offline emphasis | Preserve private ownership and explicit sharing; do not describe server-hosted MLO as local-first or end-to-end encrypted |
| [AFFiNE](https://affine.pro/) | Flexible documents and spatial work | Use source-and-edit panels where they help; defer a general whiteboard/editor platform |

## Applied design and scope decisions

The branch adds a shared neutral shell, coherent form surfaces, six palettes with independent light/dark modes, readable action colors, responsive board columns, keyboard move controls, mobile navigation focus handling, and reduced-motion support. The task inspector avoids losing the project context. The course importer uses an editable assessment list beside private extracted evidence. Empty dates stay unscheduled. Navigation and dashboard preferences retain existing custom labels and ordering.

Redundant global task entry in the New menu was removed while quick capture remains available in task contexts. Footer version/promotion text and repeated introductory copy were reduced. Global legacy notification controls appear only when that compatibility system is explicitly enabled for its bound owner. Study, Tasks and Calendar are views of the same imported tasks. Existing legacy academic/finance records retain their source systems and their original installation owner; there is no silent data conversion into another user's records.

The complete v4 information-architecture/editor rewrite and automatic study-block scheduler remain a separate major project. This branch brings forward the requested course importer and substantial shared UI work, but does not pretend that every future feature or every native device has been verified. Next design work should use real MLO user sessions to measure capture time, task discovery, import corrections and mobile completion. A sweeping framework replacement should follow those findings and preserve the same data, OAuth and deployment contracts.
