# Code Organization (Trae Rules)

## Structure & Naming
- **Core**: `agents/`, `ai/`, `models/`, `vector_store/`, `analytics/`.
- **Support**: `data/`, `ui/`, `utils/`, `config/`, `notifications/`.
- **Tests**: `tests/{unit,integration,e2e}/`.
- **Files**: `snake_case.py`, `PascalCase` classes, `UPPER_SNAKE` constants.
- **Scripts**: Root level (e.g., `app_modern.py`).

## Principles
- **Imports**: Use absolute imports. Avoid deep nesting (>3 levels).
- **Size**: Refactor modules >400-600 LOC.
- **Interfaces**: Export via `__init__.py`. Use `models/provider_factory.py` for abstractions.
- **Layering**: UI -> Agents -> Providers -> Vector Store -> Data.
- **Dependencies**: UI shouldn't import agents directly. Cross-package via interfaces.
