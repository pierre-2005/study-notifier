# MLO Studio v3.4.3: Sidebar + Connected Calendar Controls

## Sidebar
- Collapsed sidebar keeps both the M avatar and toggle inside the 72-pixel icon rail, in separate stacked positions.
- The expand arrow does not protrude into the page. The main content area remains aligned with the collapsed sidebar.
- Expanded sidebar appearance and mobile drawer are unchanged.

## Why "admin setup needed" appeared
The MLO user account's role (`Admin`) is **not** a Google Cloud or Microsoft Entra developer registration. The old UI erroneously used a role-sounding description for missing **server-side** OAuth configuration. v3.4.3 replaces this with “Connection not configured” and an expandable requirements checklist visible to the server's MLO admins (variable **names only**, no secrets).

The existing Git-deployed Portainer stack should retain these environment variables, configured privately in Portainer:

- `MLO_PUBLIC_URL`: your existing public site origin (`https://mlo.yourdomain.example`), no trailing slash
- `MLO_CREDENTIAL_KEY`: existing Fernet key; generate only if this is the first calendar setup
- `MLO_GOOGLE_CLIENT_ID` and `MLO_GOOGLE_CLIENT_SECRET`
- `MLO_MS_CLIENT_ID` and `MLO_MS_CLIENT_SECRET`

Do not put secrets into GitHub. Do not rotate `MLO_CREDENTIAL_KEY` without a token re-authorization plan, as it encrypts previously stored calendar credentials.

### Google Cloud setup
1. Create/select a Google Cloud project, enable Google Calendar API, and configure OAuth consent (choose appropriate internal/external audience).
2. Add requested scopes `openid`, `email`, `https://www.googleapis.com/auth/calendar.readonly`, and `https://www.googleapis.com/auth/calendar.events`. Google may require verification of sensitive scopes for public users; testing mode only allows authorized test accounts.
3. Create an OAuth Client ID of type **Web application** with the redirect URI **exactly** `https://YOUR-MLO-DOMAIN/life/calendars/callback`.
4. Put the Google OAuth client ID and secret into the existing Portainer Git stack's environment variables, not the repository.
5. Redeploy the same stack after publishing the v3.4.3 image. In MLO: Connected calendars → **Connect Google**, grant permissions, and choose an account. Repeat for your other Google accounts. If you connected an account before v3.4.3, choose **Reconnect for editing**.

### Microsoft Entra / Outlook setup
1. Register an application in Microsoft Entra, with account types that cover your personal and/or organization accounts.
2. Add a Web redirect URI **exactly** `https://YOUR-MLO-DOMAIN/life/calendars/callback`.
3. Configure Microsoft Graph **delegated** permission `Calendars.ReadWrite` and `User.Read`; sign-in also requests `openid`, `profile`, `email`, and `offline_access`.
4. Put the Application (client) ID and the client secret in Portainer, then redeploy the existing stack.
5. Connect/reconnect accounts from MLO. Organizational Microsoft accounts may require approval under the organization's tenant policies.

### Read/write behavior
- `Connect Google` / `Connect Outlook`: OAuth account authorization, each account is stored separately under its MLO user.
- `Sync`: manually fetches changed events into MLO's local read-only display cache.
- `New event`: creates a timed event in a writable calendar from that account. Editing a synchronized timed event from the MLO calendar writes its title, start/end times back to Google/Microsoft.
- `Delete`: demands typing **DELETE** to confirm removal from the original provider, not just the MLO list.
- Older connections that have only read-only scopes must **Reconnect for editing** first. Their existing calendars remain intact.
- External calendar edits made outside MLO are reflected after pressing **Sync**, not automatically pushed or continuously monitored.
- Timed events are supported in the editor. All-day and complex recurring/attendee workflows should still be edited in Google Calendar/Outlook until implemented and fully validated.
- Apple published iCalendar feeds remain **read-only**; they are not authenticated Apple/iCloud two-way synchronization. A subsequent Apple integration could use authenticated CalDAV, with appropriate secure credential handling and additional tests.

## Safety and testing
- External write/delete routes verify that the connection is owned by the logged-in user. Remote event IDs used for edits must have a matching cached event in that connection.
- Calendar OAuth tokens continue using encrypted storage with the existing `MLO_CREDENTIAL_KEY`.
- No schema migration or new environment variables are required (provider credentials were already supported in v3.2).
- Mocked API tests cover OAuth scope guards, account isolation, create/edit/delete and Google/Microsoft outbound payloads. Real provider acceptance, calendar-specific rights, recurrence and provider app verification remain untested and need a controlled test calendar before production use.
- Existing file upload/import and task/project data are unchanged.

## Deployment
1. Back up the MLO `/data` Docker volume, including database and attachments.
2. If you already have v3.4.2, apply the **hotfix** files to your existing GitHub repo, including `.github/workflows/publish-image.yml`. Or copy the complete v3.4.3 source.
3. Commit `main`, wait for successful Actions smoke tests and the `ghcr.io/pierre-2005/study-notifier:v3.4.3-calendars` publish step.
4. Confirm `docker-compose.yml` uses the same `study_notifier_data` volume, `127.0.0.1:8001:8000` port and your required environment variables. The Compose image tag must match the published tag.
5. In your **existing** Portainer Git stack, use **Pull and redeploy**. Do not create a second stack or delete any volumes.
6. Confirm the dashboard, collapsed sidebar and connected-calendar page before using external write operations. Start with a test event on a noncritical external calendar.
