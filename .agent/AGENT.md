---
version: 1.0.0
last_updated: 2026-03-21
---

# Antigravity Agent Configuration — AI Real Estate Assistant

## 1. Identity & Scope

**Role**: Gemini IDE (Antigravity) - AI Real Estate Assistant Partner.

**Project**: AI Real Estate Assistant — Conversational AI platform for real estate queries using a hybrid RAG + tool-based agent architecture with multi-LLM provider support.

**Mission**: Maximize velocity while maintaining safety and structure.

**Core Philosophy**: **TIME IS MONEY.**
- Find the simplest, working solution first.
- Avoid over-engineering.

---

## 🛑 Safety Rules (STOP & ASK)

Never auto-run: deletions, force push, dropping data, overwriting configs.

**CRITICAL**: Never expose API keys in the browser — always use backend proxy pattern.

---

## 📋 Configuration Modules

| Module | Path |
|--------|------|
| **Workspace Rules** | `.agent/workspace-rules.md` |
| **Workflows** | `.agent/workspace-workflows.md` |
| **Rules** | `.agent/rules/` |

---

## 🏗 Project Structure

```
ai-real-estate-assistant/
├── .agent/                    # Agent configuration
│   ├── AGENT.md               # This file
│   ├── workspace-rules.md     # Always-on rules (Antigravity)
│   ├── workspace-workflows.md # Slash command index
│   ├── rules/                 # Rule library
│   ├── workflows/             # Slash command files
│   └── skills/                # Agent skills
├── .gemini/
│   ├── rules/workspace-rules.md   # Gemini-specific rules
│   └── workflows/
├── apps/
│   ├── api/                   # FastAPI backend
│   │   ├── api/               # Route handlers
│   │   └── core/              # HybridPropertyAgent, QueryAnalyzer
│   └── web/                   # Next.js App Router frontend
├── chroma_db/                 # ChromaDB vector store
├── data/                      # Property data
└── tests/                     # pytest tests (unit + integration)
```

---

## 🏗️ Key Architecture Patterns

- **API Proxy**: Frontend never calls LLM providers directly — always via `/api/chat`
- **HybridPropertyAgent**: Routes between RAG (ChromaDB) and tool-based queries
- **QueryAnalyzer**: Classifies intent/complexity before routing

---

## 🔒 Non-Interactive Protocol

- Python: `python -m uvicorn api.main:app --reload --port 8000`
- `npm install` → use `npm install -y`
- `git commit` → always use `git commit -m "..."`

---

## 📄 Key Documents

| Document | Path |
|----------|------|
| **README** | `README.md` |
| **Quick Start** | `QUICKSTART.md` |
| **Claude config** | `CLAUDE.md` |
| **Workspace Rules** | `.agent/workspace-rules.md` |
| **Workflow Index** | `.agent/workspace-workflows.md` |


## 🚨 CRITICAL RULE: UNIFIED LOCAL-DEV SCRIPTS 🚨
**DO NOT use standard commands like 
pm run dev or docker-compose up directly.**
This project belongs to the NestSolo meta-repo and uses dynamic port allocation (via 
estdev) to prevent cross-agent conflicts.

To run the project locally, you MUST use the provided wrapper scripts:
- Native: ./scripts/start.sh or .\scripts\start.ps1
- Docker: ./scripts/start-docker.sh or .\scripts\start-docker.ps1
- Stop: ./scripts/stop.sh or .\scripts\stop.ps1

**How to find the active port:**
Once the script starts, the assigned port is written to the runtime directory. To discover it, read:
cat .runtime/port.txt
Alternatively, use cat .runtime/ports.json for a full list of allocated service ports.
