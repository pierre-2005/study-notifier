# MLO v3.6 verification and security boundaries

## Verified locally

- Core smoke tests (`tests_smoke.py`), new features, legacy migrations, consolidation, personal tasks/projects/files/calendars, previous privacy/role tests.
- v3.6 account test: admin temporary password, required change, session-version revocation, verified email, reset token single-use, user permission denial, bootstrap password unchanged on restart.
- v3.6 Chromium visual test: deletion card readability across light/dark and neutral/ocean/sage/rose/amber/lavender palettes; layout at widths 375, 768 and 1280 px.
- Python compilation of the full application source.

## Deliberate limits

- SMTP integration is optional and unverified against your provider; failure handling is present, but production deliverability requires a live test.
- These are application-layer capability checks for selected actions, not a complete enterprise policy engine. Shared legacy finance/study modules must be redesigned before public access.
- No real Raspberry Pi, Cloudflare, Google, Microsoft, Windows packaging or Store certification test was run in this environment.
- FastAPI still uses cookie-backed session auth with same-site restrictions and Origin/Fetch-Site protection. A consistent CSRF-token implementation and rate-limiting/2FA need further security engineering.
- SMTP submission now requires TLS or implicit TLS (port 465); SMTP sending is synchronous with a network timeout. A background mail queue is recommended at scale.
- SQL migration is additive; retains existing users. Full Docker volume backup and restore rehearsal remain mandatory.
