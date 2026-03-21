---
description: "AI Real Estate Assistant Workflow Index — All slash command workflows for Antigravity."
---

# AI Real Estate Assistant — Workspace Workflows Index

> **Source**: `.agent/workflows/` (workflow files across tiers)
> Type `/` in chat to trigger any workflow listed below.

---

## Workflow Strategy Matrix

| Complexity | Scope | Use |
|-----------|-------|-----|
| **High** (Tier 0) | Strategic / Full Lifecycle | `/co-orchestrator` |
| **Medium** (Tier 1-3) | Specific Domain | `/lead-*`, `/expert-*` |
| **Low** (Tactical) | Single Task | Direct request |

> **Default**: When unsure, use `/co-orchestrator` — it auto-delegates.

---

## Tier 0: Co-Orchestration

- `/co-orchestrator` — Global orchestrator (auto-delegates to right expert)

---

## Tier 1: Leadership (Planning Phase)

Use BEFORE coding — planning, strategy, architecture decisions.

- `/lead-tech` — Technical lead (RAG pipeline, agent architecture)
- `/lead-docs` — Documentation lead
- `/lead-research` — Research lead (LLM providers, real estate data)

---

## Tier 2: Development (Execution Phase)

Use DURING coding — implementing features, writing code.

- `/dev-backend` — Backend developer (FastAPI, ChromaDB, HybridPropertyAgent)
- `/dev-frontend` — Frontend developer (Next.js App Router, React 19, API proxy)
- `/dev-deploy` — DevOps deployer (Docker Compose, Railway, Vercel)
- `/dev-git` — Git workflow (local operations, GPG commits)
- `/dev-github` — GitHub workflow (issues, PRs, project management)
- `/dev-agent-config` — MCP configuration (add/update MCP servers)

---

## Tier 3: Experts (Verification Phase)

Use AFTER coding — review, audit, find bugs, verify quality.

- `/expert-qa` — QA engineer (pytest unit/integration tests, Playwright E2E)
- `/expert-security` — Security engineer (API key proxy safety, no browser exposure)
- `/expert-architect` — Architect (RAG patterns, hybrid agent routing)
- `/expert-designer` — UI/UX designer (conversational UI, chat interface)
- `/expert-product` — Product manager (real estate use cases, query routing)
- `/expert-devops` — DevOps engineer (multi-platform deployment)
- `/expert-researcher` — Deep researcher (LLM provider comparison, RAG improvements)

---

## Tier 4: Utilities (Anytime)

- `/utility-license-check` — License checker (NO GPL/AGPL packages)

---

## Tier 5: Prompts (Rapid Actions)

- `/prompt-next` — Identify next task from TaskMaster
- `/prompt-commit` — Analyze and commit all pending changes
- `/prompt-review` — Pre-commit review checklist
- `/prompt-feature` — Feature implementation (TDD cycle)
- `/prompt-debug` — Root cause analysis
- `/prompt-docs` — Documentation sync
- `/prompt-test` — Generate tests
- `/prompt-status` — Project status report
- `/prompt-deps` — Dependency audit

---

## Quick Decision Tree

```
Planning something?  → /lead-tech     (or /lead-research for LLM provider investigation)
Building something?  → /dev-backend   (or /dev-frontend)
Reviewing something? → /expert-qa     (or /expert-security, /expert-architect)
Need a utility?      → /prompt-next   (find the next task to work on)
Don't know?          → /co-orchestrator
```
