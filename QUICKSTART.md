# Quick Start Guide

> 🚀 Three ways to run AI Real Estate Assistant

---

## 1. Local Development (Без Docker)

### Windows (PowerShell)
```powershell
.\scripts\dev\start.ps1
```

### Linux/Mac (Bash)
```bash
./scripts/dev/start.sh
```

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 2. Docker Development

### Windows (PowerShell)
```powershell
# CPU mode
.\scripts\dev\run-docker-cpu.ps1

# GPU mode
.\scripts\dev\run-docker-gpu.ps1

# GPU + Internet access
.\scripts\dev\run-docker-gpu-internet.ps1
```

### Linux/Mac (Bash)
```bash
# Auto-detect GPU
./scripts/dev/run-docker.sh

# Force CPU mode
./scripts/dev/run-docker.sh cpu

# Force GPU mode
./scripts/dev/run-docker.sh gpu

# Enable internet access
./scripts/dev/run-docker.sh internet
```

---

## 3. Deploy to Vercel

### Windows (PowerShell)
```powershell
.\scripts\deploy-vercel.ps1
```

### Linux/Mac (Bash)
```bash
./scripts/deploy-vercel.sh
```

**The script will:**
1. Check Vercel CLI is installed
2. Guide you through login
3. Link your project
4. Show instructions for environment variables
5. Deploy to production

**Prerequisites:**
- Install Vercel CLI: `npm i -g vercel`
- Have `.env` file configured with API keys

---

## Troubleshooting

### Frontend dependencies not installed?
```powershell
cd apps/web
npm install
cd ..
```

### Python dependencies not installed?
```powershell
# Using uv (recommended)
uv pip install -e .[dev]

# Or using pip
pip install -e .[dev]
```

### Vercel CLI not found?
```bash
npm i -g vercel
```

---

## Full Documentation

See [deployment/](deployment/) folder for detailed guides.
