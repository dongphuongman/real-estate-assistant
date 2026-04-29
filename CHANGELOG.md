# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - 2026-02-08

### Added
- Next.js App Router frontend with React 19 and Tailwind CSS v4
- Hybrid AI agent with intelligent query routing (simple → RAG, complex → Agent+Tools)
- Multi-provider LLM support: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama
- Persistent ChromaDB vector store with semantic + keyword hybrid search
- Result reranking with 30-40% relevance improvement
- Streaming chat responses with real-time property cards
- Interactive property map with Mapbox/Leaflet clustering
- Comparative Market Analysis (CMA) tool
- Market trends analytics with area comparison and caching
- Investment report generation with ROI analysis
- Mortgage calculator, rent-vs-buy, and TCO comparison tools
- User authentication with dual-mode: API Key + JWT
- User profile management with model preferences per task type
- Saved searches and favorites with property comparison
- Document management system
- Agent directory with contact forms and viewing scheduling
- City overview with comparison metrics
- 9-language i18n support (EN, PL, RU, DE, ES, IT, PT, TR, UK)
- EU AI Act compliance labels and X-AI-Generated headers
- PWA support with service worker and offline caching
- WCAG 2.1 AA accessibility foundations
- Open Graph meta tags, sitemap, robots.txt, and JSON-LD for SEO
- Prometheus metrics with Grafana dashboard and alerting rules
- Sentry SDK integration for error tracking and APM
- Circuit breaker pattern for graceful degradation
- IP-based sliding window rate limiter middleware
- DB-backed tamper-evident audit logging
- Redis response caching for search/RAG endpoints
- Admin dashboard with data sources, bulk jobs, and connectors
- System health metrics widget with K8s-ready endpoints
- MCP (Model Context Protocol) Registry API with web scraper connector
- Property enrichment hooks system
- Comprehensive CI/CD pipeline with GitHub Actions
- Pre-commit hooks: Gitleaks + Semgrep + lint-staged (3-layer security)
- Lighthouse CI enforcing >=90 scores on search and chat
- Docker production hardening with non-root user and resource limits
- Dynamic port allocation for multi-agent development
- SPRAV systematic pre-release acceptance validation framework
- Community contribution guidelines, PR templates, security policy
- 5-minute quickstart guide with verification scripts
- Full test suite: 3000+ backend tests, 1000+ frontend tests

### Changed
- Migrated from Streamlit (v3) to Next.js App Router
- Replaced simple chat with hybrid agent routing
- Upgraded to React 19 with Tailwind CSS v4
- PostgreSQL support for production deployment
- Async SQLite (aiosqlite) for local development
- Structured logging with observability standards

### Security
- OWASP remediation: SSRF protection, JWT secret hardening, token logging, sort_by whitelist
- CORS hardening with secure defaults
- Removed dangerouslySetInnerHTML usage
- Docker credentials secured
- Versioned API contract enforcement
- npm vulnerability monitoring
- CodeQL workflow for Python and JavaScript analysis
- Trivy container vulnerability scanning

## [3.0.0] - 2026-01-11

### Added
- Streamlit-based frontend with multi-page layout
- ChromaDB vector store integration
- LangChain-based agent with tool support
- Property search with filter extraction
- Basic analytics and mortgage calculator
- PDF export for property reports
- Polish property listings dataset (60 properties)

### Changed
- Migrated from Flask API (v2) to FastAPI backend
- Added async endpoints with WebSocket support
- Improved query analysis and intent classification

## [2.0.0] - 2025-05-15

### Added
- Flask REST API backend
- Property database with CRUD operations
- Basic NLP query processing
- Price analysis and comparison tools
- Enhanced PRD with functional requirements and roadmap

### Changed
- Migrated from CLI prototype (v1) to web API
- Added structured data models and validation

## [1.0.0] - 2025-12-31

### Added
- Initial CLI-based real estate assistant
- OpenAI GPT integration for property recommendations
- Basic property search and filtering
- Command-line interface for queries
- SQLite database for property listings

[4.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v4.0.0
[3.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v3.0.0
[2.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v2.0.0
[1.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v1.0.0
