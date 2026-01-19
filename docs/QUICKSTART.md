# Quickstart: Run Your AI Realtor in 5 Minutes

## Prerequisites
- Docker and Docker Compose
- Create `.env` from `.env.example`
- Provide BYOK: `OPENAI_API_KEY` or configure local Ollama (`OLLAMA_BASE_URL`)

## Steps
1. Copy environment:
   ```
   cp .env.example .env
   ```
2. Set keys and DB options in `.env`.
3. Start services:
   ```
   docker-compose up -d --build
   ```
4. Open:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000/docs

## Local RAG
- Upload PDFs/Docs in the app and query property details.

## Troubleshooting
- Ensure backend CORS allows the frontend origin.
- Check logs: `docker-compose logs -f`.

