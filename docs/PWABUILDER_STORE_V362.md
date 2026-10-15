# MLO v3.6.2: Microsoft Store / PWABuilder readiness

**Active domain:** `https://organizer.overvault.ca` (do not change OAuth redirects or migrate to `www.organizer.overvault.ca`).

## Why PWABuilder reported “Missing Name” and no service worker

PWABuilder inspects MLO's **public homepage**. Previous builds linked the web app manifest only from the signed-in `base.html`, and registered the service worker from `life.js`, which the public homepage never loaded. Worse, `/service-worker.js` was treated as a protected route, so unauthenticated clients were redirected to login rather than receiving a JavaScript file.

This patch:
- Adds the existing MLO web manifest and app icons to `app/templates/public_shell.html`, shared by public homepage, privacy and terms pages.
- Registers the existing **static-only** service worker on the public homepage.
- Allows anonymous requests to `/service-worker.js`, while leaving all private `/life` routes protected.
- Increments the static-cache version and excludes the manifest from service-worker caching so metadata updates remain fresh.
- Adds `tests_pwa_public.py` to the GitHub Actions pre-publish test job.
- Updates the Compose and GitHub image tag together to `ghcr.io/pierre-2005/study-notifier:v3.6.2-pwa-ready`.

**No database schema change or new environment variables.** The service worker only handles `/static/` GET requests. Authenticated pages, API data and private workspace records are **never cached by this worker**. The installed Windows app still uses the same existing MLO server and database.

## Upgrade on GitHub → Portainer

1. Back up the existing Docker volume, including `/data/study_notifier.db` and `/data/mlo_uploads`.
2. Copy the contents of the hotfix ZIP into the **root** of your existing GitHub `pierre-2005/study-notifier` repository; preserve the `.github/` folder. Alternatively, replace the repo source with the full ZIP **if the running code matches v3.6.1**.
3. Commit on `main` and open GitHub → **Actions**. Wait until **both** “Test application” and “Publish multi-architecture Docker image” succeed.
4. Confirm your `docker-compose.yml` references `ghcr.io/pierre-2005/study-notifier:v3.6.2-pwa-ready` and retains the **same named volume** and port `127.0.0.1:8001:8000`. In Portainer, use the existing **Git Stack** and **Pull and redeploy**. Don't create another stack or edit the stack through the Web Editor.
5. Open these URLs **without signing in** (incognito or another browser):
   - `https://organizer.overvault.ca/` → public home with name/description
   - `https://organizer.overvault.ca/static/manifest.webmanifest` → JSON including `"name":"My Life Organized"`
   - `https://organizer.overvault.ca/service-worker.js` → JavaScript, no login redirect
   - `https://organizer.overvault.ca/static/icon-192.png` → 192px icon
   - `https://organizer.overvault.ca/static/icon-512.png` → 512px icon
6. Open DevTools → **Application** → Manifest and Service Workers in Microsoft Edge or Chrome to verify the manifest and worker are registered. Then test `https://organizer.overvault.ca` again at https://www.pwabuilder.com/.
7. If PWABuilder still displays old findings, select **retest** and try an incognito browser. Confirm GitHub Actions built the new tag and Portainer actually deployed it before concluding the patch didn't work.

## Next: package for Microsoft Store

With PWABuilder's required checks passing:
1. Open Microsoft Partner Center with your existing **Personal** developer account (Overvault is not currently a registered company).
2. Reserve **My Life Organized** if available, then open **Product management → Product identity** to obtain the required Package ID and Publisher details.
3. In PWABuilder select **Package for Stores → Windows**. Enter the publisher identity returned by Partner Center; generate the Windows MSIX bundle.
4. Install and test the package on Windows first. Verify login, logout, accounts, links, external calendar OAuth callbacks and updates. The app must point to `https://organizer.overvault.ca`, not a local or copied database.
5. Complete Store listing and privacy details, mark price **Free**, and submit for review when public-readiness checks are complete.

Normal website or backend updates can be deployed through GitHub → Portainer and become available to the installed app without repackaging. Store package updates are typically needed when the package identity, icon or certain packaged Windows app settings change.

## Before public release

**Do not interpret a clean PWABuilder score as a security audit or Store approval.** Resolve the outstanding Google Search Console **Deceptive pages** issue and check that authorization, account isolation, recovery, terms, privacy, and backup restoration meet your public launch requirements. PWABuilder packaging is only one step toward release. Do not alter the existing active domain, OAuth callbacks or the Cloudflare Tunnel.

## Verification limits

Locally verified the unauthenticated homepage, manifest, 192/512 icons and public worker using FastAPI TestClient. Existing smoke, legal, account-recovery and device-isolation regression tests passed. A Chromium live-server test could not complete because the execution environment blocked browser access to localhost; live PWABuilder detection and Microsoft Store certification need verification on your deployed site.
