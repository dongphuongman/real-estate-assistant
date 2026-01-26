# Quality Assurance (Trae Rules)

## Testing
- **Tiers**: `tests/unit/` (mocks), `tests/integration/` (modules), `tests/e2e/` (app flows).
- **Data**: Use synthetic data. No PII.
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
  - `cd frontend` then `npm ci`, `npm run lint`, `npm run test -- --ci --coverage`

## Thresholds & Linting
- **Coverage**: Unit ≥85%, Integration ≥70%, Critical ≥90%.
- **Linting**: Ruff (format/check), mypy (strict for core).
- **Security**: No secrets in code. Use `utils/api_key_validator.py`.

## Static Analysis
- No wildcard imports.
- No `print` (use logging).
- No network in unit tests (use stubs).
