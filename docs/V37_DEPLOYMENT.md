# v3.7 release-candidate deployment and rollback

Status: candidate only. Do not merge, publish a candidate image, change the Portainer stack, or migrate the production database until verification and the owner's explicit approval. This work has not done those actions. The feature branch retains PR #1 as a draft.

## Preserve the installation contract

Keep the original Portainer stack name, `study_notifier_data:/data` mapping, `/data/study_notifier.db`, attachment directory, loopback port `127.0.0.1:8001:8000`, reverse proxy/domain, public URL and registered OAuth callbacks. Preserve `APP_USERNAME`, `APP_PASSWORD`, `SESSION_SECRET`, `MLO_CREDENTIAL_KEY` and all existing provider credentials. Do not recreate accounts or rotate keys as part of this update. Existing password hashes, approvals and capability settings remain in place. Legacy finance/academic records are bound to the original bootstrap owner, not all administrators or a newly created account.

The existing main-triggered, multi-architecture GHCR build workflow remains the publishing path. The prepared image and Compose reference are `ghcr.io/pierre-2005/study-notifier:v3.7.0-rc1`. This tag has not been built/published by this work. Branch validation runs tests only. Before approval, record the running stable image digest and keep it available for rollback. Avoid overwriting the previous stable tag.

## Rehearse against an actual backup first

1. The operator should make a consistent SQLite online backup of the installation and a separate backup of attachments and the current stack settings. Keep these private. A raw copy of a live `.db` can omit WAL transactions; use SQLite's backup API or a stopped application snapshot.
2. Bring a copy to an isolated staging host. Keep outbound networking disabled for the initial rehearsal. Do not point the test process at the live database or mount the live volume.
3. Install the candidate dependencies, including Poppler and Tesseract. From the candidate checkout run:

   ```sh
   python -m scripts.rehearse_v37 \
     --source /private/backups/mlo.sqlite \
     --work-dir /private/staging/v37-rehearsal \
     --legacy-owner-username ORIGINAL_BOOTSTRAP_USERNAME
   ```

   The work directory must be empty. The source opens read-only; the script creates an online baseline backup, a migrated staging copy and a restored copy. It checks integrity, foreign keys, repeated initialization, preservation of every original column and restoration equality. It disables the scheduler and calendar auto-sync before importing application modules. Review `report.json`; failures require investigation on a copy. This was verified with representative legacy fixtures, not your actual database.
4. Start staging against `staging.sqlite` with `MLO_SCHEDULER_ENABLED=false` and `MLO_CALENDAR_AUTO_SYNC=false`. Keep private credentials and queued mail inaccessible to unintended recipients. Test account approvals, private records, shared viewers/editors, Finance, exports, uploads and layout preferences. Do not reuse production notification destinations for acceptance traffic.
5. After offline acceptance, use controlled test accounts/mailboxes/calendars to verify real SMTP, Google and Microsoft connect/refresh/read/create/edit/delete, ICS imports and ntfy delivery. Preserve existing OAuth callback entries; add a separate staging callback only through the normal provider administration process. Check multiple accounts and disconnect behavior. Document actual provider results separately from mocks.
6. Run all regressions using `python -m pip install -r requirements-test.txt`, `python -m playwright install chromium`, then `python scripts/run_regression.py`. Install `axe-core@4.14.0` as a test dependency and set `MLO_AXE_PATH` to its `axe.min.js` for accessibility checks. `MLO_BROWSER` optionally selects an existing Chromium executable. Do not skip failures because another version passed.

## After verification and explicit approval

Review the candidate screenshots and remaining gates in [V37_VERIFICATION.md](V37_VERIFICATION.md). Obtain approval of the tested commit and deployment window. Only then merge through the normal workflow, wait for the image build, verify its immutable digest and ARM64/AMD64 manifests, and update the existing Portainer stack to that digest/tag. Retain the existing volume and all environment values. Startup creates and checks a pre-v3.7 online snapshot before additive initialization; that automatic snapshot supplements the operator backup.

Monitor `/health`, application logs, login, one legacy record, one ordinary member, calendar connections and controlled reminder delivery. New mail configuration is described in [V37_EMAIL_SETUP.md](V37_EMAIL_SETUP.md). AI extraction remains disabled unless explicitly configured with a model and API key; local extraction works without it. Run one application/scheduler worker per database. Notifications use leases and successful-delivery records, but a provider accepting a request just before a crash can still produce an at-least-once retry.

## Rollback

Before users resume writes, stop the candidate, retain its database and attachments for investigation, restore the verified pre-upgrade database and matching attachment snapshot into the original volume, and restore the recorded stable image digest. SQLite must be closed while replacing/restoring files; do not leave unrelated WAL/SHM files beside a restored database. Restore permissions/ownership and start the old image with the unchanged keys and configuration. Verify integrity, health and login. Never run destructive down-migrations against the only copy. If users have already written new data, reconcile/export those changes before rollback; restoring an older snapshot would otherwise lose them.
