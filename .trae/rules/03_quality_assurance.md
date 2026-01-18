# Quality Assurance (Trae Rules)

## Testing
- **Tiers**: `tests/unit/` (mocks), `tests/integration/` (modules), `tests/e2e/` (app flows).
- **Data**: Use synthetic data. No PII.
- **Commands**: `python -m pytest`, `python -m ruff check .`, `python -m mypy`.

## Thresholds & Linting
- **Coverage**: Unit ≥85%, Integration ≥70%, Critical ≥90%.
- **Linting**: Ruff (format/check), mypy (strict for core).
- **Security**: No secrets in code. Use `utils/api_key_validator.py`.

## Static Analysis
- No wildcard imports.
- No `print` (use logging).
- No network in unit tests (use stubs).
