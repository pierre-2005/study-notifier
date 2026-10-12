# Deploy v3.2 with your existing GitHub → Portainer Stack

Your existing Portainer deployment uses the Git repository `https://github.com/pierre-2005/study-notifier.git`, branch `refs/heads/main`, with `docker-compose.yml`. **This package is built for that workflow.** Do not switch to Web Editor and do not build a Pi image manually.

## Before changing any files

1. In Portainer, open the **existing** stack and record its exact stack name, published port and volume mapping. Keep `127.0.0.1:8001:8000` if your current HTTPS proxy/Cloudflare tunnel targets that host port.
2. On the Pi, inspect mounts of the running MLO container, `docker inspect CONTAINER_NAME --format '{{json .Mounts}}'`. Verify the volume mounted at `/data` and its actual name. If the supplied Compose file declares a different volume, **retain the currently deployed mapping instead**.
3. Back up the **entire** data volume (SQLite DB, uploads, backups), ideally with the application stopped for the final copy, and verify the archive contents. Keep a second copy off the Pi. Never delete volumes to resolve port/pull errors. Preserve the currently running image/tag for rollback.
4. Do not place passwords, PATs or actual `.env` files in your repository. Keep existing stack variables `SESSION_SECRET`, `APP_USERNAME`, `APP_PASSWORD`, `TIMEZONE`, etc.

## Publish

1. Extract the archive. Copy the files **inside** `mlo-v3-consolidated/` into the **root** of the GitHub repository. `Dockerfile`, `app/`, `.github/` and `docker-compose.yml` must all be at the root.
2. Commit the changes to `main`.
3. Open **GitHub → Actions** and wait for **Build and publish MLO Docker image** to be green. It publishes `ghcr.io/pierre-2005/study-notifier:v3.2-studio` for both `linux/amd64` and `linux/arm64` (including most Raspberry Pi 64-bit installations).
4. Set the container package visibility to public if Portainer does not have registry authentication. A successful workflow by itself does **not** make a GHCR package publicly pullable.

## Redeploy existing stack

In Portainer, go to **Stacks → your existing Study Notifier/MLO stack → Pull and redeploy**. Keep repository URL, branch `refs/heads/main`, credentials, port `8001` and existing environment variables. Leave GitOps polling off until verified. Do not create a separate second stack occupying port 8001.

The v3.2 Compose file uses `pull_policy: always`, so the new published image is pulled when you redeploy. If the image is not published or publicly readable, Portainer will fail at *image pull*, before app startup.

## Verify

- Visit `/health` and the HTTPS `/login` page.
- Check Today, Tasks, Focus, Study, Work, Money, Calendar and Spaces with your admin account.
- Verify all old courses, assessments, jobs, bills, finance categories/transactions and shared grocery data remain.
- Verify the new Tasks module contains your old to-dos once, not twice.
- Verify `/data/study_notifier.pre-mlo-v3.2.sqlite.backup` exists and preserve it.
- Sign in with a separate account; check they **cannot** see administrator finance/study/jobs legacy data.

## Rollback

If the app is unhealthy or data is missing, stop the current container. Restore the full volume archive and redeploy the previous known-good Docker image. An old application should not write into a database already changed by v3.2. Do not run both versions against one SQLite volume.

**Limitations:** v2-to-v3 compatibility remains unverified; the GitHub workflow and live Portainer configuration cannot be tested from this archive. Pre-v3.2 snapshot is only the database, not attachments; the whole-volume backup is necessary.

## New calendar credentials (optional)

See [CALENDAR_SETUP.md](CALENDAR_SETUP.md). Add `MLO_PUBLIC_URL`, `MLO_CREDENTIAL_KEY` and optional Google/Microsoft OAuth credentials as Portainer environment variables, **never inside GitHub**. The application otherwise starts without OAuth linking enabled. Existing OAuth tokens require the same `MLO_CREDENTIAL_KEY` after every deployment.
