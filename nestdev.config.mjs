/**
 * nestdev.config.mjs — AI Real Estate Assistant Development Configuration
 *
 * AI Real Estate Assistant: AI-powered assistant for real estate agencies
 * (Next.js + FastAPI + ChromaDB)
 */
export default {
  name: 'ai-real-estate-assistant',

  services: {
    frontend: {
      type: 'nextjs',
      cwd: 'apps/web',
      preferredPort: 3830,
      portRange: 'frontend',
      command: 'npm run dev -- --port ${PORT}',
      readyPattern: 'Ready in',
      env: {
        NODE_ENV: 'development',
      },
    },
    backend: {
      type: 'fastapi',
      cwd: 'apps/api',
      preferredPort: 8030,
      portRange: 'backend',
      command: 'uv run uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --reload',
      readyPattern: 'Application startup complete',
      healthCheck: 'http://localhost:${PORT}/api/v1/health',
      env: {
        DEBUG: 'true',
      },
    },
  },

  docker: {
    composeFile: 'deploy/compose/docker-compose.yml',
    portVars: {
      FRONTEND_PORT: 'frontend',
      BACKEND_PORT: 'backend',
    },
  },
};
