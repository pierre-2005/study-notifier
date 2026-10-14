# Windows app, same hosted MLO data

**Design decision:** The Windows application will be a packaged Progressive Web App (PWA) pointed at `https://organizer.overvault.ca`. It is not a second installation of FastAPI or a separate local database. Everyone authenticates to the same hosted server and the server stores tasks, projects, local calendar events and connected-account credentials in the same existing `/data` Docker volume.

### What happens when you use MLO on different devices?
- Open the website in Edge/Chrome on Windows, or install the PWA as a standalone app: both connect to the same HTTPS origin and user account.
- Create a task/event on Windows → server writes the data → your next website page load displays that record, and vice versa.
- No independent Windows database needs manual synchronization.
- Offline is limited. The service worker caches **static assets only**; private records, passwords and OAuth tokens are not cached on disk by the service worker. Offline edits are not implemented.
- If the Raspberry Pi or Internet connection is down, remote operations will not work; plan backups, monitoring and reliable HTTPS hosting.

### Already prepared for packaging
- Updated manifest with 192px and 512px icons, standalone mode and navigation shortcuts.
- A service worker limited to static assets.
- A real hosted HTTPS URL and public privacy/terms pages already established in earlier work.

### Store submission is a separate step, not completed by this release
1. Verify website and privacy/security status; resolve any deceptive-page warnings.
2. Run https://www.pwabuilder.com/ against your **live URL** and address the PWA report-card findings.
3. Generate a Microsoft Store package through PWABuilder and test on a Windows machine.
4. Register in Microsoft Partner Center through https://storedeveloper.microsoft.com/ (new free registration path for eligible developers).
5. Submit the package, screenshots, age ratings, support contact and privacy policy for Store review.
6. Maintain the server. Web code/content updates usually appear without a new Store package, but manifest/package-related changes can require a new submission.

Avoid hard-coding secrets inside any Windows client or MSIX package; all OAuth secrets and encryption keys stay on the server.

Official Microsoft guidance:
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path
- https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/pwa/turn-your-website-pwa
- https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/microsoft-store
