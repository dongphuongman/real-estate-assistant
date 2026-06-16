# AI Real Estate Assistant — Architecture

> Canonical patterns: [NestSolo ARCHITECTURE.md](../../../../docs/architecture/ARCHITECTURE.md)
> Reference pattern: [02.003](../../../../docs/research/architecture/02.003-large-saas-auth-database-pattern-2026-06-16.md)

**Track:** Large-SaaS
**Stack:** FastAPI (Python 3.12+) + Next.js 19 + React 19 (monorepo `apps/api` + `apps/web`)
**Status:** Production-ready (frozen demo per Rule 09c)

## Layer summary

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js 19 (App Router), React 19, Tailwind CSS | `apps/web` |
| Backend | FastAPI in `apps/api` (routers, dependencies, middleware, auth.py) | |
| Auth | Per-product FastAPI JWT | See [docs/auth.md](auth.md) |
| Database | PostgreSQL 16 + SQLAlchemy + Alembic | See [docs/database.md](database.md) |
| AI | Multi-provider (OpenAI, Gemini) for conversational property search | Per [ADR-004](../../../../docs/architecture/decisions/004-ai-provider-governance.md) |
| Deploy | Dokploy | See [docs/deploy.md](deploy.md) |

## Monorepo structure

```
apps/
├── api/        # FastAPI backend
└── web/        # Next.js frontend
```

## Key decisions

- Per [ADR-019](../../../../docs/architecture/decisions/019-product-portfolio-isolation.md) — independent auth controller, no shared SSO.
- Frozen demo per Rule 09c (CI disabled for this repo).

## Acquirability test

✅ Own DB, own auth, own secrets, own AI provider keys.
