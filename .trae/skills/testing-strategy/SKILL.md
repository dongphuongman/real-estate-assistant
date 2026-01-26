name: testing-strategy
description: Comprehensive testing strategy for Backend, Frontend, and E2E.
---

# Testing Strategy
Ensure high quality through rigorous testing at all levels.

## Backend (Python)
- **Framework**: `pytest`.
- **Location**: `tests/unit`, `tests/integration`.
- **Commands**:
  - `python -m ruff check .`
  - `python -m mypy`
  - `python -m pytest -q tests/integration/test_rule_engine_clean.py`
  - `python scripts/export_openapi.py --check`
  - `python scripts/generate_api_reference.py --check`
  - `python scripts/update_api_reference_full.py --check`
  - `python -m pytest tests/unit --cov=. --cov-report=xml --cov-report=term -n auto`
  - `python scripts/coverage_gate.py diff --coverage-xml coverage.xml --min-coverage 90 --exclude tests/* --exclude scripts/* --exclude workflows/*`
  - `python scripts/coverage_gate.py critical --coverage-xml coverage.xml --min-coverage 90 --include api/*.py --include api/routers/*.py --include rules/*.py --include models/provider_factory.py --include models/user_model_preferences.py --include config/*.py`
  - `python -m pytest tests/integration --cov=. --cov-report=xml --cov-report=term -n auto`
  - `python scripts/coverage_gate.py diff --coverage-xml coverage.xml --min-coverage 70 --exclude tests/* --exclude scripts/* --exclude workflows/*`
- **Standards**:
  - Mock external services (AI providers, Database) in unit tests.
  - Use fixtures for setup/teardown.
  - Integration tests should use a test database or container.

## Frontend (TypeScript)
- **Framework**: Jest + React Testing Library.
- **Location**: `__tests__` directories co-located with components/pages.
- **Commands** (inside `frontend/`):
  - `npm ci`
  - `npm run lint`
  - `npm run test -- --ci --coverage`
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
- Verify post-push CI status with `gh run view` and fix failures immediately.
