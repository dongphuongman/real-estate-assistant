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
To configure the key, set either:
- `API_ACCESS_KEY` (single key), or
- `API_ACCESS_KEYS` (comma-separated list for key rotation; any listed key is accepted).
Keys are normalized by trimming whitespace, dropping empty entries, and de-duplicating (first occurrence wins).
If neither is set and `ENVIRONMENT` is not `production`, the API defaults to `dev-secret-key`.
In `ENVIRONMENT=production`, missing keys (or using `dev-secret-key`) is treated as an invalid configuration.
For production deployments, set a strong, unique key and do not expose it to untrusted clients.
In the web app, API calls are proxied server-side by Next.js so the browser does not need (and must not embed) the API key.
The proxy injects `X-API-Key` from `API_ACCESS_KEY` (or falls back to the first entry in `API_ACCESS_KEYS`) and intentionally ignores `NEXT_PUBLIC_*` secrets.
In production, the proxy requires `BACKEND_API_URL` and rejects localhost targets to avoid misconfigured deployments.
The repository enforces this policy with `python scripts\forbidden_tokens_check.py`.
For staged key rotation and revocation guidance, see `docs/SECURITY.md` (API Key Rotation & Staged Revocation).

### Request IDs

All API responses include an `X-Request-ID` header.
You can optionally provide your own `X-Request-ID` (letters/numbers plus `._-`, up to 128 chars)
to correlate client logs with server logs.
The header is included on error responses (including unexpected `500` errors) and is exposed to browser
JavaScript via `Access-Control-Expose-Headers: X-Request-ID` when CORS applies.

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

### Notifications (Email)

- Notification settings are managed via `GET/PUT /api/v1/settings/notifications`.
- If SMTP is configured, the backend scheduler sends digests and (optional) instant alerts.
- If backend code uses `get_text("<literal>")` for localized strings, tests enforce that the key exists in `i18n/translations.py`.

### Settings: Model Catalog Runtime Status

`GET /api/v1/settings/models` returns a catalog of providers/models. For local providers (`is_local=true`), the API includes runtime diagnostics to help operators and users troubleshoot local runtimes (e.g., Ollama):
- `runtime_available`: whether the local runtime is reachable
- `available_models`: models detected as installed/available on the runtime (may be empty)
- `runtime_error`: a human-readable hint when `runtime_available=false`

Example (local runtime unavailable):

```json
[
  {
    "name": "ollama",
    "display_name": "Ollama (Local)",
    "is_local": true,
    "requires_api_key": false,
    "models": [],
    "runtime_available": false,
    "available_models": [],
    "runtime_error": "Could not connect to Ollama. Make sure Ollama is running (ollama serve)"
  }
]
```
- When quiet hours are enabled, instant alerts are queued and delivered after quiet hours end.

### Search & Mapping

- `POST /api/v1/search` returns `SearchResponse.results[].property.latitude` and `SearchResponse.results[].property.longitude` when available.
- Clients should treat coordinates as optional and handle `null` / missing values.
- For dense result sets, clients may cluster markers by zoom to keep the map readable (client-side only).
- In the web app, cluster markers are clickable and zoom in by fitting to the cluster bounds (client-side only).

### Chat Streaming (SSE)

To stream chat responses, set `"stream": true` in `POST /api/v1/chat`.

The response uses Server-Sent Events (`text/event-stream`) with:
- Text deltas as JSON: `data: {"content":"<delta>"}`
- A final metadata event: `event: meta` with `data: {"sources":[...],"sources_truncated":false,"session_id":"..."}`
- A terminator: `data: [DONE]`

To keep responses deterministic and safe for clients, the server may truncate the `sources` payload
(number of items and per-source content length). Configure via:
- `CHAT_SOURCES_MAX_ITEMS`
- `CHAT_SOURCE_CONTENT_MAX_CHARS`
- `CHAT_SOURCES_MAX_TOTAL_BYTES`

PowerShell example (prints raw SSE frames):
```powershell
$env:API_ACCESS_KEY="dev-secret-key"
curl.exe -N `
  -H "X-API-Key: your-api-key" `
  -H "Content-Type: application/json" `
  -d "{\"message\":\"Hello\",\"stream\":true}" `
  "http://localhost:8000/api/v1/chat"
```

### Local RAG (Upload + QA)

The API supports local-first question answering over documents you upload.

- Web app: use the **Knowledge** tab (calls the endpoints below)
- API: use `POST /api/v1/rag/upload` then `POST /api/v1/rag/qa`
- Citations in `/api/v1/rag/qa` include `source` + `chunk_index`, and may also include `page_number` (PDF) or `paragraph_number` (DOCX).

Upload example (PowerShell):
```powershell
$env:API_ACCESS_KEY="dev-secret-key"

$form = @{
  files = @(
    Get-Item .\notes.md,
    Get-Item .\contract.txt
  )
}

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/rag/upload" `
  -Method Post `
  -Headers @{ "X-API-Key" = $env:API_ACCESS_KEY } `
  -Form $form
```

Upload response shape (example):
```json
{
  "message": "Upload processed",
  "chunks_indexed": 12,
  "errors": []
}
```

Reset knowledge (PowerShell):
```powershell
$env:API_ACCESS_KEY="dev-secret-key"

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/rag/reset" `
  -Method Post `
  -Headers @{ "X-API-Key" = $env:API_ACCESS_KEY }
```

Reset response shape (example):
```json
{
  "message": "Knowledge cleared",
  "documents_removed": 12,
  "documents_remaining": 0
}
```

Ask example (PowerShell):
```powershell
$env:API_ACCESS_KEY="dev-secret-key"

$body = @{
  question = "Summarize the contract termination clause"
  top_k = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/rag/qa" `
  -Method Post `
  -Headers @{ "X-API-Key" = $env:API_ACCESS_KEY; "Content-Type" = "application/json" } `
  -Body $body
```

### Quality & Stability
- Static analysis enforced: ruff (lint), mypy (types), RuleEngine (custom rules).
- For full CI parity commands on Windows, see `docs/TESTING_GUIDE.md`.
- CI runs RuleEngine as a dedicated step for fast feedback; run locally with `python -m pytest -q tests\integration\test_rule_engine_clean.py`.
- CI runs OpenAPI and API Reference drift checks to keep `docs/openapi.json` and endpoint docs in sync.
- CI also runs a Docker Compose smoke test (build + health checks). It waits for `/health` and the frontend `/`, and also checks `/api/v1/verify-auth` when `API_ACCESS_KEY` is set. Local equivalent: `python scripts\compose_smoke.py --ci`.
- Some internal/legacy modules may require optional Python packages (for example `ai/agent.py` requires `langchain-experimental`); the V4 API does not require these optional deps.
- CI coverage enforcement uses `python scripts\\coverage_gate.py`:
  - Diff coverage: enforces minimum coverage on changed Python lines in a PR (excluding tests/scripts).
  - Critical coverage: enforces ≥90% line coverage on core backend modules.
- Requests/responses documented per endpoint; examples verified in tests.

Example:
```powershell
$env:ENVIRONMENT="production"
$env:CORS_ALLOW_ORIGINS="https://yourapp.com,https://studio.vercel.app"
```

Example (Admin notifications queue stats):
```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/admin/notifications-stats" `
  -Method Get `
  -Headers @{ "X-API-Key" = $env:API_ACCESS_KEY }
```

Example response:
```json
{
  "scheduler_running": true,
  "alerts_storage_path": ".alerts",
  "sent_alerts_total": 42,
  "pending_alerts_total": 3,
  "pending_alerts_by_type": {
    "price_drop": 1,
    "new_property": 2
  },
  "pending_alerts_oldest_created_at": "2026-01-24T10:00:00",
  "pending_alerts_newest_created_at": "2026-01-24T12:00:00"
}
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

## GET /api/v1/admin/notifications-stats

**Summary**: Admin Notifications Stats

**Tags**: Admin

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationsAdminStats |

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

## POST /api/v1/rag/reset

**Summary**: Reset Rag Knowledge

**Tags**: RAG

Clear all indexed knowledge documents for local RAG (CE-safe).

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RagResetResponse |

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
