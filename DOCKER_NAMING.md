# DOCKER_NAMING

Container naming convention used across this product's `docker-compose*` files.

## Pattern

```
nestlab-{scope}-{product}-{service}
```

| Segment | Allowed values | Notes |
|---|---|---|
| `scope`   | `prod`                  | This public repo is the production demo (deployed to `propvector-web.onrender.com`); no local dev compose for it. |
| `product` | `ai-re`                  | AI Real Estate Assistant. |
| `service` | `backend`, `frontend`, `ollama`, `searxng`, `redis`, `postgres` | See "Applied in" below for the full mapping. |

## Examples

- `nestlab-prod-ai-re-backend`
- `nestlab-prod-ai-re-frontend`
- `nestlab-prod-ai-re-redis`
- `nestlab-prod-ai-re-ollama`
- `nestlab-prod-ai-re-searxng`
- `nestlab-prod-ai-re-postgres`

## Applied in

- `deploy/compose/docker-compose.yml` — full stack
- `deploy/compose/docker-compose.quick.yml` — minimal stack

## Why a separate doc

The compose files are the single source of truth for the **current** container names. This doc is the source of truth for the **naming rule** itself — the convention that future containers, copy-pasted compose files, and external orchestration (e.g. Render, Dokploy) should follow without re-deriving the pattern from existing services.

## History

- **PR #214** (`ac74f8c`, on `release/v5.0.7`): renamed `ai-backend`, `ai-frontend`, `ollama`, `searxng`, `ai-redis`, `postgres` → `nestlab-prod-ai-re-{backend,frontend,ollama,searxng,redis,postgres}` in `deploy/compose/docker-compose.yml` and `deploy/compose/docker-compose.quick.yml`. This document was added alongside the v5.0.7 release to document the convention referenced in that commit's message.
