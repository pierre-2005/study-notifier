# MLO public policy pages and Google OAuth branding

This patch is for the v3.4.3 MLO codebase. It introduces the following *public* URLs on the existing domain:

| URL | Purpose |
| --- | --- |
| `https://organizer.overvault.ca/privacy` | Privacy Policy |
| `https://organizer.overvault.ca/termsofservice` | Terms of Service |
| `https://organizer.overvault.ca/` | Public MLO homepage for new visitors; already logged-in users still go to their dashboard |

Both policy pages work **without signing in**. Visitors on the homepage can see what MLO does before they are asked to log in. Policies are linked from the public homepage, login and signup screens, and the in-app footer.

## Required: a real contact email

The pages intentionally do not invent a contact address. Set `MLO_LEGAL_CONTACT_EMAIL` to a real, monitored email address in Portainer's **Git Stack → Environment variables**. Example only: `privacy@overvault.ca`, but **only use it if you have created that mailbox or alias and can actually receive mail there**.

If not set, the pages clearly display a "contact not configured" notice. Do not submit the unfinished contact notice to Google for verification.

There are no database migrations or changes to existing project/task/calendar data. Other existing Portainer environment variables and the existing Docker volume stay unchanged.

## Install via GitHub → GitHub Actions → Portainer

1. Back up your existing MLO data volume as usual.
2. Extract `MLO_Public_Legal_Pages_GitHub_Patch.zip`.
3. Copy the files from the archive into the **root** of your existing `study-notifier` GitHub repository, preserving folder paths and the hidden `.github` directory. Replace existing files when prompted. Do not copy the archive itself as a single file.
4. Set the `MLO_LEGAL_CONTACT_EMAIL` environment variable in Portainer to your monitored contact email.
5. Commit to `refs/heads/main`, wait for the **Build and publish MLO Docker image** GitHub Action to pass. The action republishes the image tag currently referenced by your v3.4.3 Compose file.
6. In the **existing** Portainer Git stack select **Pull and redeploy**. Do not add another stack; keep port 8001 and your existing volume name.
7. Open all three public URLs **in a private/incognito browser** and ensure they load without prompting for MLO login. Check that the displayed email is correct.
8. Verify your existing login and dashboard still work.

## Fill in Google Auth Platform → Branding

- **Application homepage**: `https://organizer.overvault.ca/`
- **Application privacy policy link**: `https://organizer.overvault.ca/privacy`
- **Application terms of service link**: `https://organizer.overvault.ca/termsofservice`
- **Authorized domain**: `overvault.ca` (subject to Google ownership verification)
- **OAuth redirect URI**: `https://organizer.overvault.ca/life/calendars/callback`

The redirect URI is configured in the Google OAuth **Client** configuration, not the privacy policy fields.

Go to Google Search Console and verify ownership of the relevant domain if Google requires it. After Branding is saved and the public pages work, review **Audience → Publish app**. Publishing is distinct from sensitive-scope verification. The app may still have an unverified-app warning or need Google verification for public distribution.

## What each page documents

The privacy page covers: account data; projects/tasks/notes/finances; optional Google/Microsoft calendar data and read/write scopes; local event caching; encrypted OAuth credentials; collaboration; ntfy messages; storage; data export, retention, deletion and privacy contact; Google API Limited Use.

The terms page covers: login and approval, acceptable use, content ownership, sharing, connected calendars, limits of sync/reminders, free app pricing, service availability, and operator contact.

## Source files changed/added

- `app/main.py` (public route permissions and three endpoints)
- `app/templates/base.html` (footer links)
- `app/templates/login.html` and `app/templates/signup.html` (policy links)
- `app/templates/public_shell.html` (new shared public layout)
- `app/templates/public_privacy.html` (new)
- `app/templates/public_terms.html` (new)
- `app/templates/public_home.html` (new)
- `app/static/public-legal.css` (new responsive standalone styles)
- `docker-compose.yml` (pass `MLO_LEGAL_CONTACT_EMAIL` into the container)
- `.env.example` and `.env.production.example` (documentation)
- `.github/workflows/publish-image.yml` (legal-route smoke test)
- `tests_public_legal.py` (new)

## Legal and product limitations

This is a tailored first draft based on v3.4.3's implementation, **not legal advice**. The operator should review it for accuracy and applicable laws before publicly launching MLO. In particular:

- Confirm the legal identity of the operator, real contact method, retention/backups, hosting location, and any use of outside services.
- MLO currently has no guaranteed self-service full-account deletion workflow. The policy describes the need to contact the operator for full deletion; do not promise automatic deletion until it exists.
- If you introduce analytics, advertising, AI-based document processing, new processors or new data-sharing practices, update the policy and corresponding user consent first.
- Google production publishing and OAuth verification are separate checks. Public policies alone do not guarantee approval.

Google reference: https://support.google.com/cloud/answer/13464321
Google user data policy: https://developers.google.com/terms/api-services-user-data-policy
