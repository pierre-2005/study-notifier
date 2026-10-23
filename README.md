# My Life Organized v3.7.1

A redesigned shared workspace with nested tasks, touch/keyboard boards, private reminders, reviewed course-outline imports, optional AI extraction, calendar-aware study planning, email verification and password-reset codes. Existing accounts, permissions, data, calendars and the GitHub Actions to Portainer workflow are retained.

Start with the [setup report](docs/V37_SETUP_REPORT.md), [verification](docs/V37_VERIFICATION.md), [fix review](docs/V37_REVIEW_AND_FIXES.md), [Macro-focused product research](docs/V37_PRODUCT_RESEARCH.md), [email walkthrough](docs/V37_EMAIL_SETUP.md) and [deployment/rollback](docs/V37_DEPLOYMENT.md). Historical release notes follow; current account behavior is described in the v3.7 reports.

# MLO Studio v3.6.4 Update

See [the v3.6.4 release notes](docs/RELEASE_V364.md) and [Windows/iPhone guide](docs/PWABUILDER_WINDOWS_AND_IPHONE_V364.md). All previous features and backend data are retained.

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

## v3.6.3: Finance, PWA and ntfy QR fixes

See [docs/RELEASE_V363_FINANCE_PWA_NTFY.md](docs/RELEASE_V363_FINANCE_PWA_NTFY.md) for the finance budget-save repair, persistent tabs, root PWA manifest, and owner-only ntfy QR pairing. Existing Portainer data volume and public MLO domain remain unchanged.
