# Branch Protection & Required Checks (V4)

## Overview
Protect `main` and `ver4` with required status checks to ensure quality gates before merge.

## Required Checks
- Backend CI: ruff, mypy, unit coverage (≥75 temporary, target 90), integration coverage (≥40 temporary, target 70)
- Frontend CI: eslint, jest tests + coverage (thresholds in `jest.config.ts`)
- Security CI: Bandit (fail on high severity, high confidence)

## GitHub Settings
1. Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Require status checks to pass before merging:
   - `backend` job
   - `frontend` job
   - `security` job
4. Enable “Require branches to be up to date”
5. Enable “Include administrators”
6. Repeat for `ver4`

## Notes
- Temporary thresholds are documented in [DEVELOPER_NOTES.md](file:///c:/Projects/ai-real-estate-assistant/docs/DEVELOPER_NOTES.md); raise to targets as tests improve.
- Avoid storing secrets in code; CI jobs must not echo secret values.
- MVP Pause:
  - CI jobs are currently gated by `MVP_CI_DISABLED` and will complete quickly without running heavy checks.
  - If branch protection requires specific checks, they will still report success (skipped heavy steps).
  - To fully re-enable, set `MVP_CI_DISABLED='false'` in `.github/workflows/ci.yml` (or remove the env).
