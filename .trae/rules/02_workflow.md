# Workflow (Trae Rules)

## Branches & Commits
- **Active Branch**: `ver4` (MVP Stage). Work directly here. No feature branches required.
- **Future**: Pull Requests, CI/CD, and merging to `main` (Post-MVP).
- **Commits**: `type(scope): summary [IP-XXX]`.
  - Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.
  - Example: `feat(agents): add hybrid reranker [IP-241]`

## Local Checks Before Push
- Run all CI-equivalent commands from `docs/TESTING_GUIDE.md` and confirm green.
- Do not push if any check fails locally.
- After push, verify GitHub Actions status with `gh run view`.
- If any CI job fails after push, fix immediately and re-run the full local checklist before re-pushing.

## Review & Merge (Future)
- **PRs**: Will require approval, tests, linting.
- **Merge**: Squash merge to `main`.
- **Breaking**: Add migration notes.
