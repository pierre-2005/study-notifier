# Google Search Console: “Deceptive pages” with Sample URLs: N/A

A Google **Security issues → Deceptive pages** warning is distinct from Google OAuth's branding, scope and identity verification. `Sample URLs: N/A` does **not** mean the warning is a false positive, and it does not prove that the MLO website itself is the flagged location.

## Scope the problem first
1. Open https://search.google.com/search-console and look at the **selected property**.
   - **Domain property `overvault.ca`** covers the root domain and all subdomains, not only MLO.
   - **URL-prefix property `https://organizer.overvault.ca/`** covers MLO under that prefix.
2. Check which property shows the warning. If it is the root domain, inspect all websites and services under it.
3. In Search Console, open **Settings → Users and permissions** and verify that no unknown owner/delegate has been added.

## Investigation checklist
- Inspect homepage, login, signup, privacy and terms pages from an incognito browser and a separate phone/network. Look for unexpected redirects and unfamiliar forms.
- Check Cloudflare DNS records, Tunnel hostname mappings, and unknown applications routed to your domain. Do not delete legitimate records without identifying their purpose.
- Examine third-party JavaScript, embedded iframes, redirects, downloadable files, and unfamiliar links.
- Check server access logs for unknown requests or unexpected redirects. Scan your web directory and Docker containers for unauthorized changes.
- Search for unfamiliar pages with `site:overvault.ca` and `site:organizer.overvault.ca`.
- Compare files served by the production container with your expected GitHub release.
- Examine any Google Safe Browsing warning Chrome presents; do not bypass it to collect credentials.
- Review server credentials, Cloudflare access, GitHub permissions and Portainer access. Rotate credentials **if there is evidence of compromise**; back up first and preserve evidence.

## Request a review
- **If a problem is found**, correct it, fix the entry point, and request review explaining what was changed.
- **If no sample URLs are provided and your investigation finds no deceptive content**, Google's own Search Central documentation allows you to request a review explaining the checks and that you believe the flag may be mistaken. Do not claim to have removed malware that you did not find.
- Reviews may take time. A rejection may provide more detail, or you may need to investigate further.

Example factual review text (edit to match what you actually checked):

> I investigated the affected Search Console property, including its public pages, login flow, redirects, third-party resources, site ownership, DNS and hosted applications. Google did not provide sample URLs. I did not identify social-engineering content in the pages I inspected. Please review the classification and, if the issue remains, provide actionable examples where possible.

This is not a security clearance and cannot guarantee a successful Google review. Resolve any real security findings before making the app publicly available.

Official documentation: https://developers.google.com/search/docs/monitor-debug/security/social-engineering
