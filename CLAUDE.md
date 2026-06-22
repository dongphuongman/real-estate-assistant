# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Real Estate Assistant — conversational AI platform for property search. FastAPI backend (Python 3.12+) + Next.js frontend (React 19). Monorepo under `apps/`.

**Active branch:** `dev` (all PRs target this branch)

## MCP Servers

### Available via Global Config (Tier 0)
Always-on servers available in all sessions:
- **Documentation**: doc-context7 (library docs)
- **Task Management**: mgmt-taskmaster (TaskMaster AI)
- **Search**: search-brave (web + news), search-duckduckgo (free search)
- **Parse**: parse-firecrawl (site scraping)

### Available via Presets (Tier 1)
Load these via `cc-<name>` aliases when needed:
- **Research**: `cc-research` (search-exa, search-tavily, search-jina-reader, parse-jina)
- **Frontend**: `cc-frontend` (ui-playwright, ui-shadcn-ui)
- **Security**: `cc-sec` (sec-semgrep)
- **Docs**: `cc-docs` (doc-ref, doc-rtfm)
- **DevOps**: `cc-devops` (VPS SSH, deploy, monitoring)

### Configured in Project (.mcp.json)
This project has no product-specific MCP servers configured. All MCP functionality is provided via global config and presets.

**Usage**: Use global search, parse, and documentation servers for property research, content scraping, and documentation lookup during AI agent development.

## Commands

## 🚨 CRITICAL RULE: UNIFIED LOCAL-DEV SCRIPTS 🚨
**DO NOT use standard commands like
pm run dev or docker-compose up directly.**
This project uses dynamic port allocation to prevent cross-agent conflicts.

To run the project locally, you MUST use the provided wrapper scripts:
- Native: ./scripts/start.sh or .\scripts\start.ps1
- Docker: ./scripts/start-docker.sh or .\scripts\start-docker.ps1
- Stop: ./scripts/stop.sh or .\scripts\stop.ps1

**How to find the active port:**
Once the script starts, the assigned port is written to the runtime directory. To discover it, read:
cat .runtime/port.txt
Alternatively, use cat .runtime/ports.json for a full list of allocated service ports.


```bash
# Development
make dev                      # Auto-detect Docker or local mode
make dev-api                  # Backend only (localhost:8000)
make dev-web                  # Frontend only (localhost:3000)

# Backend (from apps/api/)
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (from apps/web/)
npm run dev

# Testing
make test                     # All tests (backend + frontend)
cd apps/api && pytest tests/unit tests/integration --cov=. -n auto   # Backend with coverage
cd apps/api && pytest tests/unit/test_query_analyzer.py -k test_fn   # Single test
cd apps/web && npm test       # Frontend

# Linting & Formatting
make lint                     # All (ruff + eslint)
make format                   # Format all code
cd apps/api && ruff check .   # Backend linting only
cd apps/web && npm run lint   # Frontend linting only

# Docker
docker compose -f deploy/compose/docker-compose.yml up --build
make docker-up / make docker-down / make docker-logs

# Security & CI
make security                 # All security scans (Gitleaks, Semgrep, Bandit, pip-audit)
make ci                       # Full CI pipeline locally
make sprav                    # Pre-release validation

# Setup
make setup                    # First-time environment setup
make install                  # Install all dependencies
```

## Architecture

### Monorepo Layout

```text
apps/
├── api/              # FastAPI backend
│   ├── api/          # Routers, main.py, dependencies.py, middleware/, auth.py
│   ├── agents/       # HybridAgent, QueryAnalyzer, services/, web_research_agent.py
│   ├── tools/        # LangChain tools (mortgage, comparison, etc.)
│   ├── models/       # LLM provider factory
│   ├── config/       # Settings
│   ├── db/           # SQLAlchemy models, schemas, repositories, database.py
│   ├── alembic/      # Database migrations
│   ├── vector_store/ # ChromaPropertyStore, KnowledgeStore, reranker
│   ├── data/         # Data loaders, enrichment pipeline, schemas
│   ├── services/     # Business logic services
│   ├── core/         # JWT, shared utilities
│   ├── notifications/ # Email service, scheduler, uptime monitor
│   ├── tests/        # unit/, integration/, e2e/, performance/
│   └── pyproject.toml # Python config (ruff line-length=100, target=py312)
└── web/              # Next.js App Router frontend
    └── src/
        ├── app/      # Pages and API routes
        ├── lib/      # API client, utilities
        ├── components/ # UI components
        ├── contexts/  # React contexts (Auth, Favorites)
        ├── hooks/     # Custom hooks
        └── i18n/      # Internationalization
```

### Request Flow

```text
Next.js :3000 → API Proxy (injects X-API-Key) → FastAPI :8000
                                                    │
                              ┌─────────────────────┼─────────────────┐
                              ↓                     ↓                 ↓
                        QueryAnalyzer      API Key / JWT Auth   SQLite/ChromaDB
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

### Key Patterns

**1. Dependency Injection** (`apps/api/api/dependencies.py`)

All major components via FastAPI `Depends()`:
- `get_llm()` / `get_llm_for_task()` — LLM with per-user/task preference cascade
- `get_vector_store()` — Cached ChromaPropertyStore (via `@lru_cache`)
- `get_agent()` — HybridAgent with retriever
- `get_optional_llm_with_details()` — LLM returning resolved provider/model metadata

**2. LLM Selection Priority**

1. `X-User-Email` header → DB task-specific preference → global preference
2. Request parameter override (`provider`/`model`)
3. System default per task type (`SYSTEM_DEFAULTS`)
4. Settings default (`DEFAULT_PROVIDER`)
5. Ollama fallback (if `OLLAMA_BASE_URL` configured)

**3. Query Routing** (`agents/query_analyzer.py` → `agents/hybrid_agent.py`)

| Complexity | Route | Example |
|------------|-------|---------|
| Simple | RAG-only | "What properties in Berlin?" |
| Medium | Hybrid (RAG + enhancement) | "2-bedroom apartments under 500k" |
| Complex | Agent + Tools | "Compare mortgage options for 3 properties" |

**4. Auth Dual-Mode**

| Auth Type | Use Case | Header |
|-----------|----------|--------|
| API Key | Backend access, basic endpoints | `X-API-Key` |
| JWT | User features (favorites, saved searches, market, leads) | `Authorization: Bearer <token>` |

JWT-dependent routers are conditionally included when `settings.auth_jwt_enabled` is true.

**5. API Proxy** (`apps/web/src/app/api/v1/[...path]/route.ts`)

Frontend never sends `X-API-Key` to browser. Browser → `/api/v1/*` → Next.js server injects key → FastAPI.

### Backend Task-Oriented File Map

| Task | Files |
|------|-------|
| Add LLM provider | `models/provider_factory.py`, `config/settings.py` |
| Add new tool | `tools/property_tools.py`, register in `agents/hybrid_agent.py` |
| Add API endpoint | `api/routers/<domain>.py`, mount in `api/main.py` |
| Modify query routing | `agents/query_analyzer.py`, `agents/hybrid_agent.py` |
| Add auth feature | `api/auth.py` (API key), `api/routers/auth_jwt.py` (JWT), `core/jwt.py` |
| Change prompts | `api/routers/prompt_templates.py`, `agents/intent_prompts.py` |
| Add data provider | `data/<provider>.py`, register in `data/factory.py` |
| DB schema change | `db/models.py`, `db/schemas.py`, add alembic migration |
| Add service | `services/<name>.py`, wire in `api/dependencies.py` |

### Frontend Task-Oriented File Map

| Task | Files |
|------|-------|
| Add page | `src/app/<route>/page.tsx` |
| Add API call | `src/lib/api.ts` |
| Add context | `src/contexts/<Context>.tsx`, add to `providers.tsx` |
| Add component | `src/components/<category>/<Component>.tsx` |

## Testing

### Backend (pytest)

Tests in `apps/api/tests/` — unit tests use mocks, integration tests hit in-memory SQLite.

```bash
cd apps/api
pytest tests/unit tests/integration --cov=. --cov-report=term -n auto
pytest tests/unit/test_query_analyzer.py -v            # Single file
pytest tests/unit/test_query_analyzer.py -k test_fn -v  # Single test
```

**Key fixtures** (`tests/conftest.py`):

| Fixture | Purpose |
|---------|---------|
| `async_client` | HTTP client with auth overrides, test app with market router |
| `db_session` | Fresh in-memory SQLite (`aiosqlite`) AsyncSession per function |
| `auth_headers` | JWT Bearer token for `test-user-123` |
| `unauth_client` | Unauthenticated client for testing auth requirements |
| `query_analyzer` | QueryAnalyzer instance |
| `sample_properties` | 5 test Property objects (Krakow/Warsaw apartments) |

Tests use `@pytest.mark.asyncio` for async and `pytest-timeout` (300s default).

### Frontend (Jest)

```bash
cd apps/web
npm test              # All tests
npm run test:watch    # Watch mode
npm run test:ci       # CI with coverage
```

Tests colocated in `__tests__/` next to source.

## CI Pipeline

GitHub Actions `.github/workflows/ci.yml` runs on push/PR to `main`, `dev`, `ver4`.

| Job | Description |
|-----|-------------|
| `gitleaks` | Secret scanning (all jobs guarded by `github.repository_owner == 'AleksNeStu'`) |
| `secret-validation` | Placeholder secret detection in deploy configs |
| `backend` | uv + Ruff + mypy + pytest with coverage gates |
| `frontend` | npm ci + ESLint + Jest with coverage |
| `security` | Bandit SAST |
| `semgrep` | Security rules |
| `trivy` | Container vulnerability scan |
| `compose_smoke` | Docker build + health check |

**Local CI:** `make ci` or `python scripts/workflows/full_ci.py`

## Pre-Commit Hooks

`.pre-commit-config.yaml` — 3-layer security:

| Hook | Purpose | Config |
|------|---------|--------|
| Gitleaks | Secret scanning | `.gitleaks.toml` |
| Ruff | Python linting/formatting | `apps/api/pyproject.toml` (line-length=100) |
| lint-staged | Frontend (Prettier + ESLint) | `package.json` |

Semgrep runs in CI only. Install hooks: `pre-commit install`

## Configuration

`.env` (copy from `.env.example`):

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

Frontend env in `apps/web/.env.local`.

## Branching & Commits

- `dev` — Active development (PRs target this)
- `main` — Production releases
- Feature branches: `feature/short-description`
- Commit format: `type(scope): description (Task #XX)`

## Task Management

Uses **Taskmaster** (`.taskmaster/tasks/`).

## Relevant Global Skills

When working on this project, leverage these global skills:
- `/commit-work` — High-quality git commits
- `/systematic-debugging` — Structured bug investigation
- `/verification-before-completion` — Pre-completion validation
- `/python-testing-patterns` — Python test strategies
- `/openapi-to-typescript` — API type generation
- `/shadcn-ui` — Component library patterns

### Project Skills
- `check-saas-security` — Security audit
- `tenant-isolate` — Multi-tenant data isolation
- `billing-implement` — Billing implementation

## Public Repo Maintenance

This repo (`AleksNeStu/ai-real-estate-assistant`) is **frozen** for demo purposes. Active development happens in a private mirror; the public repo stays unarchived and must remain healthy for demo purposes.

### Allowed Changes (Health Pushes Only)

| Category | Examples | When |
|----------|----------|------|
| Security patches | Dependabot critical/high CVEs | Immediate |
| CI fixes | Pipeline breaks, flaky tests | When CI is red |
| Demo health | Demo mode broken, render staging down | When demo breaks |
| Secret rotation | Leaked or expired keys | Immediate |
| Doc fixes | Broken badges, dead links, typos | Anytime |

### Blocked Changes

- New features or UI changes
- Architecture or API changes
- Performance improvements (unless demo-breaking)
- Dependency bumps below critical/high severity
- Anything that adds new code beyond fixes

### Force-Push Policy

| Remote | Force-push | Reason |
|---|---|---|
| `AleksNeStu/ai-real-estate-assistant` | ❌ **NEVER** | Public, frozen, canonical demo repo. History must remain linear and append-only. |
| `NestLab-Tech/ai-real-estate-assistant` | ✅ Allowed | Working mirror (force-push to recover from local-only divergence is permitted). |
| `dev-scaler/ai-real-estate-assistant` | ✅ Allowed | Working mirror (force-push to recover from local-only divergence is permitted). |
| Any other remote | ❌ Default | Ask the user before force-pushing. |

Always use `--force-with-lease=refs/heads/<branch>:<expected-sha>` (not bare `--force`) when force-pushing to a mirror, so the push aborts if the remote ref has moved since the last fetch. Bare `--force` is forbidden on every remote, including the working mirrors — the lease guard exists to detect concurrent pushes.

### Health Push Workflow

1. Check Dependabot alerts — only critical/high CVEs
2. Run `make ci` locally — verify pipeline
3. Push to `feature/health-*` branch
4. Verify CI passes on GitHub
5. Merge to `dev`
6. Verify Render staging deploys and health check passes

### Frequency

- **Monthly** scheduled check (Dependabot alerts, CI status, demo health)
- **On-demand** for critical CVEs or broken demo

### Render Staging

The Render staging deployment must remain functional. After any health push, verify:

- `https://ai-real-estate-assistant-api.onrender.com/health` returns 200
- Frontend loads and demo mode works
