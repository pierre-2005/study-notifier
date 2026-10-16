# MLO Studio v3.6.4: iPhone pairing and Windows Store preparation

## What is implemented

- **iPhone pairing:** Phones & reminders now shows a second QR for iOS. It encodes a URL on the existing MLO domain, not the ntfy topic secret. An authenticated device owner scanning it reaches a mobile page with a Copy topic button. Paste that topic in ntfy's Add subscription flow, then press Test in MLO. If the user is not signed in to MLO in Safari, they sign in first. Only the device owner can open the page. This does **not** claim automatic ntfy subscription on iPhone, because the official deep-link specification is Android-only.
- **Manifest:** valid categories, `lang`, `dir`, orientation, and two *real* screenshots of the application using a disposable demo database (desktop 1280×720, mobile 390×844). These are genuine UI renders with demonstration data, not user screenshots. You can replace them with your own sanitized captures.
- **Version:** 3.6.4; updated GitHub build image and Portainer Compose image to `ghcr.io/pierre-2005/study-notifier:v3.6.4-store-ios`.

## Screenshots: how to replace the demo images

1. Open `https://organizer.overvault.ca` in Edge or Chrome and sign into a **demo account** (avoid real names, finances, contacts, banking details, private project info).
2. Set the theme/layout you want to advertise, expand the sidebar if helpful, close popups and browser dev tools.
3. Press **Win + Shift + S**, choose rectangular snip, or open **Snipping Tool** and capture the whole app. Save as PNG. Make a landscape capture and one portrait/mobile capture (use Edge/Chrome developer device emulation, or capture the app from a mobile device).
4. Resize/crop the landscape screenshot to 1280×720 and the mobile screenshot to 390×844 or change the manifest's `sizes` fields to the **actual** pixel dimensions. Don't stretch images or include browser borders if avoidable.
5. Replace `app/static/dashboard-desktop.png` and `app/static/dashboard-mobile.png` in GitHub. Keep their paths unchanged, otherwise update the manifest. PWA screenshot declarations live in `app/static/manifest.webmanifest`.
6. Deploy, refresh PWABuilder's analysis, and separately upload polished Store listing screenshots in Microsoft Partner Center when prompted.

**Do not add every optional PWABuilder capability just to increase the score.** MLO has no implemented file-handler registration, protocol handler, Windows Widgets, background data mutations or offline private-data editing. Declaring such capabilities prematurely can make installation misleading or unsafe.

## Diagnose the downloaded Windows *test* package

1. **Extract** the complete PWABuilder test ZIP. Keep all its `.msix`/`.msixbundle`, `.cer`, `.exe`, and `.ps1` files in their original relative locations.
2. Open **PowerShell**, not the installer by double-clicking.
3. Navigate to the directory containing the test package's `install.ps1` and run `./install.ps1`. An alternative that keeps the window open is `powershell.exe -NoProfile -NoExit -File ".\install.ps1"` from that folder.
4. If you copied the MLO source kit, run `tools/windows_pwa_install_diagnostic.ps1 -PackageFolder "C:\path\to\extracted-PWABuilder-test" -RunInstaller` from an existing terminal. This writes `mlo-windows-install-report.txt` in the extracted test folder and prints signature information. It does not install or trust certificates on its own.
5. If PowerShell shows an *execution policy* error, first inspect `Get-ExecutionPolicy -List`. Do **not** disable security globally. If it reports a *signing certificate is not trusted* error, verify that the package and certificate really came from your own PWABuilder build before making any trust change. A development MSIX requires a trusted signing certificate; a Store-installed package is signed through Microsoft's Store distribution.
6. If `pwainstaller.exe` vanishes, inspect the same package folder, then share the `install.ps1` error output. Merely launching an EXE is not enough to identify the specific problem.
7. For extra Windows diagnostics run `Get-AppxLog | Select-Object -First 20 | Format-List` in PowerShell and capture relevant errors (avoid unrelated sensitive information).

## Safe release order

1. Commit source files to GitHub; wait for tests and published image.
2. Back up `/data`, then redeploy the *existing* Portainer stack (port 8001 and external URL unchanged).
3. Confirm `https://organizer.overvault.ca/manifest.webmanifest` returns JSON with `screenshots`, `categories` and `orientation` and all screenshot URLs return HTTP 200.
4. In PWABuilder, run analysis again, then package for Windows and test the result in PowerShell.
5. Reserve the app name in Partner Center and submit the production package when you are satisfied with account security and server availability.

Important: The installed PWA uses the same hosted server and data as the website, with no separate local personal database. Offline editing has not been implemented.
