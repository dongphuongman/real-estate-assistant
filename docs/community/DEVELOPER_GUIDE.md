# Developer Guide

Architecture and development reference for the AI Real Estate Assistant Community Edition (CE).

## Architecture Overview

```
apps/
├── api/                  # FastAPI backend (Python 3.12+)
│   ├── api/              # Routers, auth, middleware, dependencies
│   │   ├── routers/      # Endpoint handlers by domain
│   │   ├── dependencies.py  # DI container (get_llm, get_vector_store, etc.)
│   │   ├── auth.py       # API key authentication
│   │   └── main.py       # FastAPI app factory, CORS, lifespan
│   ├── agents/           # AI agent orchestration
│   │   ├── hybrid_agent.py      # Main agent with tool routing
│   │   ├── query_analyzer.py    # Query complexity classification
│   │   └── web_research_agent.py # Web search integration
│   ├── mcp/              # MCP connector framework
│   │   ├── base.py       # MCPConnector[T] abstract base class
│   │   ├── registry.py   # Connector discovery and registration
│   │   └── connectors/   # Individual connector implementations
│   ├── tools/            # LangChain tools
│   │   ├── property_tools.py     # Property search, comparison
│   │   ├── mortgage_tools.py     # Mortgage calculator
│   │   ├── tco_tools.py          # Total Cost of Ownership
│   │   └── neighborhood_tools.py # Neighborhood scoring
│   ├── models/           # LLM provider factory
│   │   └── provider_factory.py   # Multi-provider LLM routing
│   ├── vector_store/     # ChromaDB integration
│   │   ├── chroma_store.py       # Property vector search
│   │   └── knowledge_store.py    # Document knowledge base
│   ├── data/             # Data loading and enrichment
│   │   ├── csv_loader.py         # CSV/Excel data loading
│   │   ├── providers/            # Data source adapters
│   │   └── schemas.py            # PropertyCollection, PropertySchema
│   ├── db/               # SQLAlchemy ORM layer
│   │   ├── database.py           # Async session factory
│   │   ├── models.py             # SQLAlchemy models
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── config/           # Application settings
│   │   └── settings.py           # Environment-based configuration
│   └── tests/            # Test suite
│       ├── unit/                 # Isolated unit tests (mocked)
│       ├── integration/          # Integration tests (in-memory DB)
│       ├── e2e_backend/          # End-to-end API tests
│       ├── performance/          # Benchmark and load tests
│       └── resilience/           # Graceful degradation tests
└── web/                  # Next.js App Router frontend
    └── src/
        ├── app/          # Pages and API routes (App Router)
        │   ├── [locale]/ # Internationalized routes
        │   └── api/v1/   # API proxy (injects backend API key)
        ├── components/   # UI components
        │   ├── ui/       # shadcn/ui primitives
        │   ├── search/   # Search-related components
        │   ├── chat/     # Chat interface
        │   └── admin/    # Admin panel components
        ├── contexts/     # React contexts (Auth, Favorites)
        ├── hooks/        # Custom React hooks
        ├── lib/          # Utilities, API client, types
        └── i18n/         # Internationalization (en, pl, uk, de)
```

## Request Flow

```
Browser → Next.js (:3000) → API Proxy (injects X-API-Key) → FastAPI (:8000)
                                                              │
                            ┌─────────────────────────────────┼──────────────────┐
                            ↓                                 ↓                  ↓
                      QueryAnalyzer              API Key / JWT Auth      SQLite / ChromaDB
                            │
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
          RAG-only      Agent+Tools    Hybrid
          (simple)      (complex)     (medium)
              │             │             │
              └─────────────┴─────────────┘
                            ↓
                   ChromaDB Vector Store
```

### Query Routing

| Complexity | Route | Example Query |
|------------|-------|---------------|
| Simple | RAG-only | "What properties are in Berlin?" |
| Medium | Hybrid (RAG + enhancement) | "2-bedroom apartments under 500k" |
| Complex | Agent + Tools | "Compare mortgage options for 3 properties" |

## Key Patterns

### Dependency Injection

All major components are injected via FastAPI `Depends()` in `apps/api/api/dependencies.py`:

- `get_llm()` / `get_llm_for_task()` — LLM with per-user/task preference cascade
- `get_vector_store()` — Cached ChromaPropertyStore (via `@lru_cache`)
- `get_agent()` — HybridAgent with retriever
- `get_db()` — Async SQLAlchemy session

### LLM Provider Cascade

The system supports multiple LLM providers with automatic fallback:

1. User-specific preference (from DB)
2. Request parameter override (`provider`/`model`)
3. System default per task type
4. Settings default (`DEFAULT_PROVIDER`)
5. Ollama fallback (if `OLLAMA_BASE_URL` configured)

Supported providers: OpenAI, Anthropic, Google Gemini, Ollama (local).

### Auth Dual-Mode

| Auth Type | Use Case | Header |
|-----------|----------|--------|
| API Key | Backend access, basic endpoints | `X-API-Key` |
| JWT | User features (favorites, saved searches) | `Authorization: Bearer <token>` |

JWT-dependent routers are conditionally included when `settings.auth_jwt_enabled` is true.

### API Proxy (Frontend)

The frontend never sends `X-API-Key` to the browser directly. All API calls go through:

```
Browser → /api/v1/* → Next.js server route → injects API key → FastAPI backend
```

This is handled in `apps/web/src/app/api/v1/[...path]/route.ts`.

## MCP Connector Pattern

Community connectors follow the `MCPConnector[T]` abstract base class:

1. Extend `MCPConnector` from `apps/api/mcp/base.py`
2. Implement required methods: `connect()`, `disconnect()`, `health_check()`, `execute()`
3. Register in `apps/api/mcp/registry.py`
4. Add to edition allowlist in `apps/api/config/mcp_allowlist.yaml`
5. Add tests in `apps/api/tests/unit/mcp/`

Reference implementation: `apps/api/mcp/connectors/web_scraper.py`

### Edition Allowlist

| Edition | Available Connectors |
|---------|---------------------|
| Community (CE) | echo_stub, google_maps, openstreetmap, web_scraper |
| Pro | + salesforce, stripe, hubspot |
| Enterprise | + slack, custom connectors |

## Data Layer

### Property Loading

Properties are loaded from multiple sources:

- **CSV/Excel files** — `DataLoaderCsv` / `DataLoaderExcel` in `apps/api/data/csv_loader.py`
- **URL endpoints** — Via `POST /admin/ingest` endpoint
- **Portal APIs** — Via `DataPortalClient`

Each source is tagged with `source` and `source_type` for tracking and deletion via `delete_by_source()`.

### Vector Search

ChromaDB stores property embeddings for semantic search:

- `ChromaPropertyStore` — Property vector store with metadata filtering
- `KnowledgeStore` — Document knowledge base for RAG
- Embeddings generated via configured LLM provider

## Testing

### Backend Tests

```bash
cd apps/api

# Unit tests (mocked, fast)
pytest tests/unit -v

# Integration tests (in-memory SQLite)
pytest tests/integration -v

# All tests with coverage
pytest tests/unit tests/integration --cov=. --cov-report=term -n auto

# Single test
pytest tests/unit/test_query_analyzer.py -k test_classify_intent -v
```

Key fixtures in `tests/conftest.py`:

| Fixture | Purpose |
|---------|---------|
| `async_client` | HTTP client with auth overrides |
| `db_session` | Fresh in-memory SQLite AsyncSession |
| `auth_headers` | JWT Bearer token for test user |
| `query_analyzer` | QueryAnalyzer instance |
| `sample_properties` | 5 test Property objects |

### Frontend Tests

```bash
cd apps/web
npm test           # All tests
npm run test:watch # Watch mode
npm run test:ci    # CI with coverage
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `ENVIRONMENT` | Yes | `local` for development |
| `API_ACCESS_KEY` | Yes | Backend API key |
| `OPENAI_API_KEY` | One+ | LLM provider key |
| `ANTHROPIC_API_KEY` | One+ | LLM provider key |
| `GOOGLE_API_KEY` | One+ | LLM provider key |
| `CORS_ALLOW_ORIGINS` | Yes | Allowed frontend origins |
| `OLLAMA_BASE_URL` | No | Local LLM fallback |
| `ENABLE_JWT_AUTH` | No | Enable JWT auth (default: false) |

## Common Tasks

| Task | Files to Modify |
|------|----------------|
| Add LLM provider | `models/provider_factory.py`, `config/settings.py` |
| Add new tool | `tools/property_tools.py`, register in `agents/hybrid_agent.py` |
| Add API endpoint | `api/routers/<domain>.py`, mount in `api/main.py` |
| Add MCP connector | `mcp/connectors/<name>.py`, register in `mcp/registry.py` |
| Add data provider | `data/<provider>.py`, register in `data/providers/factory.py` |
| DB schema change | `db/models.py`, `db/schemas.py`, add Alembic migration |
| Add frontend page | `web/src/app/<route>/page.tsx` |
| Add frontend component | `web/src/components/<category>/<Component>.tsx` |

## Quick Reference

```bash
make help          # Show all available commands
make dev           # Start development servers
make test          # Run all tests
make lint          # Run linting
make security      # Run security scans
make ci            # Run full CI locally
make sprav         # Pre-release validation
```

## Related Documentation

- [CONTRIBUTING.md](../../CONTRIBUTING.md) — Contribution guidelines
- [SECURITY.md](../../SECURITY.md) — Security policy
- [Community Metrics](METRICS.md) — Community health tracking
- [Development Setup](../development/CONTRIBUTING.md) — Detailed setup guide
- [Troubleshooting](../development/TROUBLESHOOTING.md) — Common issues and fixes
