# MLO Microsoft Store Launch Plan (Free Windows App)

**Status:** Planning for the next major MLO revision, not implemented or submitted in v3.4.2.  
**Researched:** October 13, 2026.  
**Recommended technology:** Existing MLO FastAPI website as a Progressive Web App (PWA), packaged for Microsoft Store with PWABuilder.

## 1. Release strategy and costs

The fastest affordable launch is an installable **Windows PWA**, not a rewrite in Electron, WinUI or .NET. It will open like a dedicated desktop application and use the same production MLO server, data, accounts, and integrations as the website. The installed Windows app will require an internet connection for private workspaces in the first Store release; the existing service worker caches static resources only, not user content.

- **Microsoft developer registration:** Microsoft's new flow waives the registration fee for new **individual developers**, in supported markets (nearly 200 at the time of research). Start at **https://storedeveloper.microsoft.com/** rather than a legacy Partner Center enrollment route. Government photo ID/selfie identity verification is required. Company onboarding is also advertised as free in the new flow, but requires company verification. Check eligibility and the final terms during enrollment.
- **Price to end users:** Select **Free** in Microsoft Partner Center. No arbitrary project/task quotas. The existing web version remains available.
- **Packaging/signing:** Microsoft recommends a Store PWA pathway using **PWABuilder** to generate Windows packages. A purchased code-signing certificate is not needed for the Store PWA route.
- **Operating costs:** The application still needs reliable hosting, backups, TLS/HTTPS, monitoring, domain/Tunnel configuration, and any paid AI/OCR APIs you choose. These are not waived by free Store publication.
- **Publisher decision:** Individual account = publication under your personal publisher identity; company account = legal business publisher identity. This decision affects Store branding and cannot simply be upgraded in place; choose consciously.

Official references: [free individual onboarding](https://learn.microsoft.com/en-us/windows/apps/publish/whats-new-individual-developer), [Microsoft developer account](https://learn.microsoft.com/en-us/windows/apps/publish/partner-center/open-a-developer-account), [PWA Store instructions](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/microsoft-store), [Windows distribution choices](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path).

## 2. Readiness blockers to resolve before public launch

| Item | Current MLO observation / requirement | Release gate |
| --- | --- | --- |
| Public HTTPS | Use a stable public hostname serving MLO over HTTPS; correct secure cookie, proxy headers and redirects | HTTPS works externally, including registration/login/logout |
| Account model | Current app was originally an admin-focused Study Notifier; independently verify v3.x user isolation and self-service account onboarding | Two strangers can register/use the app without seeing each other's data |
| Privacy and deletion | Publish a privacy policy and support page; implement user-visible account deletion, data export and retention policy | Valid URLs, tested delete/export and documented storage policy |
| Auth hardening | CSRF, rate limits, password reset, session rotation, device management, safe OAuth token encryption | Automated abuse/security checks pass |
| PWA manifest | Current `app/static/manifest.webmanifest` only declares a **180×180** icon | Add correctly sized **192×192 and 512×512** PNG assets (and ideally maskable icons), validate metadata |
| Service worker/offline | Existing service worker caches CSS/JS/image files only | Graceful offline/connection-lost screen that does not show stale private data |
| Reliability | One Raspberry Pi can fail or go offline | Backups, tested restores, monitoring and a recovery procedure are ready |
| Compatibility | Test app on Windows 10/11 with Microsoft Edge/WebView context; support keyboard and screen readers | No blank screens, stuck login, viewport overflow or critical console errors |
| Billing/importers | Syllabus and bank statement importers remain planned | Neither is a prerequisite to first Store listing; do not promise unfinished capabilities |
| Legal and licensing | Proper name/logo, age rating, third-party assets, policy compliance | Store metadata and declarations checked |

**Do not publish a localhost-only or private-LAN-only app** to the public Store. A Store PWA must be reachable by users, not just computers on your home network. Avoid distributing development admin credentials or SQLite files in the Windows package. Partner Center policies can change; confirm before submission.

## 3. Engineering implementation phases

### Phase A. Prepare the production website

1. Stabilize the GitHub Actions → GHCR → Portainer pipeline, including test dependencies **before** browser tests.
2. Verify the deployed Docker image tag, database volume, and HTTPS base URL. Back up the existing deployment and confirm migrations restore.
3. Make the app genuinely public-user-safe: self-service sign-up, password recovery, rate limiting, strict per-user data isolation, user data deletion/export, encrypted integration tokens, and secret management.
4. Add public `/privacy`, `/terms` (if applicable), `/support`, and `/status` or other support-contact surfaces. Document the hosted nature of the app and what external providers access.
5. Test non-admin accounts across Tasks, Projects, Study, Money, attachments, calendar events, reminders and shared spaces.

### Phase B. Finish PWA quality

1. Keep the web app as the single codebase with the existing `manifest.webmanifest` and `sw.js`.
2. Add 192×192 and 512×512 icons, preferably a maskable icon, accessible names, and coherent Windows tile branding. Do not redistribute licensed artwork without rights.
3. Ensure the manifest's `id`, `scope`, `start_url`, theme color and display mode correspond to the public hostname/app entry point, and do not direct users to a dead end before login.
4. Make Windows app launch, close/reopen, refresh, deep links, keyboard shortcuts, file chooser, and notification permissions behave correctly. Keep server-side data authoritative.
5. Build a clear **offline screen** while preserving the current security decision not to cache private finance/academic pages. Full offline editing and sync can be added in a later release.
6. Run [PWABuilder](https://www.pwabuilder.com/) or compatible PWA validators against the **public HTTPS URL**, correct their actionable findings, and re-test.

### Phase C. Register and package

1. Open https://storedeveloper.microsoft.com/ and create a Microsoft Store developer account using the **new, free** onboarding flow. For an individual account, use a personal Microsoft account. Complete MFA and identity verification.
2. In Microsoft Partner Center, choose **New product → MSIX or PWA app** and reserve the MLO product name (subject to availability).
3. Copy **Package ID, Publisher ID and Publisher display name** from Product Identity.
4. Enter the live MLO URL in PWABuilder; generate a **Windows package** using the matching publisher/package identity. Do not simply rename an unsigned archive.
5. Locally install and test the generated package on Windows 10 and 11 before submitting it.
6. Prepare Store screenshots (without real customer/personal data), logo, concise description, category (Productivity), support details, privacy link, age rating, and truthful feature descriptions.

### Phase D. Publish and maintain

1. Upload package(s) in Partner Center; select **Free** pricing, appropriate countries and visibility, and fill out all required disclosures.
2. Submit for **Store certification**, handle any rejection with the specific issue corrected. Review time varies; do not make a guaranteed approval promise.
3. Once accepted, share the Microsoft Store listing on your website and within MLO.
4. Continue pushing ordinary website feature fixes via GitHub Actions and Portainer. For PWAs, hosted web changes may propagate without re-submitting a package, but update/re-submit the Store package if packaged metadata, capabilities, app identity or relevant Store configuration changes.
5. Monitor crashes, session/login issues, installation failures, user feedback and privacy requests. Keep a staged release/rollback procedure.

Microsoft references: [publish PWA](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/microsoft-store), [price and availability](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/pwa/price-and-availability), [privacy and properties](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/pwa/enter-app-properties), [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies), [updating](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/pwa/publish-update-to-your-app-on-store).

## 4. Planned tasks / delivery sequence

1. **CI and deployment reliability**: fix broken action; verify a clean image build and rollout.
2. **Public-account security**: privacy isolation, registration and recovery, abuse protections, export/deletion, legal/support pages.
3. **PWA readiness**: icon sizes, offline/connection-lost UX, tested installation, accessible responsive UI.
4. **Store onboarding**: free individual registration, publisher identification and app-name reservation.
5. **Windows packaging**: PWABuilder output plus clean Windows install test.
6. **Submission**: listing, rating, privacy, pricing Free, certification, launch link.
7. **Maintenance**: Store health monitoring, bug reporting, updates and rollback.

**First Store release scope:** tasks, projects, calendar, notes, focus, personal/study/work dashboards and existing features that are confirmed stable. Do not advertise automated syllabus import, universal bank PDF parsing, fully offline data entry or universal two-way calendar sync until they ship and are tested.

## 5. Acceptance test / definition of done

- [ ] New individual developer account created using free supported flow; publisher name verified.
- [ ] MLO public production hostname is always available over HTTPS and works for arbitrary new users.
- [ ] A new user's data is inaccessible to a different user, including via raw API routes and attachments.
- [ ] Login, sign-up, reset, logout, account delete and export work inside the installed Windows app.
- [ ] Windows manifest/PWABuilder tests pass, including icons, service worker and app identity.
- [ ] The Windows package installs, launches and uninstalls cleanly on target Windows versions.
- [ ] Store listing has screenshots, disclosures, privacy URL, support contact and **Free** pricing.
- [ ] Certification is approved and the public listing is discoverable.
- [ ] Continuous deployment and Store update policy are documented, with rollback.

## 6. Integration with the two importers

The syllabus importer and statement importer should share a secure document-processing backbone: PDF/DOCX/CSV intake, parsers/OCR where required, normalized structured extraction, source attribution, confidence flags, preview/edit, duplicate checks, and explicit final confirmation. This is more economical and safer than independently implementing two opaque AI upload systems.

**Syllabus:** Course, assessments and due dates flow into Study, Tasks and Calendar. **Bank statements:** Transactions flow into Money only after reconciliation/approval. Offer deterministic local import of CSV/OFX first so basic functionality stays free; reserve costly AI/OCR for optional use with an explicit consent and resource policy. Uploaded personal/financial records must never appear in app-store screenshots or analytics payloads.
