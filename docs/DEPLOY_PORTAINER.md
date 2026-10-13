# Safe v3.3 update: GitHub repository → GitHub Actions → Portainer

This uses your **existing** Portainer Git Stack, *not* Web Editor.

## 1. Preserve your currently running installation

1. In Portainer → **Stacks**, open your existing stack and record the stack name, compose path (`docker-compose.yml`), branch (`refs/heads/main`), environment variables, and the actual database volume mounted at `/data`.
2. Use Portainer's Containers UI or Pi shell to inspect the current container's mounts. If using a Pi shell: `docker inspect CONTAINER_NAME --format '{{json .Mounts}}'`.
3. Take a **complete backup of the entire `/data` Docker volume**, including the SQLite file, its write-ahead log files if any, attachments and OAuth-related persisted data. Prefer a stopped-container final backup, and verify an off-device copy. Save the exact currently working Docker image tag for rollback.
4. Check **the exact existing volume name** against the `docker-compose.yml` in this package. `study_notifier_data` is only a Compose key and may be stack-prefixed by Docker. Do not unknowingly attach a new empty volume.

## 2. Update GitHub

1. Extract the ZIP. Copy the **contents of `mlo-v3.3/`**, including hidden `.github/`, to the **root** of `https://github.com/pierre-2005/study-notifier.git`, replacing corresponding app files. Do not create a nested folder.
2. Make sure the root has `Dockerfile`, `app/`, `requirements.txt`, `docker-compose.yml`, `.github/workflows/publish-image.yml`.
3. If necessary, adjust only the Compose **volume declaration** so it matches the already-running data volume, or keep your known-correct production declaration unchanged. Keep host port `127.0.0.1:8001:8000` and existing secrets.
4. Push/commit to `main`. The GitHub Action publishes `ghcr.io/pierre-2005/study-notifier:v3.3-polished` on `linux/amd64` and `linux/arm64`.
5. Wait until GitHub **Actions → Build and publish MLO Docker image** is **green**. Make the GHCR package readable by Portainer, either by setting the package public or by configuring GHCR registry credentials within Portainer. It does not become public automatically.

## 3. Deploy from your current Portainer stack

1. **Do not create a second stack.** It will compete for port 8001 and may attach a new database.
2. Open **Stacks → your existing MLO stack → Redeploy from git repository**.
3. Keep the repo URL, `refs/heads/main`, Git authentication, and `docker-compose.yml` path as currently configured.
4. Click **Pull and redeploy** after the image exists. `pull_policy: always` downloads the published v3.3 image.
5. Keep current Cloudflare Tunnel target `127.0.0.1:8001` if that's what was previously working. HTTPS requires `COOKIE_SECURE=true`.

## 4. Verify in your browser

- Check `/health`, sign in to your regular account, and verify old projects, tasks, courses, expenses, attachments and calendars.
- Open **Today → Arrange**, move a card, change size, hide it, select Done, reload and confirm persistence.
- Change a palette in **Settings → Appearance**, visit Today, and verify that cards/sidebar change with the palette while the blue hero remains.
- Add a task and complete it without full-page navigation; refresh and check stored state.
- Confirm another account still has its own layout and private data.

## 5. Roll back safely

If you find missing data, migration errors or broken authentication, stop the v3.3 app and restore **both** the old full-volume snapshot and its exact old Docker image. Do **not** run earlier code against an already changed database. Do not remove volumes to fix image pull or port-binding errors.

## Extra calendar setup

Google/Outlook read-only OAuth is optional and requires your client keys plus `MLO_PUBLIC_URL`, `MLO_CREDENTIAL_KEY`. Apple/iCalendar is a read-only subscribed feed, not Apple ID OAuth or two-way sync. See [CALENDAR_SETUP.md](CALENDAR_SETUP.md).
