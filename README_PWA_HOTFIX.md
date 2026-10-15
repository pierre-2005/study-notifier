# MLO v3.6.2 PWABuilder fix

PWABuilder could not see the manifest or service worker from the public home page. This release makes both discoverable without requiring login. It preserves user data, existing accounts, OAuth redirects and the active `https://organizer.overvault.ca` domain.

**Deployment:** `docs/PWABUILDER_STORE_V362.md`.

**Automated check:** `python tests_pwa_public.py` (also runs in GitHub Actions).

**Publishing status:** This is a PWA-readiness patch, **not** a submitted or approved Microsoft Store app.
