name: docker-deployment
description: Guidelines for Docker-based development and deployment.
---

# Docker & Deployment
Use Docker for consistent environments across dev and prod.

## Structure
- **Dockerfile**: Root level, multi-stage build (backend + frontend).
- **docker-compose.yml**: Orchestrates services (App, DB, Vector Store).

## Development
- **Start**: `docker-compose up --build`.
- **Logs**: `docker-compose logs -f`.
- **Shell**: `docker-compose exec app bash`.

## Best Practices
- **Images**: Use slim/alpine variants for production (e.g., `python:3.11-slim`).
- **Caching**: Order Dockerfile instructions to maximize layer caching.
- **Security**: Run as non-root user. Do not bake secrets into images.

## Environment
- Use `.env` file for local development (not committed).
- Inject secrets via platform environment variables in production (Vercel/Cloud).

## CI/CD
- GitHub Actions builds and pushes images on merge to main.
