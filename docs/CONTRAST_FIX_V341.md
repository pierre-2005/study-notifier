# MLO Studio v3.4.1: theme and contrast repair

## Why parts of the app turned white in dark mode

The newer `flow34.css` components used custom properties called `--surface`, `--surface-2`, `--line`, and `--text-muted`. The base app's actual palette system names those properties `--panel`, `--panel2`, `--border`, and `--muted`. Since those aliases did not exist, some components fell back to literal white (`#fff`) regardless of the theme. Light-colored text inherited from dark mode became difficult to read.

## Changes

- Connect the newer components to existing theme tokens rather than replacing the theme.
- Make Saved filters, task search, dropdowns, bulk controls, quick-capture dialog, and Insight backgrounds theme-aware.
- Give control labels, selected values, placeholders, dropdown options, and focus outlines readable colors across modes. Also use dark text on the lighter accent buttons in dark mode and minimally deepen light-mode button backgrounds for contrast.
- Leave dashboard layout, the blue welcome art, custom palette choices, project/task data, and calendar connections intact.
- Bump the application/service-worker asset version to 3.4.1, preventing the browser from reusing the old CSS.
- Incorporate the earlier GitHub Actions dependency correction for FastAPI `TestClient` (`httpx`) and run a repeatable theme-contrast browser test as a CI gate.

## Verification completed

- Backend: smoke, new features, migration, consolidation, v3.2, v3.4 suites passed.
- Browser: v3.3 and v3.4 Chromium interaction suites passed.
- New browser regression: six palettes × light/dark modes; check readable saved filters, task filters, labels, dropdowns, primary action buttons, and bulk actions; pass threshold ≥4.5:1 for tested normal text.
- Captured four test screenshots in `docs/preview/tasks-{light,dark}-{neutral,ocean}-v341.png`.

**Not verified:** actual Raspberry Pi deployment, every third-party/browser combination, and every screen in the legacy codebase. This is a targeted theme repair, not a claim of complete WCAG certification.

## Deployment: existing GitHub-to-Portainer stack

1. Back up the existing database/attachment volume; preserve the stack and `study_notifier_data` volume. No database migration is necessary for this CSS-only behavior change, but a backup remains recommended.
2. Merge the updated files into your `main` branch and commit.
3. In GitHub Actions wait for the Docker image to publish successfully as `ghcr.io/pierre-2005/study-notifier:v3.4.1-contrast`.
4. Check your GitHub `docker-compose.yml` still maps **the same existing database volume and port 8001**. Do not create another stack.
5. On the existing Portainer Git stack, use **Pull and redeploy**. Keep your current environment variables.
6. Refresh the browser after deployment; the new version query string invalidates old theme CSS. If necessary use Ctrl+Shift+R once.

The GitHub Action checks code and publishes an image. It does not itself deploy the application.
