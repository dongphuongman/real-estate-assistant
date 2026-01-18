name: python-development
description: Standards and workflows for Python development in this project.
---

# Python Development
Follow these standards for Python code in this project.

## Code Style
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- **Type Hints**: Mandatory for all function arguments and return values.
- **Docstrings**: Google style (Args, Returns, Raises).
- **Imports**: Absolute imports preferred. Group standard lib, 3rd party, local.

## Testing
- **Framework**: `pytest`.
- **Location**: `tests/unit`, `tests/integration`, `tests/e2e`.
- **Mocks**: Use `unittest.mock` or `pytest-mock`. Avoid network calls in unit tests.

## Dependency Management
- **File**: `requirements.txt` or `pyproject.toml`.
- **Virtual Env**: Ensure `.venv` or `venv` is active.

## Error Handling
- Use custom exception classes where appropriate.
- Log errors using the `logging` module, not `print`.
