# Workflow (Trae Rules)

## Branches & Commits
- **Branches**: `type/description` (e.g., `feature/reranker`, `fix/login`).
- **Commits**: `type(scope): summary [IP-XXX]`.
  - Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.
  - Example: `feat(agents): add hybrid reranker [IP-241]`

## Review & Merge
- **PRs**: Require 1 approval. Check tests, linting, secrets, docs.
- **Merge**: Squash merge to `main`. All checks must pass.
- **Breaking**: Add migration notes.
