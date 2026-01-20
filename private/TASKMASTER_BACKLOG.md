# Taskmaster Backlog (Private) — PRD Split for MVP CE

## Overview
This backlog translates PRD (Community Edition) into executable tasks and subtasks. It defines priorities, estimates, dependencies, acceptance criteria, and test/documentation requirements. Pro features remain out of scope for CE and are tracked elsewhere privately.

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
  - Notes: Implemented SSE streaming with X-Request-ID, dependency overrides in tests; provider routing via ModelProviderFactory; rate limiting via middleware.
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
  - Notes: Implemented streaming via `streamChatMessage` with `onStart` meta and progressive UI updates; request_id surfaced; retry UX added.
  - Estimate update: Actual 1.5d; 0.5d reallocated to TM-SEARCH-001 documentation polish.
  - Follow-ups: Add localization for chat UI strings; monitor frontend error rates.
  - Docs: User Guide (chat page)

### Epic: Property Search (Hybrid)
- TM-SEARCH-001 (high, 3d, pending)
  - Task: Filters, sorting, and geo (radius/box) endpoints
  - Subtasks:
    - Implement filters + sort in `/api/v1/search`
    - Geo radius and bounding box filtering
    - Hybrid retrieval hooks + reranker
  - Acceptance: p95 < 2s, correct counts and sort
  - Tests: integration scenarios, geo filter correctness
  - Docs: API Reference (search), Developer Notes

- TM-SEARCH-002 (medium, 2d, pending)
  - Task: Frontend filters UI and neutral states
  - Subtasks:
    - Filter controls (price, rooms, type)
    - Sort controls (price, price/m², relevance)
    - Empty/neutral states
  - Acceptance: accessible UI, correct payloads
  - Tests: component/integration
  - Docs: User Guide (search)

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

### Epic: Tools
- TM-TOOLS-001 (high, 2d, completed)
  - Task: UI wiring for existing tools (mortgage, compare, price, location)
  - Subtasks:
    - Forms/pages + validations
    - Results rendering + errors
  - Acceptance: correct results, input validation paths
  - Tests: unit calculators, integration endpoints
  - Docs: API Reference updates

- TM-TOOLS-002 (medium, 2d, pending)
  - Task: CE wiring to new endpoints (valuation/legal/enrichment/CRM) — stubs
  - Subtasks:
    - Forms/actions; handle disabled flags gracefully
  - Acceptance: endpoints callable; errors surfaced; no Pro data exposed
  - Tests: integration (success/error), DI flags behavior

### Epic: Saved Settings
- TM-SETTINGS-001 (medium, 2d, pending)
  - Task: Client-side preferences and settings page
  - Subtasks:
    - Notification preferences; model settings by email
    - Persistence via local storage
  - Acceptance: settings persist/load; validated inputs
  - Tests: UI state and serialization

### Epic: Exports
- TM-EXPORTS-001 (medium, 2d, pending)
  - Task: CSV/JSON/Markdown endpoints + UI actions
  - Subtasks:
    - Export from search/compare
    - Download UX, columns selection
  - Acceptance: reproducible outputs; selected columns honored
  - Tests: content validation, delimiter/locale checks

### Epic: Prompt Templates
- TM-PROMPT-001 (medium, 2d, pending)
  - Task: Template library + picker UI; apply endpoint
  - Subtasks:
    - Templates (listing descriptions, emails)
    - Variables form and validation
  - Acceptance: usable outputs, no runtime errors
  - Tests: rendering/validation

### Epic: Deployment (BYOK)
- TM-DEPLOY-001 (high, 1d, pending)
  - Task: Docker Compose and env flags verification
  - Subtasks:
    - Verify Quickstart; BYOK via OpenAI or Ollama
  - Acceptance: local run in 5 min; endpoints reachable
  - Docs: Quickstart, Deployment

### Epic: QA & Security
- TM-QA-001 (high, ongoing, pending)
  - Task: ruff/mypy gates and RuleEngine cleanliness
  - Subtasks:
    - Configure checks; fix violations
  - Acceptance: unit ≥90%, integration ≥70%, critical ≥90%; RuleEngine clean
  - Notes: Temporary MVP pause—CI heavy steps gated via `MVP_CI_DISABLED`. Post-MVP, re-enable gates and raise thresholds to targets.

### Epic: Docs (CE)
- TM-DOCS-001 (medium, 2d, pending)
  - Task: API Reference, User Guide, Troubleshooting updates
  - Acceptance: complete docs; navigable from README

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
