# User Guide - AI Real Estate Assistant

## Appearance

Use the theme button (moon/sun) in the top navigation to switch between Light and Dark mode. Your selection is saved in your browser.

## Notifications & Digests

The AI Real Estate Assistant helps you stay on top of the market with personalized email digests. Whether you're a homebuyer looking for your dream house or an investor monitoring market trends, our digests provide the insights you need.

All notification settings and labels follow your selected app language.

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

The platform aggregates data from multiple sources:
- **Direct Listings**: Properties uploaded directly to the platform.
- **External APIs**: Real-time integrations with major real estate data providers (new in v1.1).
- **Market Indices**: Aggregated regional data for market analysis.

## Market Analytics

The platform now supports comprehensive market analysis across multiple regions, including indices and comparables for CIS, Russia, Turkey, USA, and Africa.

### Regional Insights
You can access detailed statistics for specific countries and regions:
- **Market Overview**: Total listings, average/median prices, and price per square meter.
- **Price Trends**: Analyze historical price movements to identify growing or cooling markets.
- **Comparables**: Compare property metrics across different cities and countries.

### How to Use
1. **Expert Mode**: Ensure you are in Expert Mode to view detailed indices.
2. **Filtering**: Use the location filters to select a specific country (e.g., "Turkey") or region (e.g., "Marmara").
3. **Indices Panel**: View the generated price indices and year-over-year (YoY) growth rates.

These insights are automatically included in the **Expert Digest** for your subscribed regions.

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

### How to Use
1. Navigate to the **Chat** tab.
2. Type your request (e.g., "Find me a 2-bedroom apartment in Warsaw under 3000 PLN").
3. The AI will analyze your request, search the database, and present the best matches.
4. You can ask follow-up questions or refine your criteria conversationally.
 
### Streaming Responses (SSE)
For real-time streaming from the assistant:
- In API mode, set `"stream": true` in `POST /api/v1/chat`
- The response uses `text/event-stream` with lines like `data: {"content":"..."}` and finishes with `data: [DONE]`
- Ensure you include the `X-API-Key` header; see API Reference for an example

## Search Filters

Use the filters sidebar on the Search page to narrow results:
- Min/Max Price: Enter numbers to constrain price range
- Minimum Rooms: Specify the minimum number of rooms
- Property Type: Choose from Apartment, House, Studio, Loft, Townhouse, Other

Tips:
- Filters combine with your text query for hybrid ranking
- Click “Clear Filters” to reset and broaden results

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

### API Tools (V4)
If you are using the V4 API (FastAPI), the same tool capabilities are available over HTTP:
- Compare properties by IDs
- Basic price analysis for a query
- Basic location lookup for a property ID

### Models & Costs (V4 API)
If you are building a client that needs to display available models/providers (and token pricing where applicable):
- `GET /api/v1/settings/models` returns provider + model metadata, including context windows, capabilities, and pricing (when available).
In the web app, you can view this under **Settings > Models & Costs**.
For local providers (e.g., Ollama), the response includes `runtime_available` and `available_models`, and the UI shows setup steps when the local runtime is not detected.

### API Export (V4)
To export search results or specific property IDs via the V4 API:
103| - `POST /api/v1/export/properties` supports `format`: `csv`, `xlsx`, `json`, `md`, `pdf`
