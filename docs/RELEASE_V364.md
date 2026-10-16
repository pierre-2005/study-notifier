# MLO Studio v3.6.4, Store-readiness and iPhone pairing

## Changes

- iPhone-specific QR code links to a sign-in-protected MLO pairing page with one-tap topic copy, instead of displaying an unsupported iOS ntfy deep link.
- Android direct-subscribe QR remains unchanged.
- iPhone pairing page and QR are account scoped and do not expose the device topic in the QR payload.
- Manifest adds `lang`, `dir`, `orientation`, categories, and wide/narrow screenshot records using synthetic test-account renders.
- Service worker cache/version incremented. Private user pages remain uncached.
- Windows PowerShell diagnostics and screenshot-replacement instructions included.
- No changes to existing database schema, application port, or domain.

## Verification

Locally tested: `tests_v364_ios_manifest.py`, `tests_v363_finance_pwa_qr.py`, `tests_v361_device_isolation.py`, `tests_pwa_public.py`, `tests_smoke.py`, `tests_v36_accounts.py`, `tests_v35_calendar.py`; Python compile and manifest screenshot pixel dimensions. These do not validate the user's external PWABuilder test-package installation, which requires its own error log.

## Deployment

1. Make a verified backup of your current Docker `/data` volume.
2. Copy the contents of the ZIP into your existing GitHub repository, preserving `.github/` and current Docker volume name.
3. Commit to `main`, allow the workflow to finish, then redeploy **the existing Portainer Git stack**.
4. Confirm `https://organizer.overvault.ca/manifest.webmanifest` contains the new screenshots and `https://organizer.overvault.ca/static/dashboard-desktop.png` serves a PNG.
5. Refresh the PWABuilder analysis. Generate a fresh Windows test package and use the included PowerShell troubleshooting instructions if installation fails.

Read `docs/PWABUILDER_WINDOWS_AND_IPHONE_V364.md` for the user-facing walkthrough.
