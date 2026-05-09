# Deployment Guide

## Architecture

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Vercel | `ai-real-estate-assistant.vercel.app` |
| Frontend (alt) | Render | `realestate-web.onrender.com` |
| Backend | Render | `realestate-api.onrender.com` |
| Docker | GHCR | `ghcr.io/aleksnestu/ai-real-estate-assistant` |

## Prerequisites

### Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Link project: `cd apps/web && vercel link`
3. Set environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` = `/api/v1`
   - `API_ACCESS_KEY` = (from 1Password/shared secrets)
   - `BACKEND_API_URL` = `https://realestate-api.onrender.com/api/v1`
   - `NEXT_PUBLIC_SENTRY_DSN` = (optional)

### Render
1. Create account at render.com
2. Create new Web Service from GitHub repo `AleksNeStu/ai-real-estate-assistant`
3. `render.yaml` auto-configures both services
4. Set required secrets in Render dashboard:
   - `API_ACCESS_KEY` — primary API auth key
   - `ZAI_API_KEY` — LLM provider key
   - `SENTRY_DSN` — error tracking (optional)

### GitHub Secrets (for CI/CD)
| Secret | Purpose |
|--------|---------|
| `VERCEL_TOKEN` | Vercel deployment token |
| `RENDER_API_KEY` | Render API key |
| `RENDER_SERVICE_ID_API` | Backend service ID |
| `RENDER_SERVICE_ID_WEB` | Frontend service ID |
| `API_ACCESS_KEY` | For smoke tests |

## Deploy Methods

### 1. Automatic (Push to `main`)
Pushing to `main` triggers the deploy workflow:
- Validates configs
- Deploys backend to Render
- Deploys frontend to Vercel
- Runs smoke tests

### 2. Docker Compose (Self-hosted)
```bash
# Production stack with PostgreSQL
make deploy-prod

# Quick start with GHCR images
make quickstart

# Validate configs
make deploy-validate
```

### 3. Manual Deploy
```bash
# Backend (Render)
curl -X POST "https://api.render.com/v1/services/$SERVICE_ID/deploys" \
  -H "Authorization: Bearer $RENDER_API_KEY"

# Frontend (Vercel)
cd apps/web && vercel --prod
```

## Post-Deploy Verification

```bash
# Backend health
curl https://realestate-api.onrender.com/health

# Frontend
curl -s -o /dev/null -w "%{http_code}" https://ai-real-estate-assistant.vercel.app

# Smoke test
make smoke-test
```

## Rollback

- **Vercel**: `vercel rollback` or redeploy previous commit
- **Render**: Manual redeploy from Render dashboard → select previous commit
- **Docker**: `docker compose down` → change image tag → `docker compose up -d`
