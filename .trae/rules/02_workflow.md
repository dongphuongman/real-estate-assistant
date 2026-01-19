# Workflow (Trae Rules)

## Branches & Commits
- **Active Branch**: `ver4` (MVP Stage). Work directly here. No feature branches required.
- **Future**: Pull Requests, CI/CD, and merging to `main` (Post-MVP).
- **Commits**: `type(scope): summary [IP-XXX]`.
  - Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.
  - Example: `feat(agents): add hybrid reranker [IP-241]`

## Review & Merge (Future)
- **PRs**: Will require approval, tests, linting.
- **Merge**: Squash merge to `main`.
- **Breaking**: Add migration notes.
