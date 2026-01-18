# Architecture (V4)

## System Overview
- Next.js web app (chat, search, dashboards, exports)
- FastAPI backend (chat orchestration, tools, retrieval, analytics, notifications)
- Query Analyzer (intent, filters)
- Hybrid processing: simple → RAG, complex → Agent + Tools
- Tools: mortgage, comparison, analysis
- Strategic Reranker (investor/family/bargain strategies, valuation boost)
- Hedonic Valuation Model (fair price estimation, undervaluation detection)
- Retrieval: ChromaDB (semantic + keyword, MMR), geo radius, price filters, sorting
- Response formatter

## Key Data Flows
- Data load → embeddings → ChromaDB persist → hybrid retrieval → rerank → response
- Web app → API (/search, /chat, /tools, /settings, /admin) → structured JSON or downloadable files
- **Digest Generation**:
  - **DigestGenerator**: Orchestrates data gathering from `VectorStore` (new matches for saved searches) and `MarketInsights` (trends/expert data).
  - **AlertManager**: Triggers generation based on user schedules (daily/weekly) and `UserPreferences`.
  - **EmailService**: Renders `DigestTemplate` with gathered data (Consumer: top picks, saved searches; Expert: indices, YoY trends).

---

## Technology Stack
- Web: Next.js 16 (App Router), TypeScript, Tailwind CSS v4
- Backend: FastAPI (Python 3.12), Pydantic, SSE streaming, rate limiting, request IDs
- Vector store: ChromaDB 0.5+ (dev), optional pgvector (Neon) for prod
- Embeddings: FastEmbed (BGE) or OpenAI embeddings
- Data: Pandas 2.2+, Pydantic 2.5+

## API Surface
- Search: `/api/v1/search`
- Chat: `/api/v1/chat` (SSE supported)
- Tools: `/api/v1/tools/*` (mortgage, compare, price analysis, location analysis)
- Settings: `/api/v1/settings/notifications`, `/api/v1/settings/models`
- Auth: `/api/v1/auth/*` (email one-time code login, session token)
- Admin: `/api/v1/admin/*` (ingest/reindex/health)

## Deployment
- Web: Vercel
- API: container-based deployment (separate from web), versioned endpoints
