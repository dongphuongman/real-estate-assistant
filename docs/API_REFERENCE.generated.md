# API Reference (Generated)

This file is generated from the committed OpenAPI schema snapshot (`docs/openapi.json`).
- Source title: AI Real Estate Assistant - Modern
- Source version: 3.0.0

To regenerate:

```powershell
python scripts\export_openapi.py
python scripts\generate_api_reference.py
```

---

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
