# MLO v3.6.3, Finance, PWA discovery and device pairing

## Improvements in this patch

1. **PWABuilder**: the public homepage now links to `/manifest.webmanifest` at the site root, with an unauthenticated route that serves the valid manifest as `application/manifest+json`. The previous `/static/manifest.webmanifest` also remains available, as does the public `/service-worker.js`. The manifest keeps the existing PWA `id` and start URL so existing installations do not lose their identity. If PWABuilder still reports no manifest, run `python tools/check_live_pwa.py https://organizer.overvault.ca` from your Windows PC and check Cloudflare Access/WAF, server image tag, and cache. The local tests cannot prove what PWABuilder sees over the internet.
2. **Finance navigation**: all seven finance views use the same visible tabs: Overview, Transactions, Budget, Monthly, Rules and Import. The left sidebar Finance link now points directly to `/finance`, rather than `/life/money`. The older money hub still exists for bookmarks.
3. **Budget saves**: switched SQLite UPSERT using `ON CONFLICT(section,name)` to an UPDATE-first write, compatible with old finance tables that lack the expected unique key. HTTP failures now show a styled error and the JavaScript form keeps unsaved inputs rather than navigating to a black 500 page. A production database with an unrelated failure still needs its container error log reviewed.
4. **ntfy QR pairing**: under Phone reminders, add a device and select Pair phone with QR code. The QR contains the official Android deep link `ntfy://<server>/<topic>?display=My+Life+Organized`. The QR endpoint checks the device owner and is marked `private, no-store`. It only guarantees automatic subscription on Android. On iPhone, use the copyable exact topic with the ntfy app; there is no documented iOS equivalent for this deep-link behavior. Keep the topic/QR secret on public ntfy.sh.
5. **Regression tests**: `tests_v363_finance_pwa_qr.py` covers the budget on a simulated legacy table, interactive save success/failure, Finance tabs, root manifest and unauthorized QR access. It now runs before GitHub's image-publishing job.

## Exact upgrade steps

1. Back up the existing `study_notifier_data` volume, including SQLite and attachments. Keep the Portainer stack and port 8001.
2. Upload **contents** of the GitHub hotfix ZIP to the root of `pierre-2005/study-notifier` (including `.github/workflows/publish-image.yml`), preserving existing other files.
3. Commit to `main`, wait for the test and publish GitHub Actions jobs to finish successfully.
4. Verify `docker-compose.yml` references `ghcr.io/pierre-2005/study-notifier:v3.6.3-finance-pwa-ntfy`, then use Portainer **Pull and redeploy** on your existing Git stack. Do not delete the existing database volume.
5. Open in a private window: `https://organizer.overvault.ca/manifest.webmanifest`, `/service-worker.js` and `/`. Then rerun PWABuilder analysis. If it still fails, run `tools/check_live_pwa.py` externally and inspect the printed status codes.
6. Test your existing Budget with a small change, visit each Finance tab, and add one personal device to test the QR on an Android phone. Keep the original records and other accounts intact.

No new environment variables or database schema migrations are needed. The QR image rendering library is added to `requirements.txt`. This release does not fix full per-user isolation of the legacy Finance database, a separately documented architectural issue.

## Technical note about the reported 500

With a fresh database, the original budget route does not reproduce the error. A database created with older finance schema may lack `UNIQUE(section, name)`, causing the old `ON CONFLICT` statement to fail. The updated save works in a test fixture without that unique key. If the live server still encounters a different SQLite or filesystem exception, check the Portainer container log during a save; this package avoids claiming an unverified exact root cause on your production DB.
