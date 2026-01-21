# Developer Notes (V4)

## Overview
This document captures practical details for working on the FastAPI backend and Next.js frontend
in V4.

## Backend (FastAPI)
- Entry point: `api/main.py`
- Routers: `api/routers/*` (chat, search, tools, settings, admin, auth)
- OpenAPI:
  - Runtime schema: `http://localhost:8000/openapi.json`
  - Repo snapshot: `docs/openapi.json` (regenerate: `python scripts\export_openapi.py`)
  - Generated endpoint index: `docs/API_REFERENCE.generated.md` (regenerate: `python scripts\generate_api_reference.py`)
  - CI drift check (when enabled): fails if snapshot differs from the runtime schema generated from `api/main.py`
- Observability: `api/observability.py` adds:
  - `X-Request-ID` header to all responses
  - Per-client rate limiting for `/api/v1/*`
  - Structured JSON logs (`utils/json_logging.py`) with `event`, `request_id`, `client_id`,
    `method`, `path`, `status`, `duration_ms`
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
  - Email (optional; enables digest delivery when users opt in):
    - `SMTP_PROVIDER` (`gmail` | `outlook` | `sendgrid` | `custom`)
    - `SMTP_USERNAME` / `SMTP_PASSWORD`
    - `SMTP_FROM_EMAIL` (optional; defaults to username)
    - `SMTP_FROM_NAME` (optional; defaults to "Real Estate Assistant")
    - `SMTP_USE_TLS` / `SMTP_USE_SSL` (optional; defaults `true` / `false`)
    - `SMTP_TIMEOUT` (optional; seconds, default `30`)
    - Custom SMTP only: `SMTP_SERVER`, `SMTP_PORT`
  - `CRM_WEBHOOK_URL` (optional; enables CE CRM webhook connector)
  - `DATA_ENRICHMENT_ENABLED` (`true`/`false`; enables CE enrichment endpoint)
  - `VALUATION_MODE` (default `simple`; set to non-`simple` to disable CE valuation stub)
  - `LEGAL_CHECK_MODE` (default `basic`; set to non-`basic` to disable CE legal check stub)
  - `UPTIME_MONITOR_ENABLED` (`true`/`false`)
  - `UPTIME_MONITOR_HEALTH_URL` (default `http://localhost:8000/health`)
  - `UPTIME_MONITOR_EMAIL_TO` (ops email recipient)
  - `UPTIME_MONITOR_INTERVAL` (seconds, default `60`)
  - `UPTIME_MONITOR_FAIL_THRESHOLD` (default `3`)
  - `vector_persist_enabled` (`true`/`false`; enable Chroma persistence)
  - `CHROMA_FORCE_FASTEMBED` (`1` to force FastEmbed on Windows)
  - `FORCE_FASTEMBED` (`1` to force FastEmbed on Windows; alias)
  - `UPTIME_MONITOR_COOLDOWN_SECONDS` (default `1800`)

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

## Quality Gates
- Static rules: RuleEngine checks line length, secrets, and loop concatenations.
- Config: rules/config.py defines IGNORE_PATTERNS and MAX_LINE_LENGTH.
- Run RuleEngine (CI-equivalent):
  ```powershell
  python -m pytest -q tests\integration\test_rule_engine_clean.py
  ```
- Run RuleEngine (sample):
  ```powershell
  python -c "from rules.engine import RuleEngine; print('rules ready')"
  ```
- Lint/typecheck: keep ruff and mypy clean before commit.
- Coverage targets (CE): unit ≥90%, integration ≥70%, critical paths ≥90%.

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
- E2E (Playwright):
  ```powershell
  $env:PLAYWRIGHT_START_WEB='1'
  npx playwright test -c playwright.config.ts --reporter=list
  ```
- Playwright env vars:
  - `PLAYWRIGHT_BASE_URL` (default `http://localhost:3000`)
  - `PLAYWRIGHT_START_WEB` (`1`/`true` to auto-start Next.js dev server)
  - `PLAYWRIGHT_OUTPUT_DIR` (default `artifacts/playwright`)
  - `PLAYWRIGHT_SCREENSHOT_DIR` (default `artifacts/playwright/screenshots`)
  - `PLAYWRIGHT_LOG_DIR` (default `artifacts/playwright/logs`)
- Client configuration:
  - `NEXT_PUBLIC_API_URL` points to backend base (default `http://localhost:8000/api/v1`)
  - `NEXT_PUBLIC_API_KEY` is forwarded as `X-API-Key`
  - `userEmail` stored in `localStorage` is forwarded as `X-User-Email`
  - `modelPrefs:<email>` stored in `localStorage` caches per-user default model selection
- Chat streaming:
  - `streamChatMessage` emits text deltas parsed from `data: <text>`
  - `X-Request-ID` is available on the streaming response; the UI surfaces it for correlation

## Settings (Backend)
- Notification preferences storage: `.preferences/notification_preferences.json`
- Model preferences storage: `.preferences/model_preferences.json`
- Endpoints:
  - `GET/PUT /api/v1/settings/notifications` (requires `X-User-Email` or `?user_email=`)
  - `GET /api/v1/settings/models` (catalog only)
  - `GET/PUT /api/v1/settings/model-preferences` (requires `X-User-Email` or `?user_email=`)
- LLM selection:
  - [get_llm](file:///c:/Projects/ai-real-estate-assistant/api/dependencies.py) loads per-user model preferences
    via `X-User-Email`
  - Falls back to `settings.default_provider`/`settings.default_model` if preferences are missing or invalid

## CI/CD
- GitHub Actions workflow: `.github/workflows/ci.yml`
- Backend:
  - Lint: `ruff`
  - Type check: `mypy` (strict fail on errors)
  - Coverage gates:
    - Diff coverage (unit): `python scripts\\coverage_gate.py diff --min-coverage 90 --exclude tests/* --exclude scripts/*`
    - Diff coverage (integration): `python scripts\\coverage_gate.py diff --min-coverage 70 --exclude tests/* --exclude scripts/*`
    - Critical coverage (unit): `python scripts\\coverage_gate.py critical --min-coverage 90`
- Frontend:
  - Lint: `npm run lint`
  - Tests + coverage: `npm run test -- --ci --coverage` (thresholds enforced in `jest.config.ts`)
- Artifacts: coverage reports uploaded per job
- Docker Compose smoke:
  - CI runs a Compose smoke job that builds backend/frontend images and waits for `/health` + `/`.
  - Local equivalent: `python scripts\compose_smoke.py --ci`
- Security:
  - Static analysis: Bandit (fail on high severity/high confidence)
  - Dependency audit: pip-audit (fail on vulnerabilities)
- Temporary MVP pause:
  - CI jobs are gated by `MVP_CI_DISABLED` (workflow env).
  - Set `MVP_CI_DISABLED` to `'true'` to disable heavy steps (jobs still succeed quickly).
  - Default is `'false'` so full CI runs on pushes and PRs.

## Branch Protection
- Protect `main` and `ver4` branches with required CI checks:
  - Backend job (ruff, mypy, unit/integration coverage gates)
  - Frontend job (eslint, jest)
  - Security job (Bandit: high severity/high confidence)
- Enable “Require branches to be up to date” and “Include administrators”.

## Notes
- Do not commit secrets; use environment variables.
- In development, `auth/request-code` returns the code inline for easier testing.
- Notifications:
  - The notification scheduler starts on API startup and evaluates user preferences periodically.
  - If SMTP is not configured, email delivery is skipped (preferences are still stored).

## Monitoring
- Health endpoints:
  - `/health` (system)
  - `/api/v1/admin/health` (admin with cache/store indicators)
- Uptime monitor:
  - Module: `notifications/uptime_monitor.py`
  - Periodically runs a checker and sends alert emails on consecutive failures
  - Configurable interval, fail threshold, and alert cooldown

## Search Filters (End-to-End)
- UI (Next.js): `frontend/src/app/search/page.tsx` collects `min_price`, `max_price`, `rooms`,
  `property_type` and validates query/price range (neutral state before first search)
- Client API: `frontend/src/lib/api.ts` sends `filters` in `POST /api/v1/search` payload
- Backend Router: `api/routers/search.py` forwards `request.filters` to `store.hybrid_search`
- Vector Store: `vector_store/chroma_store.py` converts filters to Chroma format via `_build_chroma_filter`

Testing:
- Unit: `tests/unit/api/test_api_search_filters.py` (router forwards filters)
- Unit: `tests/unit/test_chroma_filters.py` (filter conversion)
- Integration: `tests/integration/api/test_api_search_filters_integration.py` (endpoint accepts filters)

## Search Sorting (End-to-End)
- UI (Next.js): `frontend/src/app/search/page.tsx` provides `sort_by` and `sort_order` controls
- Client API: `frontend/src/lib/api.ts` includes `sort_by` and `sort_order` in `POST /api/v1/search`
- Backend Router: `api/routers/search.py` forwards sort params to `store.hybrid_search`
- Vector Store: `vector_store/chroma_store.py` sorts by metadata fields (`price`, `price_per_sqm`,
  `area_sqm`, `year_built`)

Testing:
- Unit: `tests/unit/api/test_api_search_sorting.py` (router forwards sorting)
- Integration: `tests/integration/api/test_api_search_sorting_integration.py` (endpoint accepts sorting)

## Export (End-to-End)
- UI (Next.js):
  - `frontend/src/app/search/page.tsx` exports search results (format + optional columns + CSV locale options)
  - `frontend/src/app/tools/page.tsx` exports by IDs from the Compare tool
- Client API: `frontend/src/lib/api.ts` provides `exportPropertiesBySearch(...)` and `exportPropertiesByIds(...)`
- Backend Router: `api/routers/exports.py` handles `POST /api/v1/export/properties` for IDs or search
- Utils: `utils/exporters.py` supports `csv`, `xlsx`, `json`, `md`, `pdf` (columns filtering for `csv`/`xlsx`/`json`)

Testing:
- Unit: `tests/unit/api/test_api_exports.py` (formats, headers, errors)
- Integration: `tests/integration/api/test_api_exports_integration.py` (auth + validation + CSV option acceptance)

## Prompt Templates (End-to-End)
- Templates library: `ai/prompt_templates.py` (CE-safe, static catalog)
- Router: `api/routers/prompt_templates.py`
- Endpoints (requires `X-API-Key`):
  - `GET /api/v1/prompt-templates` (catalog + variable schemas)
  - `POST /api/v1/prompt-templates/apply` (render by `template_id` + `variables`)
- Placeholder syntax: `{{variable_name}}` (validated against the declared variable list)

Testing:
- Unit: `tests/unit/test_prompt_templates.py` (render/validation)
- Unit (API): `tests/unit/api/test_api_prompt_templates.py`
- Integration: `tests/integration/api/test_api_prompt_templates_integration.py`

## Local RAG (Community Edition)
- Knowledge store module: `vector_store/knowledge_store.py`
- Routers: `api/routers/rag.py` (`/api/v1/rag/upload`, `/api/v1/rag/qa`)
- Supported ingestion types (CE): `.txt`, `.md`
- Supported with optional install: `.pdf` (`pip install pypdf`), `.docx` (`pip install python-docx`)
- If nothing is indexed (only errors), the upload endpoint returns `422` with a structured error list.
- `/api/v1/rag/qa` accepts optional `provider` / `model` overrides in the JSON body; otherwise it uses per-user preferences (`X-User-Email`) or defaults.

Environment flags:
- `EMBEDDING_MODEL` via `settings.embedding_model` (FastEmbed/OpenAI)
- `vector_persist_enabled` controls Chroma persistence (`config/settings.py`)
- `RAG_MAX_FILES`, `RAG_MAX_FILE_BYTES`, `RAG_MAX_TOTAL_BYTES` control upload limits for `/api/v1/rag/upload`

Testing:
- Unit: `tests/unit/api/test_api_rag.py`
- Integration: `tests/integration/api/test_api_rag_integration.py`
