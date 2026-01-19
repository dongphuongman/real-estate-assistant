# Contributing to AI Real Estate Assistant

Thank you for your interest in contributing to the AI Real Estate Assistant! This document provides guidelines and standards for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## 🤝 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other contributors

## 🚀 Getting Started

### Prerequisites

- Python 3.12 or higher
- Node.js 18+ and npm
- Git
- API keys for at least one LLM provider (OpenAI, Anthropic, etc.)

### Initial Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-real-estate-assistant.git
   cd ai-real-estate-assistant
   ```

2. **Backend Setup (FastAPI)**
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\Activate.ps1
   # Linux/Mac:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Frontend Setup (Next.js)**
   ```bash
   cd frontend
   npm install
   ```

4. **Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 💻 Development Setup

### Project Structure

```
ai-real-estate-assistant/
├── agents/              # AI agents (Hybrid, Tools)
├── analytics/           # Market insights & Valuation
├── api/                 # FastAPI routers & endpoints
├── data/                # Data providers (CSV, API)
├── docs/                # Documentation
├── frontend/            # Next.js Application
├── models/              # LLM Provider Factory
├── notifications/       # Digest & Alert System
├── tests/               # Pytest suite
└── vector_store/        # ChromaDB integration
```

### Running Locally

1. **Backend**
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm run dev
   # Runs on http://localhost:3000
   ```

## 📝 Code Standards

### Python (Backend)
- **Style**: Follow PEP 8.
- **Linting**: We use `ruff` for linting and formatting.
  ```bash
  ruff check .
  ruff format .
  ```
- **Type Hints**: Mandatory for all function signatures.
- **Docstrings**: Google style.

### TypeScript/React (Frontend)
- **Style**: Prettier + ESLint.
- **Components**: Functional components with hooks.
- **UI**: Use Shadcn UI components from `src/components/ui`.

## 🧪 Testing Guidelines

### Backend (Pytest)
```bash
# Run all tests
python -m pytest

# Run specific category
python -m pytest tests/unit
python -m pytest tests/integration
```

### Frontend (Jest)
```bash
cd frontend
npm test
```

## 🔄 Pull Request Process

### Commit Message Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

### Pull Request Template
- **Description**: What changed?
- **Type**: Bug fix / Feature / Docs.
- **Testing**: How was it verified?

## 📚 Documentation
- Keep `README.md` concise.
- Place detailed docs in `docs/`.
- Update `docs/API_REFERENCE.md` for API changes.
