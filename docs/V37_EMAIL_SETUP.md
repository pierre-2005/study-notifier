# Account email setup for MLO v3.7

The branch now implements self-service registration with a verification link, administrator approval, resend verification, and a six-digit password-reset code. New accounts need both verification and approval before they can sign in. Existing accounts retain their current sign-in rules. Recovery codes expire after ten minutes, allow five attempts, can be used once, and revoke old sessions when consumed. Administrators can request delivery to an already verified address; they cannot choose the owner's new password or redirect recovery to a different address.

## Configure a sender

Use the installation's existing SMTP provider if one is already configured. For a new installation, Resend is one compatible example; this is an implementation example, not a requirement to purchase a particular service. Its current [SMTP guide](https://resend.com/docs/send-with-smtp) and [domain guide](https://resend.com/docs/dashboard/domains/introduction) were checked on October 23, 2026.

1. In the provider dashboard, add a domain or sending subdomain you control, for example `account.overvault.ca`.
2. Copy the exact DNS records supplied by that provider into your DNS dashboard. Wait until its domain verification succeeds. Configure SPF/DKIM and review DMARC alignment using the provider's instructions. Preserve existing domain and mail records; do not replace an existing SPF policy blindly.
3. Create a sending credential. Store it in the existing Portainer stack's environment settings, outside Git. Disable link/open tracking for account recovery messages.
4. At the approved staging/deployment step, set the existing environment variables below. No mail-provider account or DNS records were changed by this work.

| Variable | Resend example |
| --- | --- |
| `MLO_SMTP_HOST` | `smtp.resend.com` |
| `MLO_SMTP_PORT` | `587` |
| `MLO_SMTP_STARTTLS` | `true` |
| `MLO_SMTP_USER` | `resend` |
| `MLO_SMTP_PASSWORD` | Your sending API key, entered privately |
| `MLO_SMTP_FROM` | `My Life Organized <no-reply@account.overvault.ca>` |
| `MLO_PUBLIC_URL` | `https://organizer.overvault.ca` |
| `MLO_LEGAL_CONTACT_EMAIL` | A monitored support address |
| `COOKIE_SECURE` | `true` behind production HTTPS |

Port 465 uses implicit TLS automatically. Other providers work with their own submission host and credentials. Keep `SESSION_SECRET` and `MLO_CREDENTIAL_KEY` exactly as they are. The first protects sessions and queued account mail; the second protects existing calendar credentials. The Compose changes pass additional optional v3.7 settings without replacing volumes, ports, OAuth configuration, or credentials.

## Verify before opening registration to real users

In staging, use a mailbox you control. Register, check the message's sender/domain and HTTPS link, verify the address, confirm login is still blocked pending approval, approve in Users, then sign in. Request a reset code, reset the password, confirm the code cannot be reused and the old session stops working. Check inbox and spam folders and the provider's delivery log. Exercise resend and expiry. Test a second account and confirm it sees none of the first account's records or devices. A missing SMTP configuration means mail cannot be delivered; do not enable public signups before this acceptance check passes.

The application queues encrypted mail atomically with signup, attempts immediate background delivery, then retries from the scheduler every minute with a two-minute retry delay, at most ten attempts and never beyond token expiry. A scheduler-disabled staging rehearsal never sends queued mail. SMTP acceptance is not proof that a message reached an inbox. There is no new paid identity service, marketing email integration, or account-approval bypass.
