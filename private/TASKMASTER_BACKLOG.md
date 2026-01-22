# Taskmaster Backlog (Private) — PRD Split for MVP CE

## Overview
This backlog translates PRD (Community Edition) into executable tasks and subtasks. It defines
priorities, estimates, dependencies, acceptance criteria, and test/documentation requirements.
Pro features remain out of scope for CE and are tracked elsewhere privately.

## Conventions
- IDs: TM-<EPIC>-<SEQ> (e.g., TM-CHAT-001)
- Status: pending | in_progress | completed | blocked
- Priority: high | medium | low
- Estimate: story points or days
- DoR: design ready, interfaces in place, env configured
- DoD: tests + docs + quality gates + endpoints reachable

## Epics and Tasks

### Epic: Chat Assistant
- TM-CHAT-001 (high, 3d, completed)
  - Task: Backend SSE stream `/api/v1/chat` with provider routing and rate limits
  - Subtasks:
    - Implement SSE streaming with request IDs
    - Enforce per-client rate limits
    - Provider selection via settings and ModelProviderFactory
  - Acceptance: p95 < 8s, retries work, errors mapped to 4xx/5xx
  - Tests: unit (provider init), integration (SSE), e2e (chat flow)
  - Docs: API Reference (chat), User Guide usage, Developer Notes
  - Dependencies: settings defaults, provider keys (BYOK)
  - Notes: Implemented SSE streaming with X-Request-ID, dependency overrides in tests, provider
    routing via ModelProviderFactory, and rate limiting via middleware.
  - Estimate update: Actual 2d; remaining 1d reallocated to TM-CHAT-002.
  - Follow-ups: Monitor p95 latency in production; add e2e chat flow in frontend (TM-CHAT-002).

- TM-CHAT-002 (high, 2d, completed)
  - Task: Frontend streaming chat UI with session correlation
  - Subtasks:
    - SSE client handling with progressive rendering
    - Session correlation via request IDs
    - Error states and retry UX
  - Acceptance: smooth streaming, accessible controls, error recovery
  - Tests: component/unit, integration (mock SSE)
  - Notes: Implemented streaming via `streamChatMessage` with `onStart` meta and progressive UI
    updates; request_id surfaced; retry UX added.
  - Estimate update: Actual 1.5d; 0.5d reallocated to TM-SEARCH-001 documentation polish.
  - Follow-ups: Add localization for chat UI strings; monitor frontend error rates.
  - Docs: User Guide (chat page)

- TM-CHAT-003 (high, 0.5d, completed)
  - Task: Streaming chat returns citations/sources and UI renders Sources expander
  - Subtasks:
    - Emit a final SSE `meta` event with `sources` and `session_id` on `/api/v1/chat` streaming mode
    - Update `streamChatMessage` to parse SSE JSON frames and handle `meta` events
    - Render Sources expander per assistant message in Chat UI
  - Acceptance: streaming chat text remains progressive; citations appear deterministically after stream completes; no secrets exposed; existing clients remain functional
  - Tests: unit (agent sources retrieval), integration (SSE includes meta), frontend unit (SSE parser meta)
  - Docs: API Reference (chat streaming), User Guide (chat streaming/sources), Developer Notes (SSE framing), Architecture note
  - Dependencies: TM-CHAT-001, TM-CHAT-002
  - Notes: Added `get_sources_for_query` to agents for CE-safe retrieval in streaming; streaming chat now emits `event: meta` with `sources`; Chat UI renders Sources when present.
  - Estimate update: Actual 0.25d; remaining 0.25d reallocated to backlog buffer.
  - Follow-ups: Consider limiting source payload size via truncation settings; consider structured source titles for cleaner UI display.

### Epic: Property Search (Hybrid)
- TM-SEARCH-001 (high, 3d, completed)
  - Task: Filters, sorting, and geo (radius/box) endpoints
  - Subtasks:
    - Implement filters + sort in `/api/v1/search`
    - Geo radius and bounding box filtering
    - Hybrid retrieval hooks + reranker
  - Acceptance: p95 < 2s, correct counts and sort
  - Tests: integration scenarios, geo filter correctness
  - Docs: API Reference (search), Developer Notes
  - Notes: Implemented hybrid search with filters, sorting, geo radius and bbox; RuleEngine clean.
  - Estimate update: Actual 2d; remaining 1d reallocated to TM-DOCS-001.
  - Follow-ups: Monitor p95 latency; improve BM25 weighting; extend localization.

- TM-SEARCH-002 (medium, 2d, completed)
  - Task: Frontend filters UI and neutral states
  - Subtasks:
    - Filter controls (price, rooms, type)
    - Sort controls (price, price/m², relevance)
    - Empty/neutral states
  - Acceptance: accessible UI, correct payloads
  - Tests: component/integration
  - Notes: Added true neutral state before first search; enforced query and filter validation
    (including min<=max); improved error handling and stable result keys; updated Search page tests.
  - Estimate update: Actual 1d; remaining 1d reallocated to TM-DOCS-001.
  - Docs: User Guide (search), API Reference (search), Developer Notes

- TM-SEARCH-003 (medium, 0.5d, completed)
  - Task: Add map view to Search UI (CE-safe, no API keys)
  - Subtasks:
    - Render property results on an interactive map when coordinates are available
    - Add List/Map toggle and “mappable” count
    - Keep behavior deterministic when coordinates are missing
  - Acceptance: map view renders without external keys; users can switch views; missing coords degrade gracefully
  - Tests: unit (map point/bounds utils), component (map wrapper), integration (Search page toggle)
  - Docs: User Guide (map view), Developer Notes (leaflet deps), API Reference (coords note)
  - Dependencies: TM-SEARCH-002
  - Notes: Implemented Leaflet-based map using OpenStreetMap tiles, plus a List/Map toggle and a “mappable” count.
  - Estimate update: Actual 0.25d; no remaining.
  - Follow-ups: Consider clustering for dense results; add per-property detail page map focus when available.

### Epic: Local RAG
- TM-RAG-001 (high, 3d, completed)
  - Task: Upload pipeline (parse, chunk, embed) and QA endpoint
  - Subtasks:
    - File upload handling (CE: .txt/.md; PDF/DOCX deferred to Pro)
    - Chunking + embeddings persist (Chroma, CE-safe)
    - QA endpoint with citations
  - Acceptance: upload→query < 2 min; citations present
  - Tests: ingestion/retrieval, large-file edge cases
  - Docs: User Guide, API Reference, Developer Notes
  - Dependencies: embeddings provider configured or snippet fallback
  - Notes: Implemented KnowledgeStore and RAG router; LLM optional with snippet fallback when keys absent.
  - Estimate update: Actual 2d; remaining 1d reallocated to TM-DOCS-001.
  - Follow-ups: Add PDF/DOCX parsing in CE with optional dependency; expose model selection for QA.

- TM-RAG-002 (high, 1d, completed)
  - Task: Support PDF/DOCX uploads for local RAG (optional dependencies)
  - Subtasks:
    - Parse `.pdf` and `.docx` to text via optional deps
    - Return structured 422 when nothing is indexed
    - Keep partial success behavior for mixed uploads
  - Acceptance: PDF/DOCX ingest works when deps installed; missing deps produce clear errors; tests + docs updated
  - Tests: unit (extractor), integration (mixed upload), existing RAG suite remains green
  - Docs: API Reference (RAG), User Guide (RAG), Developer Notes (RAG)
  - Notes: Added document text extractor with optional `pypdf`/`python-docx` support and improved upload error semantics.
  - Estimate update: Actual 0.5d; no remaining.
  - Follow-ups: Consider adding per-page chunk metadata for `.pdf` and `.docx` sources.

- TM-RAG-003 (high, 0.5d, completed)
  - Task: Enforce local RAG upload size limits (CE-safe)
  - Subtasks:
    - Add max files, per-file bytes, and total bytes limits via settings/env
    - Preserve partial success for oversized files; return 413 when total payload exceeds limit
    - Add unit + integration coverage for limit enforcement
  - Acceptance: large uploads are bounded; behavior is deterministic; tests + docs updated
  - Tests: unit (limit enforcement), integration (413 no-ingest path)
  - Docs: API Reference (RAG), User Guide (RAG), Developer Notes (RAG)
  - Notes: Added `RAG_MAX_FILES`, `RAG_MAX_FILE_BYTES`, `RAG_MAX_TOTAL_BYTES` and enforced limits in `/api/v1/rag/upload`.
  - Estimate update: Actual 0.5d; no remaining.

- TM-RAG-004 (medium, 0.5d, completed)
  - Task: Expose per-request model selection for local RAG QA (CE-safe)
  - Subtasks:
    - Accept JSON body for `/api/v1/rag/qa` with optional `provider`/`model`
    - Return `llm_used` and effective provider/model selection in response
    - Preserve legacy query-param support for backwards compatibility
  - Acceptance: per-request overrides work; missing keys still fall back to snippet; tests + docs updated
  - Tests: unit (request parsing + LLM override + fallback), integration (upload→qa)
  - Docs: API Reference (RAG), User Guide (RAG), Developer Notes (RAG), Architecture note
  - Notes: `/api/v1/rag/qa` now supports request-scoped model selection via `provider`/`model`, while keeping the CE-safe snippet fallback when LLM is unavailable.
  - Estimate update: Actual 0.25d; no remaining.
  - Follow-ups: Consider adding a RAG UI page to upload/query knowledge with model picker.

### Epic: Tools
- TM-TOOLS-001 (high, 2d, completed)
  - Task: UI wiring for existing tools (mortgage, compare, price, location)
  - Subtasks:
    - Forms/pages + validations
    - Results rendering + errors
  - Acceptance: correct results, input validation paths
  - Tests: unit calculators, integration endpoints
  - Docs: API Reference updates

- TM-TOOLS-002 (medium, 2d, completed)
  - Task: CE wiring to new endpoints (valuation/legal/enrichment/CRM) — stubs
  - Subtasks:
    - Forms/actions; handle disabled flags gracefully
  - Acceptance: endpoints callable; errors surfaced; no Pro data exposed
  - Tests: integration (success/error), DI flags behavior
  - Notes: Added mode/flag gating for CE stub endpoints, improved client error messages and UX
    hints, and added unit + integration coverage for success/disabled/error paths.
  - Estimate update: Actual 1d; remaining 1d reallocated to TM-DOCS-001.
  - Follow-ups: Add Pro connectors for valuation/legal/enrichment/CRM behind explicit feature flags.

### Epic: Saved Settings
- TM-SETTINGS-001 (medium, 2d, completed)
  - Task: Client-side preferences and settings page
  - Subtasks:
    - Notification preferences; model settings by email
    - Persistence via local storage
  - Acceptance: settings persist/load; validated inputs
  - Tests: UI state and serialization
  - Notes: Added Settings navigation link; Settings page now includes Identity (email), Notifications
    (including marketing emails), and Default Model selection. Implemented per-user model preferences
    backend (`/settings/model-preferences`) and applied in LLM selection via `X-User-Email`. Client
    caches model selection in `localStorage` per email.
  - Estimate update: Actual 1d; remaining 1d reallocated to TM-DOCS-001.
  - Follow-ups: Consider exposing model selection in RAG UI; add provider/model capability badges.

### Epic: Exports
- TM-EXPORTS-001 (medium, 2d, completed)
  - Task: CSV/JSON/Markdown endpoints + UI actions
  - Subtasks:
    - Export from search/compare
    - Download UX, columns selection
  - Acceptance: reproducible outputs; selected columns honored
  - Tests: content validation, delimiter/locale checks
  - Notes: Implemented export endpoint (`POST /api/v1/export/properties`) with column filtering, CSV
    delimiter/decimal options, and frontend download actions from Search and Tools > Compare.
  - Estimate update: Actual 1d; remaining 1d reallocated to TM-DOCS-001.
  - Follow-ups: Consider a dedicated Compare summary export (beyond property rows) if needed.

### Epic: Prompt Templates
- TM-PROMPT-001 (medium, 2d, completed)
  - Task: Template library + picker UI; apply endpoint
  - Subtasks:
    - Templates (listing descriptions, emails)
    - Variables form and validation
  - Acceptance: usable outputs, no runtime errors
  - Tests: rendering/validation
  - Notes: Added CE-safe prompt template catalog and render endpoint (`/api/v1/prompt-templates`,
    `/api/v1/prompt-templates/apply`), plus Tools UI section to pick templates, fill variables, and
    copy generated output.
  - Estimate update: Actual 1d; remaining 1d reallocated to TM-DOCS-001.
  - Follow-ups: Add persistence for user-defined templates (optional); add more template categories
    and localization.

### Epic: Deployment (BYOK)
- TM-DEPLOY-001 (high, 1d, completed)
  - Task: Docker Compose and env flags verification
  - Subtasks:
    - Verify Quickstart; BYOK via OpenAI or Ollama
    - Add backend/frontend services to Compose
    - Create backend/frontend Dockerfiles
    - Align Windows PowerShell commands in docs
  - Acceptance: local run in 5 min; endpoints reachable
  - Docs: Quickstart, Deployment, API Reference, User Guide, Developer Notes
  - Notes: Replaced legacy Streamlit compose with FastAPI (8000) and Next.js (3000); added
    Dockerfile.backend and frontend/Dockerfile.frontend; updated .env example with CORS and Uptime
    flags; Quickstart/Deployment use PowerShell; healthchecks added.
  - Estimate update: Actual 1d; no remaining.
  - Follow-ups: Optional Ollama service enablement docs; add CI compose smoke test.

- TM-DEPLOY-002 (high, 0.5d, completed)
  - Task: Add Docker Compose smoke test in CI (build + health)
  - Subtasks:
    - Add `scripts/compose_smoke.py` to build Compose and wait for `/health` + `/`
    - Add a CI job that runs the smoke test and always tears down containers
  - Acceptance: CI validates docker-compose build and service health without external keys; local smoke script works on Windows and Linux.
  - Tests: unit (command building + wait loop), integration (CLI dry-run wiring)
  - Docs: API Reference, User Guide, Developer Notes
  - Dependencies: TM-DEPLOY-001
  - Notes: Added `compose_smoke` CI job and a cross-platform smoke script to prevent drift in Compose/Dockerfiles.
  - Estimate update: Actual 0.25d; remaining 0.25d reallocated to TM-DOCS-001 follow-ups.
  - Follow-ups: Consider calling a minimal authenticated `/api/v1/verify-auth` check once stable.

- TM-DEPLOY-003 (high, 0.25d, completed)
  - Task: Extend Compose smoke to verify authenticated API endpoint
  - Subtasks:
    - Check `GET /api/v1/verify-auth` when `API_ACCESS_KEY` is set (send `X-API-Key`)
    - Ensure dry-run output does not print secrets
    - Update unit + integration coverage and docs
  - Acceptance: CI smoke validates `/health`, frontend `/`, and `/api/v1/verify-auth` without external keys; local smoke supports auth check when `API_ACCESS_KEY` is set.
  - Tests: unit (header pass-through + CI gating), integration (CLI dry-run wiring)
  - Docs: API Reference, User Guide, Developer Notes
  - Dependencies: TM-DEPLOY-002
  - Notes: Smoke script now performs an authenticated verify-auth check when `API_ACCESS_KEY` is available, improving confidence that auth wiring works in Compose.
  - Estimate update: Actual 0.1d; no remaining.
  - Follow-ups: None.

### Epic: QA & Security
- TM-QA-001 (high, 1d, completed)
  - Task: ruff/mypy gates and RuleEngine cleanliness
  - Subtasks:
    - Configure checks; fix violations
  - Acceptance: unit ≥90%, integration ≥70%, critical ≥90%; RuleEngine clean
  - Notes: Added RuleEngine config with IGNORE_PATTERNS (translations/templates) and
    MAX_LINE_LENGTH=120; ruff/mypy clean; repo-wide no error-level RuleEngine violations; unit
    tests for rules (coverage 91%); integration test ensures zero error severity across core.
  - Estimate update: Actual 1d; follow-up to raise unit coverage gates from 75→90 in CI post-MVP.

- TM-QA-002 (high, 1d, completed)
  - Task: Update Playwright e2e to Next.js UI (3000) and harden chat retry UX
  - Subtasks:
    - Migrate Playwright baseURL/output paths and add optional webServer auto-start
    - Replace legacy Streamlit e2e specs with Next.js smoke + observability coverage
    - Ensure chat errors surface request_id and retry does not corrupt message history
  - Acceptance: Playwright e2e runs locally, is deterministic (no external LLM keys), and produces artifacts.
  - Tests: Playwright (UI smoke + observability), frontend unit tests for chat error/retry
  - Docs: API Reference (streaming/CORS note), User Guide (request_id behavior), Developer Notes (Playwright env vars)
  - Notes: Playwright now stubs `/api/v1/chat` via route interception with CORS-exposed `X-Request-ID` to keep
    request correlation visible in browser-like environments.
  - Estimate update: Actual 0.5d; remaining 0.5d kept as buffer (no pending tasks).

- TM-QA-003 (high, 0.5d, completed)
  - Task: Re-enable CI and enforce coverage gates for PRs and critical paths
  - Subtasks:
    - Enable full CI by default (keep an env kill-switch)
    - Add coverage gating script for changed lines (diff coverage)
    - Add critical path coverage gate (core backend modules)
    - Make frontend lint/tests blocking in CI
  - Acceptance: CI runs by default; unit diff ≥90%, integration diff ≥70%, unit critical ≥90%; RuleEngine clean via integration suite
  - Tests: unit (coverage gate script), existing unit/integration suites remain green
  - Docs: API Reference, User Guide, Developer Notes
  - Notes: Added `scripts/coverage_gate.py` and wired it into CI; removed frontend `continue-on-error`; set CI default enabled with `MVP_CI_DISABLED=false`.
  - Estimate update: Actual 0.5d; no remaining.
  - Follow-ups: Consider expanding the critical module set as coverage improves; add a dedicated RuleEngine CI step if desired.

- TM-QA-004 (high, 0.25d, completed)
  - Task: Add dedicated RuleEngine CI step (fast feedback)
  - Subtasks:
    - Add a backend job step that runs the RuleEngine cleanliness integration check
    - Document the CI-equivalent RuleEngine command for contributors
  - Acceptance: CI exposes a separate RuleEngine step and fails fast on violations; docs updated
  - Tests: existing integration test (`tests/integration/test_rule_engine_clean.py`) remains green
  - Docs: API Reference, User Guide, Developer Notes
  - Notes: Inserted a dedicated RuleEngine step after mypy in `.github/workflows/ci.yml` to run `tests/integration/test_rule_engine_clean.py` early.
  - Estimate update: Actual 0.1d; no remaining.
  - Follow-ups: Consider making the RuleEngine step a required branch protection check.

- TM-QA-005 (medium, 0.2d, completed)
  - Task: Re-enable CI Jobs Post-MVP
  - Description: Reactivate all CI pipeline jobs after MVP completion
  - Acceptance Criteria: All previously disabled jobs must be successfully restored and verified
  - Priority: Medium
  - Estimated Effort: 1-2 hours
  - Notes: Removed the `MVP_CI_DISABLED` workflow kill-switch so backend/frontend/compose_smoke/pipeline_health always run; docs updated to reflect always-on CI.
  - Estimate update: Actual 0.15d; remaining 0.05d reallocated to backlog buffer.
  - Follow-ups: None.

### Epic: Docs (CE)
- TM-DOCS-001 (medium, 1d, completed)
  - Task: API Reference, User Guide, Troubleshooting updates
  - Acceptance: complete docs; navigable from README
  - Notes: Updated API Reference PowerShell streaming example, removed duplicated tool endpoint docs,
    corrected RAG upload PowerShell example, expanded Developer Notes env vars, refreshed
    Troubleshooting for V4 ports/venv, and added README doc links.
  - Estimate update: Actual 1d; no remaining.
  - Follow-ups: Consider generating API docs from OpenAPI schema in CI to reduce drift.

- TM-DOCS-002 (high, 0.5d, completed)
  - Task: Export OpenAPI schema snapshot and enforce drift check
  - Subtasks:
    - Add `scripts/export_openapi.py` to generate `docs/openapi.json` from FastAPI app
    - Add CI drift check step to ensure schema snapshot stays in sync
  - Acceptance: schema snapshot committed; drift check fails on changes until regenerated
  - Tests: unit (export/check modes), integration (schema includes core routes)
  - Notes: Added OpenAPI export utilities, committed schema snapshot, and added CI drift check (behind MVP gate).
  - Estimate update: Actual 0.5d; no remaining.
  - Follow-ups: Extend docs generation (rendered markdown) from OpenAPI if needed post-MVP.

- TM-DOCS-003 (high, 0.5d, completed)
  - Task: Generate API endpoint index from OpenAPI and enforce drift check
  - Subtasks:
    - Add OpenAPI-to-Markdown generator and CLI (`scripts\\generate_api_reference.py`)
    - Commit generated endpoint index (`docs/API_REFERENCE.generated.md`)
    - Enforce drift check in CI for the generated Markdown
  - Acceptance: generated endpoint index is deterministic; CI fails on drift; docs and tests updated
  - Tests: unit (rendering + drift), integration (schema includes core routes in generated Markdown)
  - Dependencies: TM-DOCS-002
  - Notes: Added deterministic OpenAPI→Markdown generation to keep endpoint index in sync with the committed schema snapshot.
  - Estimate update: Actual 0.25d; no remaining.
  - Follow-ups: Consider generating the full `docs/API_REFERENCE.md` from OpenAPI post-MVP to reduce manual drift further.

- TM-DOCS-004 (high, 0.5d, completed)
  - Task: Update full `docs/API_REFERENCE.md` Endpoints section from OpenAPI snapshot
  - Subtasks:
    - Add `serialize_endpoints_markdown` to OpenAPI→Markdown generator
    - Create `scripts/update_api_reference_full.py` with `--check` drift mode
    - Replace `### Endpoints` section in `docs/API_REFERENCE.md` deterministically
    - Add unit + integration tests for generator and drift
  - Acceptance: `docs/API_REFERENCE.md` Endpoints section is generated from `docs/openapi.json`; tests pass; CI gates remain clean
  - Tests: unit (`tests/unit/test_update_api_reference_full.py`), integration (`tests/integration/api/test_api_reference_full_integration.py`)
  - Docs: Developer Notes updated with command
  - Notes: Keeps manual non-endpoint content while eliminating endpoint drift; uses committed schema snapshot
  - Estimate update: Actual 0.5d; no remaining.
  - Follow-ups: Consider wiring `scripts/update_api_reference_full.py --check` into CI post-MVP alongside existing drift checks.

- TM-DOCS-005 (high, 0.1d, completed)
  - Task: Wire full API Reference drift check into CI
  - Subtasks:
    - Add CI step to run `python scripts/update_api_reference_full.py --check`
    - Document CI drift check command in Developer Notes
  - Acceptance: CI fails on drift in `docs/API_REFERENCE.md` Endpoints section; docs updated
  - Tests: existing unit/integration tests for the generator/drift remain green
  - Docs: Developer Notes (CI drift check command)
  - Dependencies: TM-DOCS-004
  - Notes: Added a dedicated CI step to enforce full API Reference drift detection; aligns with OpenAPI snapshot checks.
  - Estimate update: Actual 0.1d; no remaining.

## Cross-Cutting Requirements
- Tests: unit ≥90% coverage per module; integration ≥70%; critical paths ≥90%
- Code Quality: ruff check ., mypy strict for `api` and `agents/services`
- Security: no secrets in client; CORS pinned in prod; rate limits enforced
- Observability: structured logs, request IDs, error mapping

## Planning Artifacts
- Tracking: private backlog (this file), mark completed; adjust estimates
- Diagrams: architecture updated in `docs/ARCHITECTURE.md` when interfaces change
- Commit convention: `type(scope): description [IP-XXX]`

## Readiness
- All tasks have clear DoR/DoD and acceptance criteria; dependencies defined.
- Backlog is consistent with PRD, Architecture, and Roadmap; CE-only scope respected.
