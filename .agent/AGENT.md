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
