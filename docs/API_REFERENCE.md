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

#### System

*   `GET /health`
    *   Health check endpoint to verify API status.
    *   **Returns**: `{"status": "healthy", "version": "..."}`

#### Auth

*   `GET /api/v1/verify-auth`
    *   Verify API key validity.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Returns**: `{"message": "Authenticated successfully", "valid": true}`
*   `POST /api/v1/auth/request-code`
    *   Request a one-time login code sent to email (dev returns code inline).
    *   **Body**:
        ```json
        { "email": "user@example.com" }
        ```
    *   **Returns**:
        ```json
        { "status": "code_sent" }
        ```
      In development:
        ```json
        { "status": "code_sent", "code": "123456" }
        ```
*   `POST /api/v1/auth/verify-code`
    *   Verify the one-time code and create a session.
    *   **Body**:
        ```json
        { "email": "user@example.com", "code": "123456" }
        ```
    *   **Returns**:
        ```json
        { "session_token": "<token>", "user_email": "user@example.com" }
        ```
*   `GET /api/v1/auth/session`
    *   Fetch current session info.
    *   **Headers**: `X-Session-Token: <token>`
    *   **Returns**:
        ```json
        { "session_token": "<token>", "user_email": "user@example.com" }
        ```

#### Search

*   `POST /api/v1/search`
    *   Search for properties using hybrid search (Semantic + Keyword) and metadata filters.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "query": "2 bedroom apartment in Krakow with balcony",
          "limit": 10,
          "filters": {
            "city": "Krakow",
            "min_price": 200000,
            "max_price": 800000,
            "rooms": 2,
            "property_type": "apartment"
          },
          "alpha": 0.7,
          "lat": 50.0647,
          "lon": 19.9450,
          "radius_km": 3.0,
          "min_lat": 50.00,
          "max_lat": 50.12,
          "min_lon": 19.85,
          "max_lon": 20.05,
          "sort_by": "price",
          "sort_order": "asc"
        }
        ```
    *   **Parameters**:
        *   `query` (string, required): Non-empty natural language search query.
        *   `alpha` (float, optional): Weight for vector similarity (0.0 to 1.0). 1.0 = Pure Vector,
            0.0 = Pure Keyword. Default: 0.7.
        *   `lat/lon/radius_km` (optional): Geo radius filter (in kilometers).
        *   `min_lat/max_lat/min_lon/max_lon` (optional): Geo bounding box filter.
        *   `sort_by` (optional): `relevance`, `price`, `price_per_sqm`, `area_sqm`, `year_built`.
        *   `sort_order` (optional): `asc` or `desc`. Defaults: `sort_by=relevance`, `sort_order=desc`.
        *   `filters` (object, optional): Metadata filters. Supported keys include:
            *   `city` (string)
            *   `min_price` / `max_price` (number)
            *   `rooms` (number; treated as minimum rooms)
            *   `property_type` (string; one of: `apartment`, `house`, `studio`, `loft`, `townhouse`, `other`)
        *   Client-side validation (recommended): Ensure `min_price <= max_price` before submitting.
    *   **Returns**: `SearchResponse` object containing list of properties with hybrid scores.

#### RAG (Local Knowledge, CE)

*   `POST /api/v1/rag/upload`
    *   Upload text/markdown documents and index for local RAG (Community Edition).
    *   **Headers**: `X-API-Key: your-api-key
    *   **Form Data**:
        - `files`: One or more files (`text/plain`, `text/markdown`, `.txt`, `.md`, `.pdf`, `.docx`)
    *   **Returns**:
        ```json
        { "message": "Upload processed", "chunks_indexed": 12, "errors": [] }
        ```
    *   **Notes**:
        - Upload limits are configurable via env (`RAG_MAX_FILES`, `RAG_MAX_FILE_BYTES`, `RAG_MAX_TOTAL_BYTES`)
        - Files exceeding `RAG_MAX_FILE_BYTES` are skipped and reported in `errors` (partial success supported)
        - If the total uploaded bytes exceed `RAG_MAX_TOTAL_BYTES`, the API returns `413` and indexes nothing:
          ```json
          {
            "detail": {
              "message": "Upload payload too large",
              "max_total_bytes": 26214400,
              "total_bytes": 30000000,
              "errors": ["..."]
            }
          }
          ```
        - PDF parsing requires optional dependency: `pip install pypdf`
        - DOCX parsing requires optional dependency: `pip install python-docx`
        - If nothing is indexed (e.g., only unsupported files), the API returns `422`:
          ```json
          {
            "detail": {
              "message": "No documents were indexed",
              "errors": ["..."]
            }
          }
          ```

*   `POST /api/v1/rag/qa`
    *   Simple QA over uploaded knowledge with citations.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "question": "What is Krakow known for?",
          "top_k": 5,
          "provider": "openai",
          "model": "gpt-4o-mini"
        }
        ```
        - `provider` / `model` are optional. If omitted, the server uses model preferences (via `X-User-Email`) or defaults.
    *   **Returns**:
        ```json
        {
          "answer": "…",
          "citations": [{ "source": "guide.txt", "chunk_index": 0 }],
          "llm_used": true,
          "provider": "openai",
          "model": "gpt-4o-mini"
        }
        ```
    *   **Notes**: If LLM is unavailable, returns a context snippet as `answer`.

#### Chat

*   `POST /api/v1/chat`
    *   Process a natural language query using the hybrid agent (RAG + Tools).
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "message": "Find me a cheap apartment in Warsaw with a balcony",
          "session_id": "optional-session-id",
          "stream": false
        }
        ```
    *   **Returns**: `ChatResponse` object containing the agent's answer and sources.
    *   **Streaming**: Set `"stream": true` to receive Server-Sent Events (SSE).
        *   Content Type: `text/event-stream`
        *   Events: `data: <text-delta>`
        *   End of stream: `data: [DONE]`
        *   Headers: `X-Request-ID` present on the streaming response
        *   CORS (browser clients): `X-Request-ID` is exposed via `Access-Control-Expose-Headers`
        *   Example (Windows PowerShell, streaming):
            ```powershell
            curl.exe -N `
              -H "X-API-Key: your-api-key" `
              -H "Content-Type: application/json" `
              -d '{ "message": "Hello", "stream": true }' `
              http://localhost:8000/api/v1/chat
            ```
        *   Example (client):
            ```ts
            await streamChatMessage(
              { message: "Hello", session_id: "your-session-id" },
              (chunk) => { /* append chunk to UI */ },
              ({ requestId }) => { /* correlate logs with requestId */ }
            )
            ```

#### Tools

*   `POST /api/v1/tools/mortgage-calculator`
    *   Calculate mortgage payments.
    *   **Body**:
        ```json
        { "property_price": 300000, "down_payment_percent": 20, "interest_rate": 6.5, "loan_years": 30 }
        ```
    *   **Returns**:
        ```json
        { "monthly_payment": 1234.56, "total_interest": 0, "total_payment": 0 }
        ```
*   `POST /api/v1/tools/compare-properties`
    *   Compare properties by IDs.
    *   **Body**:
        ```json
        { "property_ids": ["id1", "id2"] }
        ```
    *   **Returns**:
        ```json
        {
          "properties": [{ "id": "id1", "price": 100000 }],
          "summary": { "count": 1, "min_price": 100000, "max_price": 100000, "price_difference": 0 }
        }
        ```
*   `POST /api/v1/tools/price-analysis`
    *   Analyze prices for a query.
    *   **Body**:
        ```json
        { "query": "Warsaw apartments" }
        ```
    *   **Returns**:
        ```json
        {
          "query": "Warsaw apartments",
          "count": 10,
          "average_price": 200000,
          "median_price": 195000,
          "distribution_by_type": { "Apartment": 8 }
        }
        ```
*   `POST /api/v1/tools/location-analysis`
    *   Location info for a property.
    *   **Body**:
        ```json
        { "property_id": "id1" }
        ```
    *   **Returns**:
        ```json
        { "property_id": "id1", "city": "Warsaw", "lat": 52.2297, "lon": 21.0122 }
        ```
*   `POST /api/v1/tools/valuation` (CE stub)
    *   Estimate value from area and price_per_sqm.
    *   **Body**:
        ```json
        { "property_id": "id1" }
        ```
    *   **Returns**:
        ```json
        { "property_id": "id1", "estimated_value": 250000 }
        ```
    *   **Errors**:
        *   `503` when disabled (`VALUATION_MODE!=simple`) or vector store is unavailable
*   `POST /api/v1/tools/legal-check` (CE stub)
    *   Basic legal risk analysis.
    *   **Body**:
        ```json
        { "text": "contract..." }
        ```
    *   **Returns**:
        ```json
        { "risks": [], "score": 0.0 }
        ```
    *   **Errors**:
        *   `503` when disabled (`LEGAL_CHECK_MODE!=basic`)
*   `POST /api/v1/tools/enrich-address` (CE stub)
    *   Address enrichment (enabled via flag).
    *   **Body**:
        ```json
        { "address": "Some St 1" }
        ```
    *   **Returns**:
        ```json
        { "address": "Some St 1", "data": {} }
        ```
    *   **Errors**:
        *   `503` when disabled (`DATA_ENRICHMENT_ENABLED=false`)
*   `POST /api/v1/tools/crm-sync-contact` (CE stub)
    *   Sync contact via webhook (if configured).
    *   **Body**:
        ```json
        { "name": "John", "phone": "123456", "email": "j@e.com" }
        ```
    *   **Returns**:
        ```json
        { "id": "contact-123" }
        ```
    *   **Errors**:
        *   `503` when not configured (`CRM_WEBHOOK_URL` unset)
        *   `502` when webhook call fails

*   `GET /api/v1/tools`
    *   List all available property analysis tools.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Returns**: List of tools with names and descriptions.

#### Prompt Templates

*   `GET /api/v1/prompt-templates`
    *   List available prompt templates and their variable schemas.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Returns**:
        ```json
        [
          {
            "id": "buyer_followup_email_v1",
            "title": "Buyer follow-up email",
            "category": "email",
            "description": "Follow-up email after an inquiry with next steps and a short question set.",
            "template_text": "Subject: Quick follow-up on {{property_address}} ...",
            "variables": [
              { "name": "property_address", "description": "Property address", "required": true, "example": "Main St 10" }
            ]
          }
        ]
        ```

*   `POST /api/v1/prompt-templates/apply`
    *   Apply a template by ID using provided variables and return rendered text.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "template_id": "buyer_followup_email_v1",
          "variables": {
            "property_address": "Main St 10, Warsaw",
            "buyer_name": "Alex",
            "agent_name": "Maria Nowak"
          }
        }
        ```
    *   **Returns**:
        ```json
        {
          "template_id": "buyer_followup_email_v1",
          "rendered_text": "Subject: Quick follow-up on Main St 10, Warsaw\n\nHi Alex,\n..."
        }
        ```
    *   **Errors**:
        *   `404` when `template_id` is unknown
        *   `400` when required variables are missing or unknown variables are provided

#### Export

*   `POST /api/v1/export/properties`
    *   Export properties to CSV, Excel, JSON, Markdown, or PDF.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body** (export by IDs):
        ```json
        {
          "format": "csv",
          "property_ids": ["prop1", "prop2"]
        }
        ```
    *   **Body** (export by search):
        ```json
        {
          "format": "pdf",
          "search": {
            "query": "2 bedroom apartment in Krakow",
            "limit": 25,
            "filters": { "city": "Krakow" },
            "alpha": 0.7,
            "sort_by": "price",
            "sort_order": "asc"
          }
        }
        ```
    *   **Search parameters**: Same as `POST /api/v1/search`, including:
        *   `filters` (object, optional)
        *   `alpha` (float, optional)
        *   `lat/lon/radius_km` or `min_lat/max_lat/min_lon/max_lon` (optional)
        *   `sort_by` (optional): `relevance`, `price`, `price_per_sqm`, `area_sqm`, `year_built`
        *   `sort_order` (optional): `asc` or `desc`
    *   **Returns**: File download with `Content-Disposition: attachment`.
    *   **Parameters**:
        *   `format` (string, required): One of `csv`, `xlsx`, `json`, `md`, `pdf`.
        *   `property_ids` (array, optional): Explicit property IDs to export.
        *   `search` (object, optional): Same as `SearchRequest` (supports filters, geo, `sort_by`, `sort_order`).
        *   `columns` (array, optional): Limit columns included in `csv`, `xlsx`, and `json`.
        *   `include_header` (bool, CSV): Include header row (default: `true`).
        *   `csv_delimiter` (string, CSV): Single-character delimiter (default: `,`).
        *   `csv_decimal` (string, CSV): Single-character decimal separator (default: `.`).
        *   `include_summary` (bool, Excel/Markdown): Include summary section/sheet (default: `true`).
        *   `include_statistics` (bool, Excel): Include statistics sheet (default: `true`).
        *   `include_metadata` (bool, JSON): Include metadata block (default: `true`).
        *   `pretty` (bool, JSON): Pretty-print JSON (default: `true`).
        *   `max_properties` (int, Markdown): Limit number of properties shown (default: all).

    *   **Body** (export with column selection + locale-friendly CSV):
        ```json
        {
          "format": "csv",
          "property_ids": ["prop1", "prop2"],
          "columns": ["id", "city", "price"],
          "include_header": true,
          "csv_delimiter": ";",
          "csv_decimal": ","
        }
        ```

#### Settings

*   `GET /api/v1/settings/notifications`
    *   Get user notification preferences.
    *   **Headers**: `X-API-Key: your-api-key
    *   **User selection**: Provide `X-User-Email: <user@example.com>` header or
        `?user_email=<user@example.com>` query param (query param overrides header).
    *   **Returns**: `NotificationSettings` object.

*   `PUT /api/v1/settings/notifications`
    *   Update user notification preferences.
    *   **Headers**: `X-API-Key: your-api-key
    *   **User selection**: Provide `X-User-Email: <user@example.com>` header or
        `?user_email=<user@example.com>` query param (query param overrides header).
    *   **Body**:
        ```json
        {
          "email_digest": true,
          "frequency": "weekly",
          "expert_mode": false,
          "marketing_emails": false
        }
        ```
    *   **Returns**: Updated `NotificationSettings` object.

*   `GET /api/v1/settings/models`
    *   List available model providers and their models (pricing/capabilities/metadata).
    *   **Headers**: `X-API-Key: your-api-key
    *   **Notes**:
        *   For local providers (e.g., Ollama), `runtime_available` indicates whether the local
            runtime is reachable from the API.
        *   `available_models` lists models that are already downloaded in the local runtime.
    *   **Returns**: Array of providers:
        ```json
        [
          {
            "name": "openai",
            "display_name": "OpenAI",
            "is_local": false,
            "requires_api_key": true,
            "models": [
              {
                "id": "gpt-4o",
                "display_name": "GPT-4o (Latest)",
                "provider_name": "OpenAI",
                "context_window": 128000,
                "pricing": { "input_price_per_1m": 2.5, "output_price_per_1m": 10.0, "currency": "USD" },
                "capabilities": ["streaming", "function_calling", "json_mode", "system_messages"],
                "description": "Latest flagship model",
                "recommended_for": ["general purpose"]
              }
            ]
          },
          {
            "name": "ollama",
            "display_name": "Ollama (Local)",
            "is_local": true,
            "requires_api_key": false,
            "runtime_available": false,
            "available_models": [],
            "models": [
              {
                "id": "llama3.3:8b",
                "display_name": "Llama 3.3 8B (Recommended)",
                "provider_name": "Ollama (Local)",
                "context_window": 128000,
                "pricing": null,
                "capabilities": ["streaming", "function_calling", "system_messages"],
                "description": "Latest balanced Llama model (8B parameters) - requires 8GB RAM",
                "recommended_for": ["best balance", "general purpose", "local inference"]
              }
            ]
          }
        ]
        ```

*   `GET /api/v1/settings/model-preferences`
    *   Get the default model preferences for the current user.
    *   **Headers**: `X-API-Key: your-api-key
    *   **User selection**: Provide `X-User-Email: <user@example.com>` header or
        `?user_email=<user@example.com>` query param (query param overrides header).
    *   **Returns**:
        ```json
        {
          "preferred_provider": "openai",
          "preferred_model": "gpt-4o"
        }
        ```

*   `PUT /api/v1/settings/model-preferences`
    *   Update the default model preferences for the current user (used by `/api/v1/chat` and `/api/v1/rag/qa`).
    *   **Headers**: `X-API-Key: your-api-key
    *   **User selection**: Provide `X-User-Email: <user@example.com>` header or
        `?user_email=<user@example.com>` query param (query param overrides header).
    *   **Body**:
        ```json
        {
          "preferred_provider": "openai",
          "preferred_model": "gpt-4o"
        }
        ```
    *   **Returns**: Updated model preferences.

#### Admin

*   `GET /api/v1/admin/health`
    *   Detailed health check for admin.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Returns**: `{"status": "healthy|degraded (...)", "version": "..."}`

*   `GET /api/v1/admin/metrics`
    *   Return simple API metrics counters.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Returns**:
        ```json
        {
          "GET /api/v1/verify-auth": 42,
          "POST /api/v1/search": 10
        }
        ```

## Analytics

### HedonicValuationModel

**Module**: `analytics.valuation_model`

Estimates the fair market value of a property using a component-based hedonic pricing model.

#### `HedonicValuationModel(market_insights)`

*   **Args**:
    *   `market_insights` (MarketInsights): Instance of market insights engine to retrieve local price data.

#### Methods

*   `predict_fair_price(property: Property) -> ValuationResult`
    *   Calculates estimated price, price delta, and valuation status.
    *   **Returns**: `ValuationResult` object containing:
        *   `estimated_price`: Predicted fair price.
        *   `price_delta`: Difference between listing price and estimated price.
        *   `delta_percent`: Percentage difference.
        *   `valuation_status`: "undervalued", "fair", "overvalued", etc.
        *   `confidence`: Confidence score (0.0 - 1.0).

---


## PropertyExporter

Handles the export of property data to various formats (CSV, Excel, JSON, Markdown, PDF).

### Class: `PropertyExporter`

```python
class PropertyExporter:
    def __init__(self, properties: Union[List[Dict[str, Any]], PropertyCollection, pd.DataFrame]):
        """
        Initialize the exporter with property data.
        
        Args:
            properties: List of dictionaries, PropertyCollection, or DataFrame containing property data.
        """
```

### Methods

#### `export`

```python
def export(self, format: ExportFormat, **kwargs) -> Union[str, BytesIO]:
    """
    Export properties to the specified format.
    
    Args:
        format: ExportFormat enum value (CSV, EXCEL, JSON, MARKDOWN, PDF).
        **kwargs: Additional arguments passed to specific export methods.
        
    Returns:
        str or BytesIO: The exported data (string for text formats, BytesIO for binary).
    """
```

#### `export_to_pdf`

```python
def export_to_pdf(self) -> BytesIO:
    """
    Export properties to PDF format with a summary and listing table.
    
    Returns:
        BytesIO: Buffer containing the generated PDF file.
    """
```

#### `get_filename`

```python
def get_filename(self, format: ExportFormat, prefix: str = "properties") -> str:
    """
    Generate a timestamped filename for the export.
    
    Args:
        format: The export format.
        prefix: Prefix for the filename.
        
    Returns:
        str: The generated filename (e.g., "properties_20231027_123456.pdf").
    """
```

### Enums

#### `ExportFormat`

Supported export formats:
- `CSV` ("csv")
- `EXCEL` ("xlsx")
- `JSON` ("json")
- `MARKDOWN` ("md")
- `PDF` ("pdf")

---

## Data

### Property

**Module**: `data.schemas`

Pydantic model representing a real estate listing.

*   **Fields**:
    *   `id` (str): Unique ID.
    *   `title` (str): Title (min 5 chars).
    *   `price` (float): Listing price.
    *   `area_sqm` (float): Area in square meters.
    *   `city` (str): City name.
    *   `rooms` (float): Number of rooms.
    *   `year_built` (int): Year of construction.
    *   `points_of_interest` (List[PointOfInterest]): Nearby POIs.
    *   ... (see source for full list)

### PointOfInterest

**Module**: `data.schemas`

Represents a nearby location of interest.

*   **Fields**:
    *   `name` (str): Name of the place.
    *   `category` (str): Type (school, park, transport, etc.).
    *   `distance_meters` (float): Distance from property.
    *   `latitude` (float): Geo-coordinate.
    *   `longitude` (float): Geo-coordinate.
    *   `tags` (Dict[str, str]): Additional OSM tags.

---

## Python API: Data Providers

### `APIProvider` — External REST API ingestion

**Module**: `data.providers.api_provider`

Fetch property listings from external REST APIs and normalize into project schemas.

#### Usage

```python
from data.providers.api_provider import APIProvider

provider = APIProvider(api_url="https://api.example.com", api_key="secret")
properties = provider.get_properties()
```

#### Notes

- Authentication via Bearer token when `api_key` is provided.
- Validates API reachability, loads JSON payload, and returns `Property` objects.
- See integration tests for end-to-end flow: `tests/integration/data/test_api_provider_integration.py`.
