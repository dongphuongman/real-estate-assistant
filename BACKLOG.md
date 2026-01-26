# BACKLOG (Spec-Driven, Omni Tree) — AI Real Estate Assistant V4

Generated on 26.01.2026.

## Phase 1 — Architectural Discovery

### Capability Mapping (What the system must do)

- **Identity & Access**: API access key injection via Next.js proxy; email-based OTP auth; user-scoped settings via `X-User-Email`.
- **Chat (Realtime)**: SSE streaming chat with tool invocation, request correlation, and source/citation metadata.
- **Search & Retrieval**: Hybrid retrieval (semantic + keyword), metadata filters, geo filters (radius/bbox), sorting, and reranking.
- **Tools**: Mortgage calculator, comparison, price and location analysis; safe stubs for Pro-only tools.
- **Local RAG**: Upload documents, index chunks, answer questions with citations, reset knowledge base.
- **Settings**: Notification preferences, model catalog/runtime status, per-user model preferences.
- **Notifications**: Scheduled digests and instant alerts with quiet hours and dedupe.
- **Analytics**: Mortgage widget and market/portfolio insights dashboards.
- **Exports**: CSV/JSON/Markdown (and other formats) for reproducible search and comparison outputs.
- **Admin & Ops**: Health/metrics, ingestion/reindex, and operational endpoints.
- **Observability**: Structured logs, request IDs, rate limiting, audit-aligned events.
- **Deployment**: Local Docker Compose; free-tier hosting targets; CORS pinned in production.

### Constraint Check (Risks, conflicts, and technical pressure points)

- **Secrets exposure risk**: client must never receive provider secrets; proxy must inject server-side keys only.
- **Free-tier resource limits**: bounded indexing size, controlled embeddings cost, cached model catalog, and restricted background schedulers.
- **SSE fragility**: intermediaries/proxies can buffer/terminate streams; requires heartbeats, retry semantics, and clear client recovery paths.
- **Geo + hybrid retrieval complexity**: consistent filtering across vector/keyword modalities; sorting must remain stable and explainable.
- **Provider variability**: local runtimes can be unavailable; runtime status must be explicit and actionable.
- **Testing determinism**: provider calls must be stubbed; integration tests must be reproducible without external network reliance.

### Outcome Validation (What “done” means)

- Every task below is phrased as a **user-visible outcome** and is verified by **automated tests** plus CI-equivalent checks.
- UI-related subtasks include explicit **Zero-data / Loading / Error / Populated** states.

---

## Phase 2 — Three-Level Decomposition (The Omni Tree)

### [P1-01]: Platform Security & Request Correlation (P1)
- **Outcome**: Users can safely use the app without exposed secrets; every failure is traceable via request ID.
- **SUBTASK [P1-01.1]**: Next.js API proxy hardening
  - **STEP [P1-01.1.1]**: Enforce server-side `X-API-Key` injection and strip client-supplied secrets.
  - **STEP [P1-01.1.2]**: Propagate `X-Request-ID` and preserve streaming bodies end-to-end.
  - **STEP [P1-01.1.3]**: Integration tests for proxy behavior and production safeguards.
- **SUBTASK [P1-01.2]**: Backend auth check and per-client limits
  - **STEP [P1-01.2.1]**: Implement `GET /api/v1/verify-auth` with `X-API-Key` validation and clear error detail.
  - **STEP [P1-01.2.2]**: Apply rate limiting per client identifier with safe defaults and bypass rules for health checks.
  - **STEP [P1-01.2.3]**: Integration tests for auth failures, rate limiting, and request ID headers.
- **SUBTASK [P1-01.3]**: Standard error envelope + request-id propagation
  - **STEP [P1-01.3.1]**: Normalize backend error responses and always attach `X-Request-ID`.
  - **STEP [P1-01.3.2]**: Frontend error parsing that surfaces `request_id` consistently across pages.
  - **STEP [P1-01.3.3]**: Integration tests validating request ID appears in client-visible errors.
- **Dependencies**: None

### [P1-02]: Property Search & Retrieval Pipeline (P1)
- **Outcome**: Users can find relevant listings with filters, geo constraints, and explainable sorting.
- **SUBTASK [P1-02.1]**: Search API contract and filtering
  - **STEP [P1-02.1.1]**: Define request/response models for `POST /api/v1/search` with filter and sort schemas.
  - **STEP [P1-02.1.2]**: UI state implementation
    - Zero-data: prompt for query + examples
    - Loading: skeleton results + disabled controls
    - Error: human-readable error + retry + request ID
    - Populated: results list + map + facets
  - **STEP [P1-02.1.3]**: Integration tests for filters (price/rooms/type), geo (radius/bbox), and sorting.
- **SUBTASK [P1-02.2]**: Hybrid retrieval and reranking service
  - **STEP [P1-02.2.1]**: Implement hybrid retrieval (semantic + keyword) and stable reranking with tie-breakers.
  - **STEP [P1-02.2.2]**: Add explainability fields (why matched, which signals) without leaking prompts/secrets.
  - **STEP [P1-02.2.3]**: Integration tests for relevance, truncation rules, and deterministic stubs.
- **SUBTASK [P1-02.3]**: Geo utilities and normalization
  - **STEP [P1-02.3.1]**: Normalize geo inputs (bbox/radius), validate coordinates, and clamp unreasonable radii.
  - **STEP [P1-02.3.2]**: Frontend map interactions (select center, adjust radius, clustering) with accessible controls.
  - **STEP [P1-02.3.3]**: Integration tests for geo edge cases and map utility correctness.
- **Dependencies**: [P1-01]

### [P1-03]: Chat Streaming & Tool Orchestration (P1)
- **Outcome**: Users can chat with real-time streaming responses and get tool-backed answers with sources.
- **SUBTASK [P1-03.1]**: Chat SSE API contract
  - **STEP [P1-03.1.1]**: Implement `POST /api/v1/chat` SSE with typed events (delta/meta/error) and request IDs.
  - **STEP [P1-03.1.2]**: UI state implementation
    - Zero-data: onboarding prompt + suggested questions
    - Loading: streaming placeholder + “thinking” indicator
    - Error: inline assistant apology + retry + request ID
    - Populated: message history + sources panel
  - **STEP [P1-03.1.3]**: Integration tests for streaming behavior, timeouts, and reconnection semantics.
- **SUBTASK [P1-03.2]**: Tool router and safe execution
  - **STEP [P1-03.2.1]**: Implement tool registry and validate tool inputs with schema enforcement.
  - **STEP [P1-03.2.2]**: Stream intermediate tool steps to the client without leaking secrets or PII.
  - **STEP [P1-03.2.3]**: Integration tests for tool invocation, failure modes, and deterministic stubs.
- **SUBTASK [P1-03.3]**: Session persistence
  - **STEP [P1-03.3.1]**: Persist chat sessions and replay history with stable identifiers.
  - **STEP [P1-03.3.2]**: UI history behavior (restore on refresh) with clear “new chat” flows.
  - **STEP [P1-03.3.3]**: Integration tests for persistence, replay integrity, and storage fallback.
- **Dependencies**: [P1-01]

### [P1-04]: Frontend Product Shell & State-First UX (P1)
- **Outcome**: Users can navigate all CE features with accessible, resilient UI states.
- **SUBTASK [P1-04.1]**: App shell and navigation
  - **STEP [P1-04.1.1]**: Implement layout, main navigation, and route structure.
  - **STEP [P1-04.1.2]**: UI state implementation
    - Zero-data: initial home route with clear CTAs
    - Loading: route-level pending UI (where applicable)
    - Error: global error boundary with request ID display
    - Populated: consistent header/footer and navigation affordances
  - **STEP [P1-04.1.3]**: UI tests for navigation and accessibility labels.
- **SUBTASK [P1-04.2]**: Typed API client + uniform error handling
  - **STEP [P1-04.2.1]**: Define TypeScript request/response types and runtime guards where needed.
  - **STEP [P1-04.2.2]**: Ensure every API call captures `X-Request-ID` and attaches it to thrown errors.
  - **STEP [P1-04.2.3]**: Unit tests for API client and error normalization.
- **SUBTASK [P1-04.3]**: UI state compliance across pages
  - **STEP [P1-04.3.1]**: Search page state matrix (zero/loading/error/populated) is complete and consistent.
  - **STEP [P1-04.3.2]**: Chat page state matrix (zero/loading/error/populated) is complete and consistent.
  - **STEP [P1-04.3.3]**: Settings/Analytics/Knowledge pages state matrix is complete and consistent.
- **Dependencies**: [P1-01], [P1-02], [P1-03]

### [P1-05]: Data Ingestion, Normalization, and Indexing (P1)
- **Outcome**: Operators can ingest datasets and users get searchable, normalized property records.
- **SUBTASK [P1-05.1]**: Property schema + validation
  - **STEP [P1-05.1.1]**: Enforce normalized `Property` schema (region/currency/lat/lon) with validation and defaults.
  - **STEP [P1-05.1.2]**: Implement cleaning/deduplication rules with deterministic outputs.
  - **STEP [P1-05.1.3]**: Integration tests covering schema edge cases and invalid inputs.
- **SUBTASK [P1-05.2]**: Vector store indexing + hybrid fields
  - **STEP [P1-05.2.1]**: Build indexing pipeline (chunking/embeddings/metadata) and collection naming conventions.
  - **STEP [P1-05.2.2]**: Add indexing health checks and safe fallbacks when the store is unavailable.
  - **STEP [P1-05.2.3]**: Integration tests for indexing, querying, and degradation behavior.
- **SUBTASK [P1-05.3]**: Admin operations (ingest/reindex/health)
  - **STEP [P1-05.3.1]**: Implement admin endpoints for ingest/reindex with auth and rate limiting.
  - **STEP [P1-05.3.2]**: UI state implementation
    - Zero-data: “no dataset ingested” guidance
    - Loading: progress feedback for ingest/reindex
    - Error: actionable failure messages + request ID
    - Populated: dataset stats + last run timestamps
  - **STEP [P1-05.3.3]**: Integration tests for admin flows and permission enforcement.
- **Dependencies**: [P1-01]

### [P2-01]: Local RAG Knowledge Base (P2)
- **Outcome**: Users can upload documents and receive cited answers from local knowledge.
- **SUBTASK [P2-01.1]**: Upload and indexing API
  - **STEP [P2-01.1.1]**: Implement `POST /api/v1/rag/upload` for file ingestion and chunk indexing.
  - **STEP [P2-01.1.2]**: UI state implementation
    - Zero-data: explain supported file types and limits
    - Loading: upload progress indicator
    - Error: per-file error list + retry
    - Populated: indexed chunk counts and summaries
  - **STEP [P2-01.1.3]**: Integration tests for upload validation and chunking determinism.
- **SUBTASK [P2-01.2]**: QA endpoint with citations
  - **STEP [P2-01.2.1]**: Implement `POST /api/v1/rag/qa` with `top_k` and provider/model overrides.
  - **STEP [P2-01.2.2]**: UI state implementation
    - Zero-data: prompt examples + top_k defaults
    - Loading: “asking…” indicator
    - Error: readable message + request ID
    - Populated: answer + citations list
  - **STEP [P2-01.2.3]**: Integration tests for citations, overrides, and empty-knowledge behavior.
- **SUBTASK [P2-01.3]**: Reset knowledge base
  - **STEP [P2-01.3.1]**: Implement `POST /api/v1/rag/reset` with confirmation guardrails.
  - **STEP [P2-01.3.2]**: UI state implementation
    - Zero-data: disabled reset and explanation
    - Loading: clearing indicator
    - Error: recovery path and safe rollback messaging
    - Populated: documents removed/remaining
  - **STEP [P2-01.3.3]**: Integration tests for reset idempotency and safety.
- **Dependencies**: [P1-01], [P1-04], [P1-05]

### [P2-02]: Notifications, Digests, and Quiet Hours (P2)
- **Outcome**: Users receive timely alerts and digests that respect preferences and quiet hours.
- **SUBTASK [P2-02.1]**: Notification preferences API
  - **STEP [P2-02.1.1]**: Implement `GET/POST /api/v1/settings/notifications` scoped by user email.
  - **STEP [P2-02.1.2]**: UI state implementation
    - Zero-data: defaults and opt-in explanation
    - Loading: skeleton settings form
    - Error: inline error + request ID + retry
    - Populated: saved preferences + success feedback
  - **STEP [P2-02.1.3]**: Integration tests for preference validation and persistence.
- **SUBTASK [P2-02.2]**: Digest generation pipeline
  - **STEP [P2-02.2.1]**: Generate digest content from saved searches and market insights.
  - **STEP [P2-02.2.2]**: Implement dedupe keys and storage for sent/queued alerts.
  - **STEP [P2-02.2.3]**: Integration tests for quiet hours, dedupe, and scheduling correctness.
- **SUBTASK [P2-02.3]**: Email delivery and templates
  - **STEP [P2-02.3.1]**: Render responsive email templates with safe escaping and tracking placeholders.
  - **STEP [P2-02.3.2]**: Provide a preview/test-send path guarded by config.
  - **STEP [P2-02.3.3]**: Integration tests for rendering, delivery stubs, and failure handling.
- **Dependencies**: [P1-01], [P1-05]

### [P2-03]: Prompt Templates (Realtor Copywriting) (P2)
- **Outcome**: Users can generate consistent realtor content from templates with reproducible inputs.
- **SUBTASK [P2-03.1]**: Template catalog API
  - **STEP [P2-03.1.1]**: Implement `GET /api/v1/prompt-templates` with metadata and versioning.
  - **STEP [P2-03.1.2]**: UI state implementation
    - Zero-data: “no templates available” guidance
    - Loading: list skeleton
    - Error: inline error + request ID
    - Populated: template list with search/filter
  - **STEP [P2-03.1.3]**: Integration tests for catalog retrieval and permissions.
- **SUBTASK [P2-03.2]**: Apply template API
  - **STEP [P2-03.2.1]**: Implement `POST /api/v1/prompt-templates/apply` with input validation.
  - **STEP [P2-03.2.2]**: UI state implementation
    - Zero-data: example inputs and placeholders
    - Loading: generation indicator
    - Error: retry and request ID
    - Populated: generated content with copy/export actions
  - **STEP [P2-03.2.3]**: Integration tests for deterministic stubs and safety constraints.
- **SUBTASK [P2-03.3]**: Template safety and redaction
  - **STEP [P2-03.3.1]**: Ensure prompts do not log secrets and redact sensitive inputs in logs.
  - **STEP [P2-03.3.2]**: Enforce length limits and safe formatting for generated outputs.
  - **STEP [P2-03.3.3]**: Tests for redaction and limit enforcement.
- **Dependencies**: [P1-01], [P1-03]

### [P2-04]: Exports and Reproducible Reports (P2)
- **Outcome**: Users can export search/comparison results for sharing and auditing.
- **SUBTASK [P2-04.1]**: Export API endpoints
  - **STEP [P2-04.1.1]**: Implement export endpoints that accept reproducible inputs (filters/sort/query).
  - **STEP [P2-04.1.2]**: UI state implementation
    - Zero-data: disable export until results exist
    - Loading: “exporting…” indicator
    - Error: export failure message + request ID
    - Populated: download links and format options
  - **STEP [P2-04.1.3]**: Integration tests validating exported schema and stable ordering.
- **SUBTASK [P2-04.2]**: Markdown report generator
  - **STEP [P2-04.2.1]**: Generate a shareable Markdown report with sources and assumptions.
  - **STEP [P2-04.2.2]**: Provide deterministic formatting and line-wrapping rules.
  - **STEP [P2-04.2.3]**: Tests for formatting stability and regression protection.
- **SUBTASK [P2-04.3]**: Export security and quotas
  - **STEP [P2-04.3.1]**: Enforce per-user export limits and input size bounds.
  - **STEP [P2-04.3.2]**: Prevent CSV injection and sanitize fields.
  - **STEP [P2-04.3.3]**: Tests for injection prevention and quota behavior.
- **Dependencies**: [P1-01], [P1-02]

### [P2-05]: Analytics & Market Insights (P2)
- **Outcome**: Users can understand affordability and market trends through dashboards.
- **SUBTASK [P2-05.1]**: Mortgage calculator component
  - **STEP [P2-05.1.1]**: Implement mortgage math with validated inputs and deterministic rounding.
  - **STEP [P2-05.1.2]**: UI state implementation
    - Zero-data: defaults and explanation
    - Loading: N/A (local compute)
    - Error: invalid input guidance
    - Populated: monthly payment + scenario breakdown
  - **STEP [P2-05.1.3]**: Unit tests for financial calculations and edge cases.
- **SUBTASK [P2-05.2]**: Market indices pipeline
  - **STEP [P2-05.2.1]**: Compute price indices (median/avg, YoY/YoM) with smoothing and anomaly detection.
  - **STEP [P2-05.2.2]**: Expose indices via API with pagination and regional filters.
  - **STEP [P2-05.2.3]**: Integration tests for index correctness and regression baselines.
- **SUBTASK [P2-05.3]**: Analytics UI dashboards
  - **STEP [P2-05.3.1]**: Implement analytics page components for indices and insights.
  - **STEP [P2-05.3.2]**: UI state implementation
    - Zero-data: “no data yet” and ingest guidance
    - Loading: chart skeletons
    - Error: chart fallback + request ID
    - Populated: charts and tables with export controls
  - **STEP [P2-05.3.3]**: UI tests for rendering and accessibility roles.
- **Dependencies**: [P1-02], [P1-05]

### [P3-01]: Deployment Hardening & Cost Controls (P3)
- **Outcome**: The app runs reliably on free-tier infrastructure with predictable cost.
- **SUBTASK [P3-01.1]**: Production config hardening
  - **STEP [P3-01.1.1]**: Pin CORS origins and block unsafe backend proxy targets in production.
  - **STEP [P3-01.1.2]**: Enforce secure headers and no-store rules for sensitive routes.
  - **STEP [P3-01.1.3]**: Integration tests for config guards across envs.
- **SUBTASK [P3-01.2]**: Provider budgeting and routing
  - **STEP [P3-01.2.1]**: Implement model routing policy with per-provider budgets and fallbacks.
  - **STEP [P3-01.2.2]**: Surface provider/runtime availability clearly in settings UI.
  - **STEP [P3-01.2.3]**: Integration tests for fallback selection and “provider unavailable” paths.
- **SUBTASK [P3-01.3]**: Performance verification gates
  - **STEP [P3-01.3.1]**: Add performance budgets for key endpoints (search/chat) and UI Lighthouse targets.
  - **STEP [P3-01.3.2]**: Ensure streaming flush and proxy compatibility on hosting targets.
  - **STEP [P3-01.3.3]**: Automated checks for performance regressions where feasible.
- **Dependencies**: [P1-01], [P1-02], [P1-03], [P1-04]

### [P3-02]: Regionalization & Data Expansion (P3)
- **Outcome**: Users can search and compare across regions with consistent normalization.
- **SUBTASK [P3-02.1]**: Multi-region collections
  - **STEP [P3-02.1.1]**: Partition vector store collections by country/region and document naming.
  - **STEP [P3-02.1.2]**: UI state implementation
    - Zero-data: region selector defaults and explanation
    - Loading: region switch loading state
    - Error: missing region data recovery
    - Populated: region-aware results and analytics
  - **STEP [P3-02.1.3]**: Integration tests for cross-region queries and isolation.
- **SUBTASK [P3-02.2]**: Currency normalization and FX cache
  - **STEP [P3-02.2.1]**: Implement FX conversion with cached daily rates and stable rounding.
  - **STEP [P3-02.2.2]**: Add display currency selection and consistent formatting.
  - **STEP [P3-02.2.3]**: Unit tests for conversion correctness and cache behavior.
- **SUBTASK [P3-02.3]**: Multilingual query normalization
  - **STEP [P3-02.3.1]**: Implement synonyms/transliteration normalization for search queries.
  - **STEP [P3-02.3.2]**: UI language selection with safe defaults.
  - **STEP [P3-02.3.3]**: Tests for normalization correctness and regressions.
- **Dependencies**: [P1-02], [P1-05]

### [P3-03]: Extension Points for Pro Features (P3)
- **Outcome**: CE remains secure and stable while enabling private Pro modules to plug in cleanly.
- **SUBTASK [P3-03.1]**: Provider and service interfaces
  - **STEP [P3-03.1.1]**: Define interfaces for valuation, CRM, enrichment, and legal checks.
  - **STEP [P3-03.1.2]**: Add feature flags and environment-driven wiring without exposing private behavior.
  - **STEP [P3-03.1.3]**: Integration tests for CE-safe defaults and disabled features.
- **SUBTASK [P3-03.2]**: Plugin-safe configuration boundaries
  - **STEP [P3-03.2.1]**: Validate configs and reject unknown/unsafe settings in CE mode.
  - **STEP [P3-03.2.2]**: Ensure logs redact potential identifiers and external API secrets.
  - **STEP [P3-03.2.3]**: Tests for config validation and redaction behavior.
- **SUBTASK [P3-03.3]**: API surface segregation
  - **STEP [P3-03.3.1]**: Keep Pro-only routes out of public OpenAPI or gate behind build-time flags.
  - **STEP [P3-03.3.2]**: Ensure frontend does not reference Pro-only endpoints.
  - **STEP [P3-03.3.3]**: Integration tests for OpenAPI export and route availability.
- **Dependencies**: [P1-01]

---

## Phase 4 — Execution Handover

### Next Logical Task

**[P1-01.3] Standard error envelope + request-id propagation**

Rationale: This unblocks consistent recovery UX across Search/Chat/Settings/Tools and reduces debugging time in production.

#### Affected Files (initial target set)

- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/app/search/page.tsx`
- `frontend/src/app/chat/page.tsx`
- `frontend/src/app/settings/page.tsx`
- `api/main.py`
- `api/observability.py`
- `api/routers/*.py` (where errors are raised/returned)
- `tests/integration/api/test_*` (request-id and error envelope assertions)

#### Technical Contract (Inputs / Outputs)

- **Input**: Any frontend call to `/api/v1/*` via the Next.js proxy.
- **Output (success)**: Unchanged payloads; responses continue to include `X-Request-ID`.
- **Output (error)**:
  - Frontend receives a normalized error object with:
    - `message` (human-readable)
    - `status` (HTTP status)
    - `request_id` (from `X-Request-ID`, if present)
  - UI renders: `Error` + recovery action + `request_id=...` when available.

#### Verification Plan (Boris Loop)

- Backend static checks:
  - `python -m ruff check .`
  - `python -m mypy`
- Backend tests:
  - `python -m pytest -q tests/integration/test_rule_engine_clean.py`
  - `python -m pytest tests/integration -q`
- OpenAPI/doc checks:
  - `python scripts/export_openapi.py --check`
  - `python scripts/generate_api_reference.py --check`
  - `python scripts/update_api_reference_full.py --check`
- Frontend checks:
  - `cd frontend` then `npm ci`
  - `npm run lint`
  - `npm run test -- --ci --coverage`

