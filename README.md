# My Life Organized Studio v3.4.1 (Contrast Fix)

This is the **complete v3.4 application** with a targeted fix for the light-on-light/dark-on-white coloring defect affecting Tasks, Insights and quick-capture controls. All prior functionality and the existing theme/palette choices are retained.

**Root cause:** the v3.4 stylesheet introduced CSS variable names that did not exist in the earlier design system and fell back to white. The patch connects them to the existing theme tokens and adds explicit accessible control/label styling.

## Download and deploy

This full source package is intended for your existing GitHub → GitHub Actions → Portainer stack. Copy the contents of this folder to the root of your GitHub repository, commit to `main`, wait for the GitHub Action to build `ghcr.io/pierre-2005/study-notifier:v3.4.1-contrast`, then **Pull and redeploy** the existing Portainer Git stack.

**Do not** delete containers' database volumes, create a new stack or switch ports. Preserve existing `study_notifier_data` and `127.0.0.1:8001:8000` settings. Back up data before deployment.

- [Exact fix, tests, and upgrade precautions](docs/CONTRAST_FIX_V341.md)
- [Feature audit](docs/FEATURE_AUDIT_V34.md)
- [Calendar provider setup](docs/CALENDAR_SETUP.md)
- [Underlying architecture](docs/ARCHITECTURE.md)

This update also contains the corrected CI smoke-test dependencies (`httpx`) from the previous fix. The automated theme contrast test is `tests_v341_contrast.py`.
