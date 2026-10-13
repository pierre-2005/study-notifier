# Deploy MLO v3.4 via the existing GitHub → Portainer stack

You already have a Portainer **Git repository stack** using `refs/heads/main` and the root `docker-compose.yml`. Do not use the Web Editor or create a parallel stack on the same port.

1. **Backup first:** identify and back up the complete existing `/data` Docker volume, including `study_notifier.db`, WAL files and `mlo_uploads`. Ideally validate restoration onto a separate test volume. Do not delete the original volume. Stop the app briefly for an ordinary file-copy backup; SQLite's backup API is safer for live snapshots.
2. **Check mapping:** the bundled `docker-compose.yml` mounts a volume key `study_notifier_data:/data`, which may be prefixed with the stack name by Docker. Compare your current Portainer Mounts tab and update the Compose volume declaration to the exact existing external or named volume if necessary. The provided mapping is not proof of what your live deployment currently uses.
3. Extract `MLO_Studio_v3.4_Enhanced_GitHub_Portainer.zip`. Copy **contents of `mlo-v3.4/`** into your current repository root, replacing prior app files and including `.github/workflows/publish-image.yml`.
4. Preserve your real deployment environment variables, `SESSION_SECRET`, admin credentials, public URL, OAuth credentials, ntfy configuration and existing volume. The ZIP intentionally does not contain secrets.
5. Commit to `main`. Visit **GitHub → Actions** and wait for `Build and publish MLO Docker image` to complete. The workflow tags `ghcr.io/pierre-2005/study-notifier:v3.4-enhanced` for AMD64 and ARM64. Ensure Portainer can pull it (public package or suitable registry credentials).
6. Inspect Portainer's Stack Git configuration, which should remain `refs/heads/main`, root `docker-compose.yml`; then click **Pull and redeploy**, without creating a second stack or changing `127.0.0.1:8001:8000`.
7. Verify `/health`, log in via HTTPS at your existing Cloudflare/public URL, check old courses and finance, try quick task and Insights, and confirm the server created a pre-v3.4 snapshot in `/data`.
8. If the app is unhealthy, inspect **Portainer → Containers → Logs**. Roll back the image tag and source carefully; restore the backed-up DB **only if required and with the app stopped**.

**Important:** If your live database originates from the earlier independently generated v2 release instead of v3.3, test migration against a copy first; compatibility with that exact schema was not verified. Don't put two app instances on the same SQLite volume.

This repo's root `docker-compose.yml` and GitHub Actions file are the only deployment paths used for this stack. Browser styles and scripts are automatically cache-busted via version `3.4.0`.
