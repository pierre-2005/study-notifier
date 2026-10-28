# MLO v4 development ledger

Baseline: `6fc0fd97a7085dacad80745973a56dcea8f3e893` (3.7.1).
The complete October 26 handoff, including its historical appendices, was read.
No surviving v4 checkout or published branch was found. This branch reconstructs
and independently verifies the work. It is not yet a released version.

Implemented: guided Budget with five stages and quick edit, transactional cent
validation and revision conflicts, custom categories, draft retention, SQL
transaction pagination, bounded statement worker, persistent rule deletion,
shared rendering/errors/forms, extracted school/career/bills/event routes,
canonical task adapters/API compatibility, editable bills/courses/assessments,
notes Markdown preview and version protection, goal/habit CRUD and local days,
space partial updates and versions, separated grocery views, calendar agenda,
one canonical shared stylesheet and current entry points. Prior static URLs
remain available for installed clients.

Verification so far: 14 new service acceptance tests passed. The first populated
browser review covered 58 routes at desktop and phone widths (116 states), with
no document horizontal overflow or JavaScript errors. Four accessibility issues
were found and corrected; the final re-audit is pending. Historical service
regressions pass except the local OCR fixture, whose Windows runtime setup is
being completed. Synthetic migration/restore suites pass. No live integration
or production verification is claimed.

Remaining release gates: expanded interactive browser and accessibility checks,
all historical tests on the final source, current screenshot review, final
source checks, v3.7.1 upgrade rehearsal, setup/verification/rollback reports,
consistent release version, remote CI including AMD64/ARM64 container checks.
No main merge, image publication, production database or Portainer action has
been performed. The owner retains the existing-stack rollout responsibility.
