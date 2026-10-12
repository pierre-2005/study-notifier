# Portainer / Raspberry Pi upgrade guide

**Before starting:** The source available for this preview was Study Notifier v1.4.1. If your currently deployed container comes from the previously generated **v2** package, **stop and test against a copy of your actual v2 SQLite database**; this preview is not verified for v2-to-v3 migration. Back up source, volume, `.env` and image tag.

## 1. Identify your old volume and container

SSH to the Pi:

```bash
docker ps -a
docker volume ls
```

Find your existing Study Notifier volume. It might be named `study-notifier_study_notifier_data`, `mlo_study_notifier_data` or something else. **Do not guess.** Confirm with:

```bash
docker inspect YOUR_OLD_CONTAINER --format '{{json .Mounts}}'
```

The mount mapped to `/data` is your live data source. This is also where `study_notifier.db` should be located.

## 2. Back up the entire volume, not just the database

Stop the old container before the final cold backup to avoid concurrent writes. You can also make an online SQLite backup first. Example, replacing `EXACT_VOLUME_NAME`:

```bash
mkdir -p ~/mlo-backups
docker run --rm -v EXACT_VOLUME_NAME:/source:ro -v "$HOME/mlo-backups:/backup" alpine:3.20 \
  sh -c 'cd /source && tar czf /backup/mlo-before-v3.tar.gz .'
```

Inspect the backup: `tar tzf ~/mlo-backups/mlo-before-v3.tar.gz | head`. Store another copy outside the Pi. If `alpine:3.20` isn't available locally, Docker may need internet to pull it.

**Do not destroy the old volume or leave two app versions writing to the same database.**

## 3. Build the image on the Docker host

Extract the complete ZIP into a folder on the Pi, for example `~/mlo-next`, so that folder contains `Dockerfile`, `app/`, `requirements.txt` and `docker-compose.portainer.yml`.

```bash
cd ~/mlo-next
docker build -t mlo-next:v3-preview .
docker images mlo-next
```

A Portainer **Web Editor** stack with `build: .` often fails because it cannot access the source context. `docker-compose.portainer.yml` uses **`image: mlo-next:v3-preview`**, so Portainer only starts a prebuilt image. The Docker environment used by Portainer must be the **same host/environment** where the image was built.

## 4. Configure the Portainer stack

In **Portainer → Stacks → Add Stack → Web Editor**, paste `docker-compose.portainer.yml`.

Set environment variables under the stack's **Environment variables** section:

| Name | Value |
|---|---|
| `MLO_DB_VOLUME_NAME` | Actual original volume name from `docker inspect`, **not** a guessed name |
| `APP_USERNAME` | Administrator username you already use |
| `APP_PASSWORD` | Administrator password from your existing deployment |
| `SESSION_SECRET` | The **existing** session secret if known, or a new one (existing sessions will sign out) |
| `COOKIE_SECURE` | `true` with HTTPS Cloudflare Tunnel, `false` only for local HTTP testing |
| `TIMEZONE` | e.g. `America/Edmonton` |
| `NTFY_TOPIC` | Optional legacy *global* topic. Leave empty if using per-account phone topics only |
| `NTFY_BASE_URL` | e.g. `https://ntfy.sh` |

Generate a secret on the Pi with:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

**Security:** The external volume declaration in the provided Compose file fails rather than silently creating a new empty database when the provided name doesn't exist. That's intentional.

If binding `127.0.0.1:8001` prevents a reverse proxy in a separate container from reaching the app, configure a shared Docker network or an appropriate host binding. Do not expose the port publicly without HTTPS and access controls.

## 5. Start and verify

Deploy the new stack after stopping the old container. Watch logs:

```bash
docker ps -a
docker logs NEW_MLO_CONTAINER --tail 200
```

Open HTTPS URL `/login`, sign in, then check `/life`, `/life/projects`, `/life/tasks`, `/life/notes` and your old Classic pages. Check that old data remains available. A `.pre-mlo-v3.sqlite.backup` should be created beside the existing database on first start if it existed beforehand. Verify that it exists.

Test two accounts and their privacy before allowing other people to use the service. Connect ntfy phones under `/life/devices`.

## 6. Rollback

If startup or a data check fails, stop the new stack, start the old image/stack and restore the cold backup if the schema or data was changed. **Do not run old and new simultaneously against one SQLite database.** Restore with a temporary container only while both stacks are stopped.

The automatically created SQLite pre-migration snapshot is a secondary safety measure, **not a substitute for the whole-volume archive** because that archive includes file attachments and other data.

## 7. Git deployments

If you want Portainer to deploy from GitHub, first push the extracted project files to a separate test branch. Portainer's Git stack can provide source/build context where supported, but some remote environments cannot build. The host-built image route above is the recommended tested *configuration*, although the actual Portainer UI deployment was not performed here.
