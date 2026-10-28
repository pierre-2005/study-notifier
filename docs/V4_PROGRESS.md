# MLO v4 completion ledger

Baseline: `6fc0fd97a7085dacad80745973a56dcea8f3e893` (3.7.1).
The full October 26 handoff, including historical appendices, was read.
No surviving v4 checkout or published branch was found. The implementation was
reconstructed from verified main and saved durably in PR #3.

Implementation complete: guided five-stage Budget and quick edit; atomic cent
validation/revisions; hidden/custom/movable categories; draft retention; SQL
Finance pagination, persistent rules, bounded parsers and CSV protection;
shared rendering/forms/errors; extracted record routes; canonical task/API
adapters; bill/course/assessment/event editing; notes preview/save/versioning;
goal/habit CRUD; separated space/grocery views and settings; calendar agenda;
canonical CSS/current entry points; data/ACL/old asset compatibility;
additive schema/online backup and actual v4 PWA preview assets.

Local verification complete: all 31 historical scripts, 17 new service tests,
236 populated route/width states, 97 new and 47 inherited accessibility scans
with zero violations, no JavaScript errors, and exact-v3.7.1 synthetic migration
and restore. The initial full run found three accessibility issues; the affected
suite and PWA/source checks passed after correction. See V4_VERIFICATION.md for
the precise sequence and limits, and V4_SCREEN_REVIEW.md for all reviewed routes.
Setup, email/calendar/AI/phone guidance, migration provenance, deployment and
rollback reports are included. Version/cache/Compose/publication target agree
on 4.0.0. Historical screenshot evidence and compatibility assets are retained.

Final remote release gate: the current PR head must pass the full 34-script
Linux regression suite and AMD64/ARM64 container build/start. Check PR #3 for
its actual status. Merge/publication is a separate release action. No production
server, database, DNS, keys, volume or Portainer action was taken. The owner
handles actual-backup rehearsal, live integrations and existing-stack rollout.
