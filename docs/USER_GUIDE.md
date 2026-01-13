# User Guide - AI Real Estate Assistant

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

### API Export (V4)
To export search results or specific property IDs via the V4 API:
103| - `POST /api/v1/export/properties` supports `format`: `csv`, `xlsx`, `json`, `md`, `pdf`
