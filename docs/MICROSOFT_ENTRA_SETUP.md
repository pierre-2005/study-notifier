# Connect Microsoft Outlook Calendar to MLO Studio 3.5

## Prerequisites
- MLO is live at `https://organizer.overvault.ca` through your existing reverse proxy / Cloudflare Tunnel.
- You have a Microsoft Entra tenant and can register applications in it. This can be a free tenant. Registering an app is separate from purchasing a Microsoft 365 subscription.
- You can edit the **Portainer Git stack environment variables** for MLO. Never add OAuth secrets to public GitHub files.

## 1. Register an application
1. Visit https://entra.microsoft.com and sign in.
2. Choose the directory you can administer (top toolbar Directory switcher, if there are several).
3. Go to **Entra ID (Identity) → Applications → App registrations → New registration**.
4. Name: **My Life Organized**.
5. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**. This is essential if you want both Outlook.com/Hotmail and eligible university/company Microsoft 365 accounts.
6. Select Register.
7. In Overview, copy **Application (client) ID** (not the Object ID) for `MLO_MS_CLIENT_ID`.

## 2. Add Web authentication redirect
1. In your registration, open **Authentication**.
2. **Add a platform → Web** (not SPA or Mobile/Desktop).
3. Add the exact Redirect URI:
   `https://organizer.overvault.ca/life/calendars/callback`
4. Save. Leave implicit/hybrid access-token and ID-token grants disabled for this server-side authorization-code flow.
5. Do not add a tenant-specific redirect query string.

## 3. Add delegated Microsoft Graph permissions
Open **API permissions → Add a permission → Microsoft Graph → Delegated permissions**:
- `User.Read` (identify connected account)
- `Calendars.ReadWrite` (read, create, edit and delete calendar events)
- `offline_access` (renew short-lived access without signing in repeatedly)
- `openid`, `profile`, `email` (authentication and identity)

Do not choose **Application permissions** for this workflow. A work/school organization's tenant policy may require its own administrator approval, even if ordinary delegated Calendar permissions don't require it by default.

## 4. Create the client secret
Open **Certificates & secrets → Client secrets → New client secret**. Choose an expiration you can track, such as 12 months, and click Add. Copy its **Value** immediately. **Secret ID is not the secret Value.** Put the Value in `MLO_MS_CLIENT_SECRET`. Set a reminder to rotate it before expiration. Never post it into chat or a public repository.

## 5. Configure Portainer
In **Portainer → Stacks → existing MLO Git stack → Environment variables**:

```
MLO_PUBLIC_URL=https://organizer.overvault.ca
MLO_CREDENTIAL_KEY=<EXISTING_FERNET_KEY>
MLO_MS_CLIENT_ID=<APPLICATION_CLIENT_ID>
MLO_MS_CLIENT_SECRET=<CLIENT_SECRET_VALUE>
```

Keep your existing `SESSION_SECRET`, `APP_USERNAME`, `APP_PASSWORD`, volume mapping and `8001` port. Redeploy **after** GitHub Actions finishes the updated image build.

## 6. Connect and verify
1. MLO → Calendar → Connected calendars → Connect Outlook.
2. Choose your account and approve delegated permissions.
3. MLO → Calendar → New event → select the Outlook account and its calendar.
4. Make a temporary event and check that Outlook displays it; then edit/delete via MLO to verify permission.
5. Repeat the connection process for your other Microsoft accounts. You need only one MLO Entra registration.
6. MLO refreshes incoming changes in the background (default approximately 10 minutes), so you no longer need a routine Sync button. A direct write from MLO should appear in Outlook immediately after provider confirmation.

## Common issues
- `AADSTS50011`: redirect URI does not exactly match the Web redirect above.
- Consent denied / administrator required: your employer or university has restricted third-party apps. Ask that tenant's administrator.
- Connection not configured: the required Portainer variables were not forwarded into the running container; check the effective stack config and logs.
- App token refuses to decrypt: preserve the original `MLO_CREDENTIAL_KEY`.
- Calendar not listed: account may not have write permission to it; use an owned calendar for initial testing.

References:
- https://learn.microsoft.com/en-us/graph/auth-register-app-v2
- https://learn.microsoft.com/en-us/graph/permissions-reference
