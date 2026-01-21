# User Guide - AI Real Estate Assistant

## Appearance

Use the theme button (moon/sun) in the top navigation to switch between Light and Dark mode. Your
selection is saved in your browser.

## Settings

Open **Settings** from the top navigation to manage:
- **Identity**: Set the email address used to scope settings (saved locally in your browser).
- **Default Model**: Choose the provider/model used by the Assistant for responses.
- **Notifications**: Configure digest frequency and optional Expert Mode / product updates.

## Notifications & Digests

The AI Real Estate Assistant helps you stay on top of the market with personalized email digests.
Whether you're a homebuyer looking for your dream house or an investor monitoring market trends,
our digests provide the insights you need.

All notification settings and labels follow your selected app language.
Email delivery requires SMTP configuration on the backend. If SMTP is not configured, preferences
are still saved but no emails will be sent.

### Consumer Digest
Designed for homebuyers and renters, the Consumer Digest highlights:
- **New Matches**: Properties matching your saved searches that were added since your last update.
- **Top Picks**: A curated selection of high-quality listings relevant to your preferences.
- **Price Drops**: Significant price reductions on properties you might be interested in.
- **Saved Search Status**: A quick summary of how many new matches each of your saved searches has found.

**Frequency**: Daily or Weekly (customizable in Settings).

### Expert Digest
Designed for investors and real estate professionals, the Expert Digest includes everything in the Consumer Digest plus:
- **Market Trends**: Directional price trends (up/down) and percentage changes for your key cities.
- **City Indices**: Average price data and inventory status for top markets.
- **YoY Analysis**: Top gaining and declining areas year-over-year.

**How to Enable**: 
1. Go to **Settings > Notifications**.
2. Select your preferred **Digest Frequency** (Daily/Weekly).
3. Toggle **Expert Mode** to receive advanced market analytics.

### Managing Saved Searches
To ensure your digest contains relevant properties:
1. Use the **Search** tab to define your criteria (Location, Price, Rooms, etc.).
2. Click **Save Search** and give it a memorable name (e.g., "2-bed in Downtown").
3. These searches will automatically feed into your digest.
4. For map-based searches, you can narrow results by geo radius or a bounding box area.

## Data Sources

The Community Edition focuses on local-first workflows:
- **Local datasets**: Properties indexed in the local vector store (ChromaDB) for search and tools.
- **Optional connectors**: Some integrations are available as CE-safe webhooks/stubs and can be enabled via environment flags.

## Market Analytics

Market analytics are exposed in two places:
- **Tools**: Price analysis and comparisons are available under **Analytics & Tools**.
- **Email digests** (optional): If SMTP is configured, weekly/daily digests can include an Expert section with trends.

## Exporting Data

You can export property listings and search results for offline analysis or sharing.

### Supported Formats
- **PDF**: Best for sharing and printing. Includes summary statistics and a clean table of properties.
- **Excel/CSV**: Best for further analysis in spreadsheet software.
- **JSON**: Best for developers and data integration.
- **Markdown**: Best for text-based notes and documentation.

### How to Export
1. Perform a search or view your saved properties.
2. Click the **Export** button in the sidebar or results view.
3. Select your desired format (e.g., "PDF Report").
4. The file will be generated and downloaded automatically.

## Chat Interface

The AI-powered chat interface allows you to search for properties using natural language.

### Local Run (Docker)
- Ensure Docker Desktop is installed
- Copy environment: `Copy-Item .env.example .env`
- Start: `docker compose up -d --build`
- Optional smoke (build + health checks): `python scripts\compose_smoke.py --ci`
- Open UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json` (repo snapshot: `docs/openapi.json`)
- Generated endpoint index (repo): `docs/API_REFERENCE.generated.md`

### How to Use
1. Navigate to the **Chat** tab.
2. Type your request (e.g., "Find me a 2-bedroom apartment in Warsaw under 3000 PLN").
3. The AI will analyze your request, search the database, and present the best matches.
4. You can ask follow-up questions or refine your criteria conversationally.
 
### Streaming Responses (SSE)
For real-time streaming from the assistant:
- In API mode, set `"stream": true` in `POST /api/v1/chat`
- The response uses `text/event-stream` with lines like `data: <text-delta>` and finishes with `data: [DONE]`
- Ensure you include the `X-API-Key` header; see API Reference for an example
- The UI progressively renders assistant messages and shows a Retry button on errors
- The UI displays `request_id` on both success and error paths (when available) to help correlate with server logs

## Search Filters

Use the filters sidebar on the Search page to narrow results:
- Min/Max Price: Enter numbers to constrain price range
- Minimum Rooms: Specify the minimum number of rooms
- Property Type: Choose from Apartment, House, Studio, Loft, Townhouse, Other

Tips:
- Enter a query first (the Search button is disabled until you do).
- Filters combine with your text query for hybrid ranking
- Min Price must be less than or equal to Max Price
- Click “Clear Filters” to reset and broaden results
 
Neutral/empty states:
- Before the first search, the page shows a neutral prompt to enter a query
- After a search with zero matches, the page shows “No results found”

## Geo Search

Use geo filters to target a specific area:
- Radius: provide latitude, longitude, and radius (km)
- Bounding Box: provide min/max lat and min/max lon

Example (client payload):
```json
{
  "query": "apartments with balcony",
  "lat": 50.0647,
  "lon": 19.9450,
  "radius_km": 3.0,
  "sort_by": "price",
  "sort_order": "asc"
}
```

## Sorting

Use Sorting to order results:
- Sort By: Relevance, Price, Price per m², Area (m²), Year Built
- Order: Ascending or Descending

Sorting works together with filters and semantic relevance.

## Login (Email Code)

For accounts-enabled deployments, you can log in using a one-time email code:
- Request a code: `POST /api/v1/auth/request-code` with your email
- Enter the 6-digit code to verify: `POST /api/v1/auth/verify-code`
- The server returns a `session_token`; include it in subsequent requests with `X-Session-Token`
- In development, the API returns the code inline for testing

## CORS

For local development, all origins are allowed.
For production, set:
```
ENVIRONMENT=production
CORS_ALLOW_ORIGINS=https://yourapp.com,https://studio.vercel.app
```
The backend will only allow these origins.

## Quality & Stability
- The app enforces backend quality gates (lint, types, custom rules) to improve reliability.
- If requests fail due to rate limits or validation, try again after the suggested reset time.
- For contributors, run backend checks locally:
  - `python -m pytest`
  - `python -m pytest -q tests\integration\test_rule_engine_clean.py`
  - `python -m ruff check .`
  - `python -m mypy`

## Financial Tools

### Mortgage Calculator
Plan your budget effectively with our integrated Mortgage Calculator.

**Features**:
- **Monthly Payment**: Calculate your estimated monthly mortgage payment.
- **Total Interest**: See how much interest you'll pay over the life of the loan.
- **Cost Breakdown**: Visualize the split between principal and interest.

**How to Use**:
1. Navigate to the **Analytics & Tools** tab.
2. Scroll to the **Mortgage Calculator** section.
3. Enter the **Property Price**, **Down Payment**, **Interest Rate**, and **Loan Term**.
4. Click **Calculate** to view detailed results.

### Prompt Templates
Generate ready-to-use text for common real estate workflows (listing descriptions, buyer emails).

**How to Use**:
1. Navigate to the **Analytics & Tools** tab.
2. Scroll to **Prompt Templates**.
3. Pick a template (e.g., “Buyer follow-up email”).
4. Fill in the required fields (marked with `*`) and click **Generate**.
5. Copy the output and paste it into your email/client workflow.

### API Tools (V4)
If you are using the V4 API (FastAPI), the same tool capabilities are available over HTTP:
- Compare properties by IDs
- Basic price analysis for a query
- Basic location lookup for a property ID
Additional CE stub endpoints (may be disabled depending on server configuration):
- Valuation estimate: `POST /api/v1/tools/valuation` (requires `VALUATION_MODE=simple` and vector
  store available)
- Legal check: `POST /api/v1/tools/legal-check` (requires `LEGAL_CHECK_MODE=basic`)
- Data enrichment: `POST /api/v1/tools/enrich-address` (requires `DATA_ENRICHMENT_ENABLED=true`)
- CRM contact sync: `POST /api/v1/tools/crm-sync-contact` (requires `CRM_WEBHOOK_URL` to be set)

### Models & Costs (V4 API)
If you are building a client that needs to display available models/providers (and token pricing where applicable):
- `GET /api/v1/settings/models` returns provider + model metadata, including context windows,
  capabilities, and pricing (when available).
In the web app, you can view this under **Settings > Models & Costs**.
For local providers (e.g., Ollama), the response includes `runtime_available` and
`available_models`, and the UI shows setup steps when the local runtime is not detected.

### API Export (V4)
To export search results or specific property IDs via the V4 API (and from the web app UI):
- `POST /api/v1/export/properties` supports `format`: `csv`, `xlsx`, `json`, `md`, `pdf`
- Web app:
  - **Search**: pick export format, optionally provide a comma-separated column list, then click **Export**
  - **Tools > Compare**: enter IDs, then click **Export** (uses the same endpoint)
- Example (export by search with sorting):
  ```json
  {
    "format": "xlsx",
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
 - Example (export by IDs with column selection + locale-friendly CSV):
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

## Local RAG (Community Edition)

You can upload your own notes to enable question answering over your content.

- Supported file types in CE: `.txt`, `.md`
- Supported with optional install: `.pdf` (`pip install pypdf`), `.docx` (`pip install python-docx`)
- If nothing is indexed (e.g., only PDFs without optional deps), the API returns `422` with details.
- Upload limits (max files / max bytes) are enforced by the backend; oversized files are reported in `errors`.
- If total payload exceeds the configured limit, the API returns `413` and indexes nothing.

### Upload Flow
1. Use a client or cURL to call `POST /api/v1/rag/upload` with form-data `files`.
2. The server chunks your documents and indexes them locally.
3. Response includes how many chunks were indexed.

Example (PowerShell):
```powershell
$form = @{
  files = Get-Item .\notes.md
}

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/rag/upload" `
  -Method Post `
  -Headers @{ "X-API-Key" = "dev-secret-key" } `
  -Form $form
```

### Ask Questions
- Call `POST /api/v1/rag/qa` with a JSON body:
  ```json
  { "question": "What is Krakow known for?", "top_k": 5 }
  ```
- Optional: include `provider` / `model` to override the selection for this request.
- Response includes `answer`, `citations`, and `llm_used` (plus the effective `provider` / `model`).

Tip: If no model is configured, the API returns a snippet from the most relevant chunks.
