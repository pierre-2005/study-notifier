# MLO v3.5 environment variables in your GitHub-connected Portainer stack

Use the downloadable `.env` **as a private checklist**, not a file to commit to public GitHub. Your running stack uses **Portainer's Environment variables** and the checked-in `docker-compose.yml` passes them into the container. Portainer will not obtain OAuth secrets from GitHub Actions automatically.

**Preserve existing values during any upgrade:** `SESSION_SECRET`, `APP_USERNAME`, `APP_PASSWORD`, `MLO_CREDENTIAL_KEY`, Google and Microsoft OAuth credentials. Losing/changing the credential key can break decryption of all existing connections.

| Variable | Purpose | Required? |
| --- | --- | --- |
| `SESSION_SECRET` | Login cookie signing | Yes, preserve existing |
| `APP_USERNAME`, `APP_PASSWORD` | Bootstrap administrator configuration | Yes, preserve existing |
| `COOKIE_SECURE=true` | Secure cookies over Cloudflare/HTTPS | Yes for public site |
| `TIMEZONE=America/Edmonton` | Local calendar/time display | Strongly recommended |
| `MLO_PUBLIC_URL=https://organizer.overvault.ca` | OAuth redirect host | Yes for integrations |
| `MLO_CREDENTIAL_KEY` | Fernet encryption of stored tokens | Yes for integrations |
| `MLO_GOOGLE_CLIENT_ID/SECRET` | Google web OAuth | Required for Google |
| `MLO_MS_CLIENT_ID/SECRET` | Microsoft Entra web OAuth | Required for Outlook |
| `MLO_CALENDAR_AUTO_SYNC=true` | Enable background polling | Defaults to true |
| `MLO_CALENDAR_SYNC_MINUTES=10` | Frequency per connection (clamped 5–120 min) | Optional |
| `MLO_CALENDAR_SYNC_BATCH_SIZE=3` | Max accounts processed each scheduler pass | Optional |
| `MLO_LEGAL_CONTACT_EMAIL` | Public policy contact email | Configure a real monitored address |
| `NOTIFIER=ntfy` | Phone notifications | Optional |
| `NTFY_BASE_URL=https://ntfy.sh` | ntfy server | Optional |
| `NTFY_TOPIC` | Legacy default topic | Optional; leave blank if individual topics are managed in MLO |
| `STUDY_NOTIFIER_DB=/data/study_notifier.db` | Internal data path | Already fixed in Compose; preserve |
| `MLO_ATTACHMENT_DIR=/data/mlo_uploads` | Upload storage inside existing volume | Already fixed in Compose; preserve |
| `TZ` | Generic host timezone variable | Not required by MLO when `TIMEZONE` exists; remove if unused elsewhere |

### Existing volume safety
`docker-compose.yml` retains:

```yaml
volumes:
  - study_notifier_data:/data
```

Confirm this resolves to the **same existing Docker volume** as production, including if the Portainer stack has changed names. Back up that volume before any migration. Do not create another stack for this upgrade. Keep your current `127.0.0.1:8001:8000` port unless your reverse proxy setup changes.

### New deployment sequence
1. Copy source files into GitHub repository root, **excluding `.env`**.
2. Commit and wait for GitHub Actions to finish the v3.5 tests and publish image tag `v3.5-unified-calendars`.
3. In Portainer, add the new optional auto-sync variables if you want to customize defaults.
4. Confirm the stack's image tag and DB volume mapping.
5. Pull and redeploy the **existing** stack.
6. Test a writable Google or Outlook connection and watch the last-sync timestamp update without pressing Sync.
7. Open the unified New Event form and create events into MLO and a disposable external test calendar.

Production external integration and background scheduling have not been verified on the actual Raspberry Pi in this generated package. Start with a disposable external calendar.
