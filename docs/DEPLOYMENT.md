# Deployment Guide

This guide covers deploying the AI Real Estate Assistant (V4) using Docker or on a VPS/OVH server.

## Overview
- **Frontend**: Next.js 14+ (Port 3000)
- **Backend**: FastAPI (Port 8000)
- **Vector Store**: ChromaDB (local dev) or pgvector (optional)
- **Database**: PostgreSQL (Neon/Supabase) for server‑side preferences and future features

---

## 🚀 Option 1: Docker Deployment (Recommended)

The easiest way to run the full stack (Backend + Frontend + Services).

### Prerequisites
- Docker & Docker Compose installed.
- Valid `.env` file (copy from `.env.example`).
- BYOK for LLM: either `OPENAI_API_KEY` (user‑provided) or local Ollama/Llama 3.

### Steps
1. **Prepare Environment**
   ```powershell
   Copy-Item .env.example .env
   # Edit .env and set OPENAI_API_KEY (or configure OLLAMA base URL), DB settings
   ```

2. **Run with Docker Compose**
   ```powershell
   docker compose up -d --build
   ```

3. **Access Services**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000/docs`
   - Redis (optional): `redis://localhost:6379` (`docker compose up -d redis`)
   - Postgres (optional): provision Neon/Supabase and set env variables

4. **Logs & Maintenance**
   ```powershell
   # View logs
   docker compose logs -f

   # Stop services
   docker compose down
   ```

---

## ☁️ Option 2: VPS / OVH Cloud Deployment

For deploying on a Linux server (Ubuntu/Debian recommended).

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker & Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# (Log out and back in)
```

### 2. Application Setup
```bash
# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Configuration
cp .env.example .env
nano .env
```

### 3. Nginx Reverse Proxy (Optional)
To serve on a domain (e.g., `realestate.ai`) with SSL.

1. **Install Nginx**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```

2. **Configure Nginx**
   Create `/etc/nginx/sites-available/ai-real-estate` with:
   ```nginx
   server {
       server_name your-domain.com;
       
       # Frontend
       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
       }

       # Backend API
       location /api/ {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Enable & Secure**
   ```bash
   sudo ln -s /etc/nginx/sites-available/ai-real-estate /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   
   # Setup SSL
   sudo certbot --nginx -d your-domain.com
   ```

---

## ☁️ Option 3: Serverless (Vercel + Railway/Render)

### Frontend (Vercel)
1. Import `frontend/` directory to Vercel.
2. Set Environment Variables:
   - `NEXT_PUBLIC_API_URL`: URL of your backend (e.g., `https://api.yourdomain.com/api/v1`).

### Backend (Railway/Render)
1. Connect repository.
2. Root directory: `.` (Project Root).
3. Build Command: `pip install -r requirements.txt`.
4. Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`.
5. Set Environment Variables from `.env`.

### BYOK Notes
- Never expose secrets in frontend. All keys are server‑side env variables.
- For local models, configure Ollama (`OLLAMA_BASE_URL`) and select model (e.g., `llama3`).
- Feature flags choose providers; Community Edition publishes only safe toggles.
