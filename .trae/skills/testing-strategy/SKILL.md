name: testing-strategy
description: Comprehensive testing strategy for Backend, Frontend, and E2E.
---

# Testing Strategy
Ensure high quality through rigorous testing at all levels.

## Backend (Python)
- **Framework**: `pytest`.
- **Location**: `tests/unit`, `tests/integration`.
- **Command**: `pytest` or `./run_tests.sh`.
- **Standards**:
  - Mock external services (AI providers, Database) in unit tests.
  - Use fixtures for setup/teardown.
  - Integration tests should use a test database or container.

## Frontend (TypeScript)
- **Framework**: Jest + React Testing Library.
- **Location**: `__tests__` directories co-located with components/pages.
- **Command**: `npm test` (inside `frontend/`).
- **Standards**:
  - Test component rendering and user interactions.
  - Mock API calls using Jest mocks.

## End-to-End (E2E)
- **Framework**: Playwright.
- **Location**: `tests/e2e` (root) or `frontend/e2e`.
- **Command**: `npx playwright test`.
- **Standards**:
  - Test critical user flows (Login, Search, Chat).
  - Run against a running staging/dev environment.

## CI/CD
- Tests run automatically on PRs via GitHub Actions (`.github/workflows/ci.yml`).
- Maintain coverage thresholds (Rule 3).
