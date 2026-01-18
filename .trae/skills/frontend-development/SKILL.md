name: frontend-development
description: Standards and workflows for Frontend (Next.js/React) development.
---

# Frontend Development
Follow these standards for frontend code in `frontend/`.

## Stack
- **Framework**: Next.js 16 (App Router).
- **Library**: React 19.
- **Styling**: Tailwind CSS v4, `clsx`, `tailwind-merge`.
- **UI Components**: Radix UI primitives, Lucide React icons.
- **Language**: TypeScript.

## Code Style
- **Components**: Functional components with named exports.
- **Naming**: `PascalCase` for components, `kebab-case` for files (e.g., `user-profile.tsx`).
- **Props**: Use interfaces for Prop types.
- **Hooks**: Custom hooks in `hooks/` directory, start with `use`.

## Directory Structure
- `src/app/`: App Router pages and layouts.
- `src/components/`: Reusable UI components.
  - `ui/`: Base UI components (Button, Input, etc.).
- `src/lib/`: Utility functions and shared logic.

## State Management
- Use React Server Components (RSC) for data fetching where possible.
- Use Client Components (`'use client'`) only when interactivity is needed.

## Testing
- **Unit**: Jest + React Testing Library.
- **Command**: `npm test` or `npm run test:watch`.
