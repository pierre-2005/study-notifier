# Deploy MLO Studio v3.6 to your existing GitHub -> Portainer stack

1. **Back up everything under your existing `/data` Docker volume**, including database, attachments, and encryption-key backup. A new one-time SQLite backup is created at startup, but it does not replace a restorable volume backup.
2. Extract the ZIP. Copy the **contents** of `mlo-v3.6` to the **root** of `https://github.com/pierre-2005/study-notifier.git`, including hidden `.github/workflows/publish-image.yml`.
3. In Portainer's existing Git stack, preserve port `127.0.0.1:8001:8000` and the exact current `study_notifier_data` volume. **Check your actual volume name** because Compose stack names can prefix volumes.
4. Keep `SESSION_SECRET`, `MLO_CREDENTIAL_KEY`, Google/Microsoft OAuth credentials and all other existing Portainer variables unchanged. The Compose file now supports optional `MLO_SMTP_*` variables.
5. Commit changes to `main`. Wait until GitHub Actions tests pass and the ARM64/AMD64 image `ghcr.io/pierre-2005/study-notifier:v3.6-account-security` is published successfully.
6. Choose **Pull and redeploy** on the existing Portainer Git stack, not a second stack. Ensure the image is fetched from GHCR.
7. Everyone signs in again after the session-version upgrade. Check the admin Users page, Account security link, new signup email, Projects and Google Calendar.
8. Test an administrator-issued temporary password on a disposable member account, verify forced password change, and verify an old session is rejected. Do NOT use your own primary admin account as the test target.
9. Configure SMTP (if desired) and test verification then forgot-password flow with a real mailbox. Never commit your working `.env` or SMTP password to GitHub.
10. Test one full volume backup restore to staging before any major public rollout.

## Optional new Portainer environment variables

| Variable | Example | Meaning |
|---|---|---|
| `MLO_SMTP_HOST` | `smtp.example.com` | SMTP mail server, blank disables email recovery |
| `MLO_SMTP_PORT` | `587` | SMTP submission port |
| `MLO_SMTP_STARTTLS` | `true` | Require STARTTLS when configured |
| `MLO_SMTP_USER` | service-specific login | SMTP username |
| `MLO_SMTP_PASSWORD` | secret | SMTP credential, keep private |
| `MLO_SMTP_FROM` | `MLO <noreply@overvault.ca>` | Sender address; must be authorized by provider |

**No new external API billing is required to operate manual administrator resets.** Transactional email delivery may have provider-dependent charges or quotas. The core password/reset and account schema changes do not require a separate database or new stack.

## Important differences from v3.5

- `APP_PASSWORD` is now bootstrap-only, not a reset mechanism. Use Account security or an administrator-issued reset afterward.
- A `pre-mlo-v3.6.sqlite.backup` snapshot is created before the additive schema migration.
- Old signed-in sessions require reauthentication once, by design.
- Recovery emails require a verified address and configured SMTP, which has **not** been tested with your actual provider.
- No changes to your public URL, Portainer stack identity, or underlying `/data` database path are required.

## Emergency administrator recovery (if email is unavailable)

As the Docker host operator, open Portainer's terminal for the *running MLO application container* with an interactive session (or use `docker exec -it <your_MLO_container_name> sh`). Run:

```bash
python -m scripts.reset_admin_password admin
```

Replace `admin` with your configured **administrator username**. The script securely prompts twice for a temporary password without putting it in command history. It requires container-shell access (an infrastructure-level privilege), revokes old sessions, and forces a password change at next login. It does not create a new admin or require copying password hashes. Do not grant users shell access merely to reset their account.
