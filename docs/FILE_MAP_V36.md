# MLO Studio v3.6: exact new and modified file locations

Upload the *contents* of the extracted `mlo-v3.6/` directory into the **root of your existing GitHub repository**, preserving directory structure. Never upload your real `.env` or secrets.

## New files

| Path | Purpose |
|---|---|
| `app/account_security.py` | Recovery tokens, email verification, account controls, admin resets and session-safe flows |
| `app/templates/account_security.html` | Email and password management page |
| `app/templates/change_password.html` | Password change, including forced change for temporary passwords |
| `app/templates/forgot_password.html` | Anonymous account recovery request |
| `app/templates/reset_password.html` | Short-lived recovery token form |
| `app/templates/verify_email.html` | Email ownership confirmation |
| `scripts/reset_admin_password.py` | Operator-only emergency admin reset, from running container |
| `scripts/__init__.py` | Maintenance CLI package |
| `tests_v36_accounts.py` | Password, session, admin and email security tests |
| `tests_v36_visual.py` | Real browser contrast/layout verification |
| `docs/MLO_PRODUCT_RELEASE_MASTER_PLAN.md` | Complete review roadmap, including email, imports and Microsoft Store |
| `docs/MLO_PRODUCT_RELEASE_MASTER_PLAN.pdf` | PDF version of review roadmap |
| `docs/DEPLOY_V36.md` | GitHub -> Portainer upgrade instructions |
| `docs/FILE_MAP_V36.md` | This map |
| `docs/VERIFICATION_V36.md` | Tested coverage and limitations |
| `.env.v36.example` | Additional SMTP variables only; do not use as full standalone production env |

## Modified files

| Path | What changed |
|---|---|
| `app/auth.py` | Additive schema, password/session version, email fields, capability rules, bootstrap-only admin |
| `app/main.py` | Recovery route allowlist, session revocation, capability guard, signup email, pre-upgrade backup |
| `app/backup.py` | Pre-v3.6 SQLite backup |
| `app/templates/signup.html` | Optional recovery email at registration |
| `app/templates/login.html` | Forgot-password entry |
| `app/templates/admin_users.html` | Per-user permissions, temporary password and email administration |
| `app/templates/settings.html` | Account security navigation |
| `app/templates/base.html` | Quick-switcher link to Account security |
| `app/templates/public_privacy.html` | Updated accurate account information and background calendar wording |
| `app/static/design32.css` | Project deletion contrast fix and responsive security forms |
| `app/meta.py` | Version bump to 3.6.0 |
| `docker-compose.yml` | New image tag and optional SMTP variables, preserving existing volume/port |
| `Dockerfile`, `run_app.py` | Disable request-path access logs to reduce chance of recovery token leakage |
| `.github/workflows/publish-image.yml` | Build tag and regression tests for v3.6 |
| `.env.example`, `.env.production.example` | Document optional SMTP settings |
| `README.md` | Release summary and documentation links |
