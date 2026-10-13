# Connect calendars: GitHub → Portainer deployment

Calendar integration is entirely optional; MLO can run with these settings blank. The UI only shows a provider as connectable after its required server settings are supplied. No credential values are stored in your public GitHub repository.

## 1. Add private stack environment variables in Portainer

Under the existing Git-deployed stack's Environment variables, add:

```text
MLO_PUBLIC_URL=https://organizer.overvault.ca
MLO_CREDENTIAL_KEY=<a stable Fernet key generated ONCE>
MLO_GOOGLE_CLIENT_ID=<Google OAuth Client ID>
MLO_GOOGLE_CLIENT_SECRET=<Google OAuth Client Secret>
MLO_MS_CLIENT_ID=<Microsoft Entra application Client ID>
MLO_MS_CLIENT_SECRET=<Microsoft Entra Client Secret>
```

Generate the encryption key once with:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Keep this key permanently and back it up securely.** Changing or losing it means previously authorized calendar tokens and private subscription links cannot be decrypted. Never commit passwords, tokens or these variables to GitHub, and do not paste their values into public bug reports.

`MLO_PUBLIC_URL` is the full **public HTTPS origin** of your MLO site (no trailing slash or subpath), for example `https://mlo.example.com`, not `http://127.0.0.1:8001`.

## 2. Google Calendar (multiple Google accounts)

In the Google Cloud Console, make/select a project, enable **Google Calendar API**, configure the OAuth consent screen, add the `.../auth/calendar.readonly` and `openid email` scopes, and configure an OAuth 2.0 Web Application client with this EXACT authorized redirect URI:

```text
https://your-existing-mlo-domain.example/life/calendars/callback
```

Put the generated client ID and secret in Portainer's stack variables. While a Google OAuth app is in Testing, add the actual Google account email addresses as test users; otherwise Google may deny access. OAuth consent verification/publishing is governed by Google policies.

Then open **Calendar → Connect calendars & accounts → Connect Google**. Choose one Google account, grant read-only permissions and press **Sync**. Repeat **Connect Google** for each additional Google account. Each account can expose several calendars. The Calendar page displays the cached events after sync.

## 3. Microsoft Outlook (multiple accounts)

In the Microsoft Entra admin center, register a Web application. Choose a supported account type covering your personal/work accounts (for example, both organizational and personal Microsoft accounts), then add the same redirect URI:

```text
https://your-existing-mlo-domain.example/life/calendars/callback
```

Grant Microsoft Graph delegated `Calendars.Read` and `User.Read`; include offline access so the app can refresh tokens. Set its **Application (client) ID** and client secret under `MLO_MS_CLIENT_ID` and `MLO_MS_CLIENT_SECRET`. Organization administrators may need to authorize delegated permissions depending on their policies.

Then click **Connect Outlook**, authorize, sync and repeat for other accounts.

## 4. Apple Calendar and other ICS subscriptions

Apple uses a separately published/shared calendar URL here, **not** Apple ID authentication. Find the calendar's sharing/subscription link in iCloud Calendar, convert `webcal://` to `https://` if necessary, and paste it under **Apple / iCalendar feed**. MLO accepts provider-issued HTTPS links for recognized Google, Microsoft, iCloud and Yahoo calendar hosts. Press **Sync** to load events.

**Privacy warning:** Apple published calendars may be accessible by anyone who knows the sharing URL. Avoid this method for private or sensitive calendars. Authenticated Apple CalDAV is not part of this release.

## 5. Safety and operational behavior

- The `MLO_CREDENTIAL_KEY` is used for authenticated provider tokens and private ICS URLs at rest.
- No OAuth token appears in exported user JSON data or the public UI.
- Sync runs on request, not in every page load; future work can schedule refresh jobs.
- External events are read-only inside MLO, and disconnecting a connection deletes that connection's cached external events.
- Requests have timeouts and the ICS host allowlist protects the server from arbitrary user-entered fetch targets.
- The site must be served over HTTPS for production OAuth and secure cookies.
- For troubleshooting, check container logs and the sanitized error displayed beside the connection. Do not share tokens or app-specific passwords.
