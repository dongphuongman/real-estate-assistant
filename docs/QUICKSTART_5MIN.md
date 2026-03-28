# 5-Minute Quickstart

Get the AI Real Estate Assistant running locally with Docker in under 5 minutes.

> **Time:** ~5 min (first run builds from source, ~3 min on subsequent starts)
> **Requirements:** Docker + 1 LLM API key

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose)
- 1 LLM API key — any of:
  - [OpenAI](https://platform.openai.com/api-keys)
  - [Anthropic](https://console.anthropic.com/settings/keys)
  - [Google Gemini](https://aistudio.google.com/app/apikey) (free tier available)

---

## Step 1 — Clone

```bash
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant
```

## Step 2 — Configure

```bash
# Copy the Docker Compose environment template
cp deploy/compose/.env.example deploy/compose/.env
```

Open `deploy/compose/.env` in any editor. You only need to fill in **one API key**:

```ini
# Uncomment and paste your key (only one is needed):
OPENAI_API_KEY=sk-your-key-here

# This already has a working default — leave it as-is:
# API_ACCESS_KEY=change-me-to-a-secure-random-key
```

All other settings have sensible defaults. Skip them.

## Step 3 — Start

```bash
docker compose -f deploy/compose/docker-compose.yml up --build -d
```

This starts the backend, frontend, and Redis. First run builds images (~3-5 min). Subsequent starts are instant.

## Step 4 — Verify

Open in your browser:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3082 |
| **Backend API docs** | http://localhost:8082/docs |
| **Health check** | http://localhost:8082/health |

Run the verification script for a quick health check:

```bash
# macOS / Linux
bash scripts/docker/quickstart-verify.sh

# Windows PowerShell
.\scripts\docker\quickstart-verify.ps1
```

You should see:

```
Backend health:   PASS
Frontend:         PASS
API auth:         PASS

All checks passed. Open http://localhost:3082 to start chatting.
```

---

## What's Next?

- Open http://localhost:3082 and ask a question about properties
- Upload documents in the Knowledge tab for RAG-powered Q&A
- Explore the API at http://localhost:8082/docs

### Going Further

- [Developer setup (local without Docker)](../docs/development/QUICKSTART.md)
- [Full Docker options (Ollama, GPU, web search)](../docs/development/QUICKSTART.md)
- [Troubleshooting](../docs/development/TROUBLESHOOTING.md)
- [Architecture overview](../docs/README.md)

### Stop & Clean Up

```bash
docker compose -f deploy/compose/docker-compose.yml down
```

To remove all data (ChromaDB, Redis, volumes):

```bash
docker compose -f deploy/compose/docker-compose.yml down -v
```
