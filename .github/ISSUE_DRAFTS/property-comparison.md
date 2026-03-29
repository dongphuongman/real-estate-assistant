---
title: "Community: Add Property Comparison Tool"
labels: good first issue, help wanted
---

## Overview

Build a side-by-side property comparison UI that lets users select 2-4 properties and compare their features, prices, and locations visually.

## Skills Required

- [ ] Python (async, FastAPI)
- [x] TypeScript/React
- [x] Frontend UI work
- [x] shadcn/ui components

## Architecture Context

This is primarily a frontend feature using the existing property data. The comparison should:

1. Use a new route: `/compare?ids=1,2,3`
2. Fetch property details via existing API
3. Display in a responsive grid with feature rows

Reference files:
- API client: `apps/web/src/lib/api.ts`
- Property types: `apps/web/src/lib/types.ts`
- shadcn components: `apps/web/src/components/ui/`

## Acceptance Criteria

- [ ] New route `/compare` with query parameter for property IDs
- [ ] Responsive grid layout (2-4 columns)
- [ ] Feature comparison rows: price, rooms, area, location, features
- [ ] Highlight best value per feature
- [ ] Works on mobile (stacks vertically)
- [ ] Add comparison button on search result cards
- [ ] Empty state when no properties selected

## Getting Started

1. Fork and clone the repository
2. Review existing UI components and API client
3. Create branch: `git checkout -b feature/property-comparison`
4. Implement, test, and open a PR against `dev`

## Questions?

Comment on this issue and a maintainer will help you get started.
