# Developer Notes (V4)

## Overview
This document captures practical details for working on the FastAPI backend and Next.js frontend in V4.

## Backend (FastAPI)
- Entry point: `api/main.py`
- Routers: `api/routers/*` (chat, search, tools, settings, admin, auth)
- Observability: `api/observability.py` adds:
  - `X-Request-ID` header to all responses
  - Per-client rate limiting for `/api/v1/*`
- Auth: API key via `X-API-Key` header (`config/settings.py` -> `API_ACCESS_KEY`)
- CORS:
  - Development: `ENVIRONMENT!=production` → `allow_origins=["*"]`
  - Production: `ENVIRONMENT=production` → `CORS_ALLOW_ORIGINS` (comma-separated list)

## Configuration
- Source: `config/settings.py` (`AppSettings`)
- Key env vars:
  - `ENVIRONMENT` (`development` | `production`)
  - `CORS_ALLOW_ORIGINS` (comma-separated URLs; used in production)
  - `API_RATE_LIMIT_ENABLED` (`true`/`false`)
  - `API_RATE_LIMIT_RPM` (requests per minute)
  - `API_ACCESS_KEY` (default `dev-secret-key` for dev)

## Testing
- Run all tests:
  ```powershell
  python -m pytest
  ```
- Unit/integration specificity:
  ```powershell
  python -m pytest tests/unit
  python -m pytest tests/integration
  ```
- Coverage (backend packages):
  ```powershell
  python -m pytest -q --cov=api --cov=config --cov-report=term-missing
  ```
- Linting:
  ```powershell
  python -m ruff check .
  ```
- Type checking:
  ```powershell
  python -m mypy
  ```

## Frontend (Next.js)
- Directory: `frontend/`
- Dev:
  ```powershell
  cd frontend
  npm install
  npm run dev
  ```
- Tests:
  ```powershell
  cd frontend
  npm test
  ```

## Notes
- Do not commit secrets; use environment variables.
- In development, `auth/request-code` returns the code inline for easier testing.

