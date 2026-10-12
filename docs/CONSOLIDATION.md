# v3.1: Legacy-to-modern consolidation map

| Previous screen | New primary entry | Fate of records |
|---|---|---|
| Classic dashboard | Today `/life` | Dashboard shortcut retired; Today includes cross-domain highlights |
| Old To-Do `/todos` | Tasks `/life/tasks` | Imported non-destructively to `life_tasks` with `life_legacy_todo_map`; status mirrored; old data archived in original table |
| Courses `/courses` | Study `/life/study` | Same original records, no duplicate copies. Modern course list still available inside Study |
| Assignments/Exams/Labs `/items` | Study + Calendar | Original assessments remain source of truth; Study/Calendar read them directly |
| Schedule `/schedule` | Calendar `/life/calendar` | Calendar reads original events/classes, no duplicate calendars |
| Class meetings `/classes` and events `/events` | Study/Calendar management | Existing edit/detail/reminder routes retained |
| Finance `/finance` and expenses `/expenses` | Money `/life/money` | Finance transactions/budgets and recurring bill records coexist as distinct data types, with unified navigation |
| Jobs `/jobs` | Work `/life/work` | Original applications and their follow-up reminders retained |
| Your Sections `/sections` | Spaces `/life/spaces` | Existing sharing, groceries, recipes and checklists retained |
| Timers `/timers` | Focus `/life/focus` | Existing timer engine and records; management controls moved to Focus |
| New Projects, Notes, Goals | Same modules and their area contexts | Existing user-scoped records preserved |

## Migration guarantees and limitations

- One-time SQLite online backup with suffix `.pre-mlo-v3.1.sqlite.backup` is created before schema changes, in the same database directory. Attachments need a separate full-volume backup.
- `life_legacy_todo_map` ensures re-running startup does not re-import old to-dos. Deletion sets its task mapping to `NULL` so old records do not reappear.
- Old to-do completion is mirrored into the original row; old data remains intact for existing reminder history. Direct legacy write API endpoints are retained for compatibility but are no longer exposed in navigation. **Avoid using the old endpoints in external scripts** because bidirectional synchronization is not implemented.
- Legacy academic deadlines remain **academic records**, not duplicated generic tasks, but appear in Today and Calendar. If a user manually recreates one as a new task, that is a separate user-created item.
- Career and finance legacy databases have no `user_id` ownership field. Only admin accounts see these records; shared users see private new-project/task records instead. Per-user migration is a separate future project.
- Old detailed forms still use some existing structural markup, though shared visual styles and navigation context have been improved. Rebuilding every specialized form and complex finance workflow as new components remains future UI work.
- Google Calendar integration, offline editing/sync, advanced engineering modules, real-time coediting and automation platforms from the expanded strategy remain roadmap items.
