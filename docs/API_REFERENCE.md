# API Reference

This document provides a reference for the core Python APIs of the AI Real Estate Assistant.

## V4 API

The V4 API is built with FastAPI and provides a RESTful interface for the AI Real Estate Assistant.

### Base URLs (Docker Compose)
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

### OpenAPI & Interactive Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON (runtime): `http://localhost:8000/openapi.json`
- OpenAPI JSON (repo snapshot): `docs/openapi.json` (regenerate with `python scripts\export_openapi.py`)
- Generated endpoint index (repo): `docs/API_REFERENCE.generated.md` (regenerate with `python scripts\generate_api_reference.py`)

### Authentication

The API uses API Key authentication via the `X-API-Key` header.
To configure the key, set the `API_ACCESS_KEY` environment variable (defaults to `dev-secret-key` for local development).
For production deployments, set a strong, unique key and do not expose it to untrusted clients.

### Request IDs

All API responses include an `X-Request-ID` header.
You can optionally provide your own `X-Request-ID` (letters/numbers plus `._-`, up to 128 chars)
to correlate client logs with server logs.

### Rate Limiting

The API enforces per-client request rate limits on `/api/v1/*` endpoints.

When enabled, all responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.

If you exceed the limit, you will receive:
- **Status**: `429 Too Many Requests`
- **Headers**: `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### CORS

Cross-Origin Resource Sharing (CORS) is controlled via environment:
- `ENVIRONMENT=production` pins allowed origins from `CORS_ALLOW_ORIGINS` (comma‑separated).
- `ENVIRONMENT` not `production` allows all origins (`*`) for local development.

### Quality & Stability
- Static analysis enforced: ruff (lint), mypy (types), RuleEngine (custom rules).
- CI runs RuleEngine as a dedicated step for fast feedback; run locally with `python -m pytest -q tests\integration\test_rule_engine_clean.py`.
- CI also runs a Docker Compose smoke test (build + health checks). It waits for `/health` and the frontend `/`, and also checks `/api/v1/verify-auth` when `API_ACCESS_KEY` is set. Local equivalent: `python scripts\compose_smoke.py --ci`.
- CI coverage enforcement uses `python scripts\\coverage_gate.py`:
  - Diff coverage: enforces minimum coverage on changed Python lines in a PR (excluding tests/scripts).
  - Critical coverage: enforces ≥90% line coverage on core backend modules.
- Requests/responses documented per endpoint; examples verified in tests.

Example:
```
ENVIRONMENT=production
CORS_ALLOW_ORIGINS=https://yourapp.com,https://studio.vercel.app
```

### Endpoints

## GET /api/v1/admin/health

**Summary**: Admin Health Check

**Tags**: Admin

Detailed health check for admin.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | HealthCheck |

## POST /api/v1/admin/ingest

**Summary**: Ingest Data

**Tags**: Admin

Trigger data ingestion from URLs. Downloads CSVs, processes them, and saves to local cache. Does NOT automatically reindex vector store (call /reindex for that).

**Request Body**

- Required: yes
- application/json: IngestRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | IngestResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/metrics

**Summary**: Admin Metrics

**Tags**: Admin

Return simple API metrics.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## POST /api/v1/admin/reindex

**Summary**: Reindex Data

**Tags**: Admin

Reindex data from cache to vector store.

**Request Body**

- Required: yes
- application/json: ReindexRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ReindexResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/request-code

**Summary**: Request Code

**Tags**: Auth

**Request Body**

- Required: yes
- application/json: RequestCodeBody

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/auth/session

**Summary**: Get Session

**Tags**: Auth

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-Session-Token | header | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SessionInfo |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/verify-code

**Summary**: Verify Code

**Tags**: Auth

**Request Body**

- Required: yes
- application/json: VerifyCodeBody

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SessionInfo |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/chat

**Summary**: Chat Endpoint

**Tags**: Chat

Process a chat message using the hybrid agent with session persistence.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ChatRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ChatResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/export/properties

**Summary**: Export Properties

**Tags**: Export, Export

**Request Body**

- Required: yes
- application/json: ExportPropertiesRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/prompt-templates

**Summary**: List Prompt Templates

**Tags**: Prompt Templates

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[PromptTemplateInfo] |

## POST /api/v1/prompt-templates/apply

**Summary**: Apply Prompt Template

**Tags**: Prompt Templates

**Request Body**

- Required: yes
- application/json: PromptTemplateApplyRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PromptTemplateApplyResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/rag/qa

**Summary**: Rag Qa

**Tags**: RAG

Simple QA over uploaded knowledge with citations. If LLM is unavailable, returns concatenated context as answer.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| question | query | string \| null | no |  |
| top_k | query | integer | no |  |
| provider | query | string \| null | no |  |
| model | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: no
- application/json: RagQaRequest | null

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RagQaResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/rag/upload

**Summary**: Upload Documents

**Tags**: RAG

Upload documents and index for local RAG (CE-safe). PDF/DOCX require optional dependencies; unsupported types return a 422 when nothing is indexed.

**Request Body**

- Required: yes
- multipart/form-data: Body_upload_documents_api_v1_rag_upload_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/search

**Summary**: Search Properties

**Tags**: Search

Search for properties using semantic search and metadata filters.

**Request Body**

- Required: yes
- application/json: SearchRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SearchResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/settings/model-preferences

**Summary**: Get Model Preferences

**Tags**: Settings

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ModelPreferences |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/settings/model-preferences

**Summary**: Update Model Preferences

**Tags**: Settings

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ModelPreferencesUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ModelPreferences |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/settings/models

**Summary**: List Model Catalog

**Tags**: Settings

List available model providers and their models.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[ModelProviderCatalog] |

## GET /api/v1/settings/notifications

**Summary**: Get Notification Settings

**Tags**: Settings

Get notification settings for the current user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationSettings |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/settings/notifications

**Summary**: Update Notification Settings

**Tags**: Settings

Update notification settings for the current user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: NotificationSettings

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationSettings |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/tools

**Summary**: List Tools

**Tags**: Tools

List available tools.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[ToolInfo] |

## POST /api/v1/tools/compare-properties

**Summary**: Compare Properties

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: ComparePropertiesRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ComparePropertiesResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/crm-sync-contact

**Summary**: Crm Sync Contact

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: CRMContactRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CRMContactResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/enrich-address

**Summary**: Enrich Address

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: DataEnrichmentRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataEnrichmentResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/legal-check

**Summary**: Legal Check

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: LegalCheckRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LegalCheckResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/location-analysis

**Summary**: Location Analysis

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: LocationAnalysisRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LocationAnalysisResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/mortgage-calculator

**Summary**: Calculate Mortgage

**Tags**: Tools

Calculate mortgage payments.

**Request Body**

- Required: yes
- application/json: MortgageInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MortgageResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/price-analysis

**Summary**: Price Analysis

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: PriceAnalysisRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PriceAnalysisResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/valuation

**Summary**: Valuation

**Tags**: Tools

**Request Body**

- Required: yes
- application/json: ValuationRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ValuationResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/verify-auth

**Summary**: Verify Auth

**Tags**: Auth

Verify API key authentication.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /health

**Summary**: Health Check

**Tags**: System

Health check endpoint to verify API status.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | HealthCheck |
