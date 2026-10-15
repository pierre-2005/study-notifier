# My Life Organized Studio v3.6

**Account security + interface quality release**, based on the MLO v3.5 source application.

The update adds administrator-managed passwords and member capabilities, optional recovery email and verification, one-use password-reset links, session revocation, and a theme-aware project deletion panel. It also preserves MLO's existing projects, tasks, multi-account Google/Outlook calendar integration, background sync, themes and server-backed PWA architecture.

## Read before upgrading

- `docs/DEPLOY_V36.md` - precise GitHub -> GitHub Actions -> Portainer deployment.
- `docs/MLO_PRODUCT_RELEASE_MASTER_PLAN.md` - **one consolidated review document** covering account security/email, intelligent syllabus and bank-statement imports, and the free Microsoft Store release plan.
- `docs/VERIFICATION_V36.md` - actual test outcomes, limitations and remaining security work.

## Main changes

- **Admin Users:** approve/revoke; enable/disable; per-user capability controls; administrator password-confirmed temporary password and recovery email management.
- **Account security:** current-password change, recovery-email entry and verification, optional self-service forgot-password for **verified** email only.
- **Password safety:** short-lived single-use reset links, session revocation and required password rotation for admin-issued temporary passwords.
- **Database:** additive schema update, automatic pre-migration SQLite snapshot, existing account/data preservation.
- **UI:** project deletion surface follows the chosen light/dark theme and colors, with accessible spacing and contrast.
- **Bootstrap:** `APP_PASSWORD` creates the initial administrator but does **not** reset its password on every restart.

All optional email settings are listed in `.env.production.example`; use Portainer environment variables for production and keep real passwords outside GitHub. Every existing user must sign in again after the new session-version check activates.

**Scope note:** syllabus and bank-statement extraction and Microsoft Store submission are described in the consolidated plan, but are **not** implemented in this release. Live SMTP must be configured and tested before email recovery can deliver messages. Public deployment should wait until remaining tenant isolation and security concerns are addressed.

## v3.6.1 notification-device privacy hardening

All phone records are account-owned. This update adds explicit 404 responses for cross-account toggle and delete attempts, disables legacy shared-topic delivery by default, and checks owner-matched notification routing in CI. See `docs/DEVICE_PRIVACY_V361.md` for behavior, caveats, and upgrade instructions.
