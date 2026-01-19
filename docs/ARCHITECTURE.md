# Architecture (V4)

## System Overview
The AI Real Estate Assistant is a modern, conversational AI platform helping users find properties through natural language. It features a split architecture with a Next.js frontend and a FastAPI backend.

### Core Components
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, Shadcn UI.
- **Backend**: FastAPI (Python 3.12+), Pydantic, SSE streaming.
- **AI Engine**: Hybrid Agent (RAG + Tools), Query Analyzer, Strategic Reranker.
- **Data**: ChromaDB (Vector Store), Pandas (Analytics), SQLite/JSON (Persistence).

## Detailed Component Design

### 1. Frontend Architecture (Next.js)
- **Framework**: Next.js 14 (App Router).
- **Styling**: Tailwind CSS + Shadcn UI.
- **State Management**: React Hooks + LocalStorage for preferences.
- **Directory Structure**:
    - `src/app`: Pages and layouts (App Router).
    - `src/components/ui`: Atomic UI components (Button, Input, Card).
    - `src/components/layout`: Global layout components (MainNav).
    - `src/lib`: Utility functions, API clients (`api.ts`), and types.

#### Key Features
- **Theming**: Dark/light mode via `next-themes` or manual CSS class toggling.
- **Streaming**: Consumes Server-Sent Events (SSE) from `/api/v1/chat` for real-time AI responses.
- **Auth**: Email-based OTP login flow (`/api/v1/auth`).

### 2. Backend Architecture (FastAPI)
- **API Router**: Modular routers in `api/routers/` (chat, search, admin, settings).
- **Dependencies**: Dependency injection for LLMs, Vector Store, and Services via `api/dependencies.py`.
- **Observability**: Request ID tracking, structured logging, rate limiting.

#### Key Data Flows
- **Ingestion**: CSV/API -> Pandas -> Cleaning -> Embeddings -> ChromaDB.
- **Search**: Query -> Analyzer -> Hybrid Retrieval (Semantic + Keyword) -> Reranking -> Response.
- **Chat**: User Message -> Hybrid Agent -> Tool Selection (Calculator, Search, etc.) -> LLM Response.

### 3. Notification System
The digest system bridges raw property data and user notifications.

- **DigestGenerator (`notifications/digest_generator.py`)**:
    - Gathers data for email digests from `VectorStore` (new matches) and `MarketInsights`.
    - Iterates through `SavedSearch` objects to find relevant updates.
- **AlertManager (`notifications/alert_manager.py`)**:
    - Orchestrates digest generation based on schedules.
- **EmailService**:
    - Renders responsive HTML templates (`DigestTemplate`) and sends via SMTP/SendGrid.

### 4. Data Providers
- **BaseDataProvider**: Abstract interface for data fetching.
- **Implementations**:
    - `CsvProvider`: Loads local/remote CSVs.
    - `ApiProvider`: Fetches from external REST APIs.
    - `JsonProvider`: Loads JSON datasets.

## Technology Stack
- **Web**: Next.js 16 (App Router), TypeScript, Tailwind CSS v4
- **Backend**: FastAPI (Python 3.12), Pydantic 2.5+, SSE streaming
- **Vector Store**: ChromaDB 0.5+
- **Embeddings**: FastEmbed (BGE) or OpenAI embeddings
- **Testing**: Pytest (Backend), Jest (Frontend)
- **Deployment**: Docker, Vercel (Frontend), Render/Railway (Backend)

## API Surface
- **Search**: `/api/v1/search`
- **Chat**: `/api/v1/chat` (SSE supported)
- **Tools**: `/api/v1/tools/*` (mortgage, compare, price analysis)
- **Settings**: `/api/v1/settings/notifications`, `/api/v1/settings/models`
- **Auth**: `/api/v1/auth/*`
- **Admin**: `/api/v1/admin/*` (ingest, reindex)
