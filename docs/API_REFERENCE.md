# API Reference

This document provides a reference for the core Python APIs of the AI Real Estate Assistant.

## V4 API

The V4 API is built with FastAPI and provides a RESTful interface for the AI Real Estate Assistant.

### Authentication

The API uses API Key authentication via the `X-API-Key` header.
To configure the key, set the `API_ACCESS_KEY` environment variable (defaults to `dev-secret-key` for development).

### Request IDs

All API responses include an `X-Request-ID` header.
You can optionally provide your own `X-Request-ID` (letters/numbers plus `._-`, up to 128 chars) to correlate client logs with server logs.

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
            "min_price": 2000
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
        *   `alpha` (float, optional): Weight for vector similarity (0.0 to 1.0). 1.0 = Pure Vector, 0.0 = Pure Keyword. Default: 0.7.
        *   `lat/lon/radius_km` (optional): Geo radius filter (in kilometers).
        *   `min_lat/max_lat/min_lon/max_lon` (optional): Geo bounding box filter.
        *   `sort_by` (optional): `relevance`, `price`, `price_per_sqm`, `area_sqm`, `year_built`.
        *   `sort_order` (optional): `asc` or `desc`.
    *   **Returns**: `SearchResponse` object containing list of properties with hybrid scores.

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
        *   Events: `data: {"content": "..."}` or `data: {"error": "..."}`
        *   End of stream: `data: [DONE]`
        *   Example (curl):
            ```bash
            curl -N -H "X-API-Key: your-api-key" -H "Content-Type: application/json" \
              -d "{\"message\": \"Hello\", \"stream\": true}" \
              http://localhost:8000/api/v1/chat
            ```

#### Tools

*   `GET /api/v1/tools`
    *   List all available property analysis tools.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Returns**: List of tools with names and descriptions.

*   `POST /api/v1/tools/mortgage-calculator`
    *   Calculate mortgage payments and breakdown.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "property_price": 500000,
          "down_payment_percent": 20.0,
          "interest_rate": 4.5,
          "loan_years": 30
        }
        ```
    *   **Returns**: `MortgageResult` with monthly payment, total interest, and cost breakdown.

*   `POST /api/v1/tools/compare-properties`
    *   Compare multiple properties by ID (basic fields + summary).
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "property_ids": ["prop1", "prop2", "prop3"]
        }
        ```
    *   **Returns**: `ComparePropertiesResponse` with `properties[]` and `summary` (min/max/difference).

*   `POST /api/v1/tools/price-analysis`
    *   Compute basic price statistics from retrieved listings.
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "query": "apartments in Madrid"
        }
        ```
    *   **Returns**: `PriceAnalysisResponse` (count, avg/median/min/max, price/m² stats, distribution by type).

*   `POST /api/v1/tools/location-analysis`
    *   Fetch basic location information for a property by ID (city/neighborhood/coords).
    *   **Headers**: `X-API-Key: your-api-key
    *   **Body**:
        ```json
        {
          "property_id": "prop1"
        }
        ```
    *   **Returns**: `LocationAnalysisResponse`.

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
            "alpha": 0.7
          }
        }
        ```
    *   **Returns**: File download with `Content-Disposition: attachment`.

#### Settings

*   `GET /api/v1/settings/notifications`
    *   Get user notification preferences.
    *   **Headers**: `X-API-Key: your-api-key
    *   **User selection**: Provide `X-User-Email: <user@example.com>` header or `?user_email=<user@example.com>` query param (query param overrides header).
    *   **Returns**: `NotificationSettings` object.

*   `PUT /api/v1/settings/notifications`
    *   Update user notification preferences.
    *   **Headers**: `X-API-Key: your-api-key
    *   **User selection**: Provide `X-User-Email: <user@example.com>` header or `?user_email=<user@example.com>` query param (query param overrides header).
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
        *   For local providers (e.g., Ollama), `runtime_available` indicates whether the local runtime is reachable from the API.
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
- `EXCEL` ("excel")
- `JSON` ("json")
- `MARKDOWN` ("markdown")
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
