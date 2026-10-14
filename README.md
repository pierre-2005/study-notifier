# My Life Organized Studio 3.5

A complete GitHub-to-Portainer source release built from the v3.4.3 calendar integration, with the earlier event-destination and public legal-page patches incorporated.

**New:** one New Event form for MLO-only, Google and Outlook; private per-account MLO events; background calendar refresh; improved Windows PWA manifest. Data remains on the existing MLO server.

**Start here:**
1. `docs/V35_RELEASE.md`: what changed and current limitations.
2. `docs/PORTAINER_ENV.md`: environment variables and safe deployment into your existing stack.
3. `docs/MICROSOFT_ENTRA_SETUP.md`: register MLO with Entra for Outlook and Microsoft 365 calendars.
4. `docs/GOOGLE_SEARCH_CONSOLE_SECURITY.md`: investigate the deceptive-pages security issue when Search Console lists no example URLs.
5. `docs/WINDOWS_SERVER_BACKED_APP.md`: Windows Store PWA plan with shared server data.
6. `docs/VERIFICATION_V35.md`: local test results and what remains unverified.

## Deployment safety
- Do not upload an `.env` containing secrets to GitHub. The `.env.example` file is a sample only.
- Keep the same existing `study_notifier_data:/data` Docker volume (verify its **actual** Portainer volume name) and port `8001`.
- Back up database and attached files before upgrading.
- Wait for GitHub Actions to publish `ghcr.io/pierre-2005/study-notifier:v3.5-unified-calendars` before pulling in Portainer.
- Test on a disposable Google/Outlook calendar; provider writes have only been verified with simulated API responses here.

Google and Microsoft developer accounts, Google Search Console security review, and Windows Store submission are external processes that require user account authorization and cannot be completed by deploying source files alone.
