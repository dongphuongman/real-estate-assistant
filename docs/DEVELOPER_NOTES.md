# Developer Notes

## Frontend Development (Next.js)

### Architecture
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS + Shadcn UI
- **State Management**: React Hooks
- **Testing**: Jest + React Testing Library

### Theming
- Dark/light mode is controlled by a `dark` class on the root `html` element (`frontend/src/app/globals.css`).
- The initial theme is applied via an inline script in `frontend/src/app/layout.tsx` (reads `localStorage.theme` or system preference).
- The theme toggle lives in `frontend/src/components/layout/main-nav.tsx` and persists selection to `localStorage.theme`.

### Directory Structure
- `src/app`: Pages and layouts (App Router).
- `src/components/ui`: Atomic UI components (Button, Input, Card, etc.).
- `src/components/layout`: Global layout components (MainNav).
- `src/lib`: Utility functions, API clients, and types.
    - `api.ts`: API client functions wrapping `fetch`.
    - `types.ts`: Shared TypeScript interfaces (mirrors Pydantic models).
    - `utils.ts`: Helper functions (cn, etc.).
    - `api.ts` automatically adds `X-API-Key` from `NEXT_PUBLIC_API_KEY` when set.
    - `api.ts` automatically adds `X-User-Email` from `localStorage.userEmail` when available.

### Testing Guidelines
- **Unit Tests**: Located in `__tests__` directories next to the components/pages.
- **Mocking**:
    - Use `jest.mock` for `next/navigation`.
    - Mock `src/lib/api.ts` for integration tests to avoid real network calls.
    - Mock `ResizeObserver` or other browser APIs if needed (setup in `jest.setup.ts`).
- **Coverage**: Ensure ≥90% coverage. Check with `npm run test:coverage`.

### Backend SSE Testing
- Use FastAPI `TestClient.stream` to validate `text/event-stream` responses
- Patch `create_hybrid_agent` with an object exposing `astream_query` that yields event lines
- Assert chunks contain `data: ...` and end with `data: [DONE]`

---

## Notifications System - Digest Generator

### Overview
The digest system is built around `DigestGenerator`, which bridges the gap between raw property data (`VectorStore`) and user-facing notifications (`AlertManager`, `EmailService`).

The Streamlit Notifications tab uses `i18n.get_text(...)` for all user-facing labels.

### Key Components

1.  **DigestGenerator (`notifications/digest_generator.py`)**
    *   **Purpose**: Gathers and structures data for email digests.
    *   **Inputs**: `UserPreferences`, `SavedSearch` list, `MarketInsights` engine.
    *   **Outputs**: Dictionary payload compatible with `DigestTemplate`.
    *   **Logic**:
        *   Iterates through `SavedSearch` objects.
        *   Queries `ChromaPropertyStore` for new matches.
        *   Deduplicates properties across searches.
        *   Fetches market trends from `MarketInsights` (Expert mode).
        *   Aggregates data into `top_picks`, `saved_searches`, and `expert` sections.

2.  **AlertManager (`notifications/alert_manager.py`)**
    *   **Role**: Orchestrator.
    *   **Method**: `process_digest(...)`
    *   **Responsibility**:
        *   Instantiates `DigestGenerator`.
        *   Calls `generate_digest()`.
        *   Passes result to `send_digest()`.
        *   Handles errors and logging.

3.  **Email Templates (`notifications/email_templates.py`)**
    *   **Class**: `DigestTemplate`
    *   **Role**: Rendering.
    *   **Features**:
        *   Responsive HTML layout.
        *   Conditional rendering for "Expert" sections (tables, indices).
        *   Property card components.

### Extension Points

*   **New Data Sources**: To add more data (e.g., mortgage rates), inject a new service into `DigestGenerator.__init__` and update `generate_digest` to populate the payload.
*   **Custom Filtering**: Modify `DigestGenerator._build_filters` to support more complex `SavedSearch` criteria (e.g., polygon search).
*   **Performance**: Currently, `generate_digest` runs sequentially. for large user bases, consider parallelizing search execution or pre-computing matches.

### Testing
*   **Unit Tests**: `tests/unit/test_digest_generator.py` covers basic data gathering and logic.
*   **Integration Tests**: `tests/integration/test_digest_generator_integration.py` verifies the flow from `AlertManager` to `DigestGenerator`.

---

## Data Providers

### Overview
The system uses a provider pattern to fetch property data from various sources. The base class `BaseDataProvider` defines the interface.

### API Provider (`data/providers/api_provider.py`)
*   **Purpose**: Fetch property data from external REST APIs.
*   **Configuration**:
    *   `api_url`: Base URL of the provider.
    *   `api_key`: Authentication key (Bearer token).
*   **Usage**:
    ```python
    from data.providers.api_provider import APIProvider
    
    provider = APIProvider(api_url="https://api.example.com", api_key="secret")
    properties = provider.get_properties()
    ```
*   **Testing**:
    *   Use `MockRealEstateAPIProvider` for testing without keys.
    *   For integration tests, mock `requests.get` to return expected JSON structures.

---

## Analytics - Financial Metrics

### Overview
The `FinancialCalculator` module (`analytics/financial_metrics.py`) provides standardized investment analysis logic used by the Expert Dashboard and potentially by Agents/Tools.

### Key Capabilities
*   **Mortgage Calculation**: Standard amortization formula.
*   **Investment Analysis**:
    *   **Inputs**: Price, Rent, Mortgage Params, Expense Params.
    *   **Outputs**: `InvestmentMetrics` (Gross/Net Yield, Cap Rate, Cash-on-Cash, Cash Flow).
    *   **Expenses**: Detailed breakdown handling vacancy, management, tax, insurance, etc.

### Usage Example
```python
from analytics.financial_metrics import FinancialCalculator, MortgageParams

metrics = FinancialCalculator.analyze_investment(

## V4 API Notes

### General
- All API responses include an `X-Request-ID` header for log correlation.
- Rate limiting is enforced per client (API key) with defaults: 100 requests per 60 seconds.
- Rate limit headers returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

### Search

`POST /api/v1/search` supports:
- Hybrid retrieval weight: `alpha`
- Geo radius filter: `lat`, `lon`, `radius_km`
- Geo bounding box filter: `min_lat`, `max_lat`, `min_lon`, `max_lon`
- Sorting: `sort_by`, `sort_order`
    property_price=250000,
    monthly_rent=2000,
    mortgage=MortgageParams(interest_rate=5.5, down_payment_percent=20)
)
print(f"CoC Return: {metrics.cash_on_cash_return}%")
```

### Tools

The V4 API exposes tool endpoints under `/api/v1/tools/*`:
- `GET /api/v1/tools` lists available tools (name + description)
- `POST /api/v1/tools/mortgage-calculator` returns structured `MortgageResult`
- `POST /api/v1/tools/compare-properties` returns a minimal comparison + summary
- `POST /api/v1/tools/price-analysis` returns price stats and distribution by type
- `POST /api/v1/tools/location-analysis` returns basic location fields (city/coords)

### Settings

- `GET /api/v1/settings/notifications` reads user digest preferences (scoped by `X-User-Email` or `?user_email=...`).
- `PUT /api/v1/settings/notifications` updates user digest preferences (scoped by `X-User-Email` or `?user_email=...`).
- `GET /api/v1/settings/models` lists providers/models (pricing/capabilities/metadata) for model comparison and cost UX.
    - The Next.js UI renders this under `Settings > Models & Costs`.
    - For local providers (e.g., Ollama), the API also returns `runtime_available` and `available_models` for offline/local UX.

### Export

The V4 API exposes export endpoints under `/api/v1/export/*`:
- `POST /api/v1/export/properties` exports property IDs or search results to `csv`, `xlsx`, `json`, `md`, `pdf`

---

## Analytics - Regional Market Insights

### Overview
The `MarketInsights` engine has been extended to support multi-region analysis, enabling comparisons across countries and specific regions (e.g., CIS, Russia, Turkey, USA).

### Key Features
*   **Country/Region Statistics**: Get aggregate market stats filtered by country or region.
*   **Price Trends**: Analyze price direction and changes for specific geographic scopes.
*   **Regional Indices**: Generate time-series price indices for multiple countries to track YoY performance.

### Export Functionality
*   **Property Exports**: `PropertyExporter` in `utils/exporters.py` supports CSV, Excel, JSON, Markdown, and PDF formats.
*   **Points of Interest**: Exports now include POI summary statistics (count, closest distance, categories) and detailed lists in Markdown/JSON.
*   **Usage**:
    ```python
    exporter = PropertyExporter(properties)
    # Export to Markdown
    md_report = exporter.export_to_markdown()
    # Export to PDF
    pdf_report = exporter.export_to_pdf()
    ```

### Usage Example
```python
from analytics import MarketInsights

# Get stats for a specific country
stats = insights.get_country_statistics("Turkey")

# Get price trend for a region
trend = insights.get_price_trend(region="Marmara")

# Get comparative indices for multiple countries
df_indices = insights.get_country_indices(countries=["Turkey", "Russia", "USA"])
```

---

## Search & Retrieval - Strategic Reranking & Valuation

### Overview
The search system now includes a `StrategicReranker` that re-orders search results based on high-level user strategies (Investor, Family, Bargain) and a `HedonicValuationModel` that estimates fair market value to identify undervalued properties.

### Components

1.  **HedonicValuationModel (`analytics/valuation_model.py`)**
    *   **Purpose**: Estimates the fair price of a property based on its characteristics and local market data.
    *   **Logic**: Uses component-based valuation:
        *   Base value: Area * Average Price/sqm (from `MarketInsights`).
        *   Adjustments: Year built, energy rating, floor, amenities (parking, garden, etc.).
    *   **Output**: `ValuationResult` (Estimated Price, Delta, Status: Undervalued/Fair/Overvalued).

2.  **StrategicReranker (`vector_store/reranker.py`)**
    *   **Purpose**: Re-ranks vector search results to align with user persona.
    *   **Strategies**:
        *   `investor`: Boosts properties with high yield, low price/sqm, or "undervalued" status (via Valuation Model).
        *   `family`: Boosts properties with 3+ rooms, garden, parking, good energy rating.
        *   `bargain`: Boosts properties with lowest absolute price.
        *   `balanced`: Default mix of relevance and quality.

### Usage Example
```python
from vector_store.reranker import StrategicReranker
from analytics.valuation_model import HedonicValuationModel

# Initialize
valuation_model = HedonicValuationModel(market_insights=insights)
reranker = StrategicReranker(valuation_model=valuation_model)

# Rerank results
results = reranker.rerank_with_strategy(
    query="apartment in Warsaw",
    documents=docs,
    strategy="investor"
)
```

---

## Data Loading & Performance

### Parallel Data Loading
*   **Module**: `utils/data_loader.py`
*   **Purpose**: Loads multiple CSV/Excel files in parallel to reduce blocking time in Streamlit.
*   **Mechanism**: Uses `ThreadPoolExecutor` to process files concurrently.
*   **Vectorization**: `DataLoaderCsv` now uses vectorized pandas operations (e.g., `.map()`, `.fillna()`) instead of `.apply()` for 10x-100x speedup on large datasets.

### Vector Store Ingestion
*   **ChromaDB**: Ingestion is asynchronous and thread-safe.
*   **Concurrency**: You can control the number of indexing threads by setting `CHROMA_INDEXING_WORKERS` in `.env`. Default is usually 4.
*   **Optimization**: Embeddings are only generated for new documents (deduplication based on ID).
