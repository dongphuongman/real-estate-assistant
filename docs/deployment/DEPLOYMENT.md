# Deployment Guide

This guide covers deploying the AI Real Estate Assistant.

## Prerequisites

Before deploying, ensure you have:

- A GitHub repository with the code
- Generated `API_ACCESS_KEY` (run: `openssl rand -hex 32`)
- Docker and Docker Compose (for local/containerized deployment)
- Render account (for staging)

---

## Architecture Overview

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Browser       │──────│  Render (Front) │──────│  Render (Back)  │
└─────────────────┘      │  Next.js App    │      │  FastAPI        │
                         │  /api/v1/*      │      │  Port 10000     │
                         └─────────────────┘      └─────────────────┘
```

**Key:** The frontend proxies all `/api/v1/*` requests server-side, injecting the API key. The browser never sees backend credentials.

---

## Environment Variables

| Variable | Description | Where to Set |
|----------|-------------|-------------|
| `API_ACCESS_KEY` | Backend authentication key | Backend host + Frontend |
| `BACKEND_API_URL` | Backend endpoint URL | Frontend only (server-side) |
| `NEXT_PUBLIC_API_URL` | Frontend API prefix (`/api/v1`) | Frontend (build time) |
| `OPENAI_API_KEY` | LLM provider key | Backend |
| `CORS_ALLOW_ORIGINS` | Allowed origins | Backend |

---

## Docker Compose Deployment

### Step 1: Clone and Configure

```bash
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant
cp .env.example .env
# Edit .env with your keys
```

### Step 2: Start Services

```bash
docker compose -f deploy/compose/docker-compose.yml up -d

# Check status
docker compose -f deploy/compose/docker-compose.yml ps

# View logs
docker compose -f deploy/compose/docker-compose.yml logs -f
```

### Step 3: Verify

```bash
# Backend health
curl http://localhost:8000/health

# Frontend
open http://localhost:3000
```

---

## Render Staging Deployment

The project includes `render.yaml` for staging.

### Step 1: Create Backend Service

1. Go to [render.com](https://render.com) → "New" → "Web Service"
2. Connect repository: `AleksNeStu/ai-real-estate-assistant`
3. Configure:

| Setting | Value |
|---------|-------|
| Branch | `dev` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |

4. Add environment variables:

```bash
ENVIRONMENT=production
API_ACCESS_KEY=<your-key>
OPENAI_API_KEY=sk-...
CORS_ALLOW_ORIGINS=https://your-frontend.onrender.com
```

### Step 2: Create Frontend Service

1. "New" → "Web Service" → same repository
2. Configure:

| Setting | Value |
|---------|-------|
| Root Directory | `apps/web` |
| Branch | `dev` |
| Build Command | `npm run build` |
| Start Command | `npm run start` |

3. Add environment variables:

```bash
BACKEND_API_URL=https://your-backend.onrender.com
API_ACCESS_KEY=<same-key-as-backend>
NEXT_PUBLIC_API_URL=/api/v1
```

### Step 3: Deploy

Click "Deploy" — Render builds and deploys automatically on push to `dev`.

### Known Limitations (Free Tier)

- Cold start ~150s after inactivity (services spin down)
- First request may return 502 — retry after a few minutes

---

## Post-Deployment Verification

```bash
# Backend health
curl https://your-backend.onrender.com/health

# Auth test
curl -X POST https://your-frontend.onrender.com/api/v1/verify-auth \
  -H "X-API-Key: $API_ACCESS_KEY"
```

---

## Troubleshooting

### CORS Errors

1. Verify `CORS_ALLOW_ORIGINS` includes your frontend URL
2. Check `ENVIRONMENT=production` is set

### 502 Bad Gateway

- Backend may be cold-starting (wait 2-3 min)
- Check backend logs in Render Dashboard

### Build Failures

- Verify all environment variables are set
- Check build logs in Render Dashboard

---

## Related

- [DEPLOYMENT_VARIANTS.md](../../DEPLOYMENT_VARIANTS.md) — comparison of Local Docker, VPS, and Render free tier (feature matrix)
- [Docker Deployment Guide](../guides/deployment.md)
- [CI/CD Pipeline](../guides/ci-cd.md)
- [Troubleshooting](../guides/troubleshooting.md)
