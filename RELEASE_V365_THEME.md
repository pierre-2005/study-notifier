# MLO Studio v3.6.5 - Account-owned appearance

## Changes
- Appearance mode, color palette and palette tint style are now stored in SQLite by user ID.
- A signed-in user gets their saved appearance on the initial server-rendered page, before first paint.
- Setting changes are saved via authenticated `/life/layout/appearance` requests. They are validated, origin-checked and kept separate from other accounts.
- The Appearance settings screen displays save status.
- Added `tests_v365_appearance.py` to GitHub Actions.
- Existing projects, settings, credentials, calendar integrations and volumes are not modified.

## Upgrade via GitHub and Portainer
1. Back up your persistent `/data` Docker volume.
2. Copy the patch files to the *root* of `pierre-2005/study-notifier` on `main`, preserving paths including `.github/workflows/publish-image.yml`.
3. Wait for the GitHub Actions test and image-publish jobs to succeed.
4. Verify Portainer's Compose uses `ghcr.io/pierre-2005/study-notifier:v3.6.5-user-themes`, not an older image.
5. Pull and redeploy the existing Portainer Git stack. Do not delete its volume or modify secrets.
6. In MLO Settings > Appearance, choose your preferred palette and mode **once**. Earlier browser-only appearance values are deliberately not migrated, as they may belong to another account that used the same browser.
7. Log in using a second account to verify independent settings; open Windows app or a different browser and verify saved theme follows the account.

No new environment variables needed. This release adds `life_appearance` table automatically; it preserves all existing data. The Microsoft Store PWA package does not need to be rebuilt for this server-side UI enhancement.
