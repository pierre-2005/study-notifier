# MLO v3.6.1 | Notification device ownership and privacy audit

## Verified behavior

Every `life_devices` record has an `owner_id` tied to `users.id`. The authenticated account identity is derived from `request.state.current_user`, never a user-submitted ID. Device listing is filtered by `owner_id`. The add-device operation always inserts the current account's ID. Device pause/enable and removal now return HTTP 404 unless the device ID **and** current account ID match. Test notifications first fetch by both IDs and reject inaccessible devices with HTTP 404. There is no device-management override for an administrator.

Automatic task reminders explicitly join `life_tasks.owner_id = life_devices.owner_id`; task notifications cannot be routed to another account's registered device topic by the scheduler. Device topics are generated with cryptographically strong random values and uniqueness is enforced in SQLite.

## Hardening introduced in v3.6.1

1. Unauthorized pause/enable and delete operations return 404 instead of silently redirecting. No rows are modified.
2. The older global `NTFY_TOPIC` delivery route is disabled **by default** via `MLO_ENABLE_LEGACY_GLOBAL_NTFY=false`.
3. Even if a server operator explicitly enables the legacy channel, it is disabled when more than one approved active user exists. This prevents automatic classic reminders and digests from broadcasting to a shared topic in a multi-user installation.
4. The Settings test action now directs users to personal device tests; the old global test endpoint obeys the same safety guard.
5. A new real two-account plus administrator test verifies listing, toggling, deletion, test sending, and owner-matched scheduled notifications. This test runs in GitHub Actions before the Docker image is published.

## Security limitations

- An ntfy.sh topic URL is a bearer-like secret. Someone who learns it might subscribe outside of MLO, even though they cannot manage the device through MLO. Public ntfy.sh subscriptions cannot provide strong account-level guarantees. Use private, authenticated ntfy hosting for sensitive messages; never share personal topic URLs.
- A logged-in MLO administrator still has an admin-issued password-reset capability in v3.6. This could be used to take over a member's sign-in, contrary to a *strict* no-impersonation policy. Device route access checks alone cannot prevent an actor who logs in as the user. A future admin role redesign is required to remove that ability.
- The legacy course/finance reminders were not migrated into personal per-user devices. By default, legacy shared-topic reminders are not delivered after this update. Personal LifeOS task notifications continue on account-owned topics; migrate old reminders before expecting them on personal devices.
- No live calls to ntfy.sh were made during testing. Notifications were intercepted in automated tests.

## Installation

For the GitHub → GitHub Actions → Portainer setup, copy the v3.6.1 hotfix files to matching repository paths, including hidden `.github/`, and commit. Wait for the **device ownership** test and the publish job to succeed. Confirm `docker-compose.yml` uses `ghcr.io/pierre-2005/study-notifier:v3.6.1-device-privacy`, preserve the existing `study_notifier_data` volume and port 8001, and redeploy the existing Portainer stack. The Compose file sets `MLO_ENABLE_LEGACY_GLOBAL_NTFY` to false unless explicitly overridden. No database schema changes or new secrets are needed.

For a single-user installation that truly needs the old global reminders, setting `MLO_ENABLE_LEGACY_GLOBAL_NTFY=true` in Portainer will re-enable them **only while exactly one approved active account exists**. This is not recommended for public or multi-user operation.

Back up the Docker data volume before upgrading. A version tag change and code updates are required, but no migration is performed for `life_devices` beyond its already-existing schema.
