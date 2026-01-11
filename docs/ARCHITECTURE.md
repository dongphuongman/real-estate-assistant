# Architecture (V3)

## System Overview
- Streamlit UI (model selection, settings, chat, Expert Panel, Comparison Dashboard)
- Query Analyzer (intent, filters)
- Hybrid processing: simple → RAG, complex → Agent + Tools
- Tools: mortgage, comparison, analysis
- **Financial Analytics**: Standardized ROI/Yield/Mortgage calculator via `FinancialCalculator`.
- **Market Analytics**: Multi-region indices and comparables (CIS, Russia, Turkey, USA, Africa) via `MarketInsights`.
- Comparison Dashboard: Interactive side-by-side analysis, radar charts, price trends, amenity matrix
- Retriever: ChromaDB (semantic + keyword, MMR), AdvancedPropertyRetriever (geo radius, price filters, sorting)
- Strategic Reranker (investor/family/bargain strategies, valuation boost)
- Hedonic Valuation Model (fair price estimation, undervaluation detection)
- Response formatter

## Technology Stack
- UI: Streamlit 1.37+
- AI Orchestration: LangChain 0.2+
- Providers: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama
- Vector store: ChromaDB 0.5+
- Embeddings: FastEmbed (BGE)
- Data: Pandas 2.2+, Pydantic 2.5+
- Python 3.11+

## Data Layer (New in V3.1)
- **BaseDataProvider**: Abstract base class for all data providers.
- **CSVDataProvider**: Wrapper around legacy CSV loader, implementing the standard interface.
- **JSONDataProvider**: Support for local JSON files and external APIs (URL-based), including data normalization and validation.
- **Data Validation**: Pydantic models (Property, PointOfInterest, etc.) ensure data consistency.
- **Export System**: Multi-format export (CSV/Excel/JSON/MD) with POI integration via `PropertyExporter`.
- **Vector Store Optimization (PE006)**:
    - **Non-blocking Initialization**: Lazy loading of IDs to prevent startup freeze.
    - **Async Indexing**: Background thread processing with separated embedding generation (unlocked) and database writing (locked).
    - **Concurrent Search**: Search operations remain responsive during heavy indexing jobs.

## Key Data Flows
- Data load → embeddings → ChromaDB persist → hybrid retrieval → rerank → response
- Expert Panel → map filters (geo radius, geo bounding box, price/rooms/amenities, neutral states) + retrieval filters (listing type, price, sort) + indices/time‑series → export digest
- **Digest Generation**:
  - **DigestGenerator**: Orchestrates data gathering from `VectorStore` (new matches for saved searches) and `MarketInsights` (trends/expert data).
  - **AlertManager**: Triggers generation based on user schedules (daily/weekly) and `UserPreferences`.
  - **EmailService**: Renders `DigestTemplate` with gathered data (Consumer: top picks, saved searches; Expert: indices, YoY trends).

---

# Target Architecture (V4)

## System Overview
- Next.js web app (chat, search, dashboards, exports)
- Backend API (chat orchestration, tools, retrieval, analytics, notifications)
- Retrieval service (vector store + keyword + metadata + geo + sorting) behind API contracts
- Provider abstraction for multi-LLM support with consistent settings and policy controls
- Optional voice layer (ElevenLabs) for TTS/voice UX

## Deployment Target
- Web: Vercel
- API: container-based deployment (separate from web), versioned endpoints
