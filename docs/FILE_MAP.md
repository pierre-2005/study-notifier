# Exact file locations for v3.1

Copy the **contents of the ZIP's `mlo-v3-consolidated/` folder** to the root of your GitHub repository.

| Path | Purpose |
|---|---|
| `app/templates/base.html` | Single consolidated sidebar, mobile dock, command search and quick-add menu |
| `app/life_hubs.py` | New Study, Work, Money, Spaces cross-domain pages |
| `app/templates/life_study.html` | Study home, academic tasks/projects, courses, assessments, class schedule |
| `app/templates/life_work.html` | Work home, projects, tasks, applications |
| `app/templates/life_money.html` | Money home, bills, finance links |
| `app/templates/life_spaces.html` | Spaces home, shared sections and projects |
| `app/templates/life_home.html` | Today dashboard including academic/career/financial highlights |
| `app/templates/life_calendar.html` | Consolidated calendar screen |
| `app/templates/life_focus.html` | Unified focus and existing timer controls |
| `app/templates/courses.html` | Modern course list |
| `app/templates/items.html` | Modern assessment list |
| `app/templates/jobs.html` | Modern job application list |
| `app/templates/expenses.html` | Modern bills/expenses list |
| `app/templates/sections.html` | Modern shared sections list |
| `app/static/life.css` | Consolidated responsive styles and legacy detail/form normalization |
| `app/lifeos.py` | Calendar queries, Today feed, focus timers, index creation and legacy task status mirroring |
| `app/consolidation.py` | Idempotent migration of legacy todos into `life_tasks` |
| `app/backup.py` | New pre-v3.1 SQLite backup |
| `app/main.py` | Startup consolidation, area routers and obsolete screen redirects |
| `app/timers.py` | Timer actions return to the unified Focus screen |
| `app/meta.py` | Release version |
| `docker-compose.yml` | **Only Compose file** used by your current Portainer Git stack |
| `.github/workflows/publish-image.yml` | Automatic GitHub Action publishing multi-arch Docker image |
| `tests_consolidation.py` | New migration/privacy/connected-workflows regression tests |
| `docs/CONSOLIDATION.md` | Exact legacy-to-new module mapping and limitations |
| `docs/DEPLOY_PORTAINER.md` | Your GitHub-to-Portainer update and rollback guide |
| `docs/PRODUCT_SCOPE.md` | Implemented versus future features |
| `docs/VERIFICATION.md` | Verification and known limits |

Other app files are deliberately retained because they contain important finance parsing, course and reminder business logic, custom shared sections, security, databases, imports, files and project behavior. A removed navigation label is not the same as safe deletion of its underlying feature code.
