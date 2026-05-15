# Community Contribution Issues

Prepared GitHub Issues for community onboarding. These are designed as `good first issue` targets
for external contributors. Copy the issue text below into GitHub Issues when ready to publish.

---

## Issue 1: Add CSV Export for Property Search Results

**Title:** `[Community] Add CSV export for property search results`

**Labels:** `good first issue`, `enhancement`, `frontend`

**Body:**

### Summary

Add a "Export CSV" button to the property search results page that downloads the current results as a `.csv` file.

### Requirements

- Add an export button to the search results component (`apps/web/src/components/search/`)
- Export visible columns: title, price, location, bedrooms, area, url
- Use the browser's download API (no server roundtrip needed)
- Include a unit test for the CSV formatting function

### Files to modify

- `apps/web/src/components/search/SearchResults.tsx` (or similar)
- New utility: `apps/web/src/lib/export-csv.ts`
- New test: `apps/web/src/lib/__tests__/export-csv.test.ts`

### Acceptance Criteria

- [ ] "Export CSV" button appears in search results header
- [ ] Clicking downloads a valid CSV file with correct headers
- [ ] Empty results show a disabled button
- [ ] Unit test covers edge cases (empty fields, special characters)

---

## Issue 2: Add Property Comparison Side-by-Side View

**Title:** `[Community] Add property comparison side-by-side view`

**Labels:** `good first issue`, `enhancement`, `frontend`

**Body:**

### Summary

Allow users to select 2-3 properties from search results and view them in a side-by-side comparison table.

### Requirements

- Add checkboxes to search result cards for selection (max 3)
- Create a comparison modal/page with a feature-by-feature table
- Compare: price, area, bedrooms, bathrooms, location, price/sqm
- Responsive layout (stacks on mobile)

### Files to modify

- New component: `apps/web/src/components/property/PropertyComparison.tsx`
- `apps/web/src/components/search/SearchResults.tsx` (add selection)
- `apps/web/src/contexts/` (optional: comparison state context)

### Acceptance Criteria

- [ ] User can select up to 3 properties via checkboxes
- [ ] "Compare" button appears when 2+ selected
- [ ] Comparison table shows all key attributes side-by-side
- [ ] Works on mobile (stacked layout)

---

## Issue 3: Add Dark Mode Toggle

**Title:** `[Community] Add dark mode toggle to the UI`

**Labels:** `good first issue`, `enhancement`, `frontend`

**Body:**

### Summary

Add a dark/light mode toggle to the navigation bar using CSS custom properties or Tailwind's dark mode.

### Requirements

- Add a toggle button (sun/moon icon) to the navbar
- Store preference in `localStorage`
- Respect system preference on first visit (`prefers-color-scheme`)
- Use Tailwind `dark:` classes for styling

### Files to modify

- `apps/web/src/components/layout/Navbar.tsx` (add toggle)
- `apps/web/src/app/layout.tsx` (add dark class to `<html>`)
- New hook: `apps/web/src/hooks/useTheme.ts`
- `tailwind.config.ts` (ensure `darkMode: 'class'`)

### Acceptance Criteria

- [ ] Toggle switches between light and dark themes
- [ ] Preference persists across page reloads
- [ ] System preference is respected on first visit
- [ ] All major components render correctly in dark mode

---

## Issue 4: Add Email Notification MCP Connector

**Title:** `[Community] Add email notification MCP connector`

**Labels:** `good first issue`, `enhancement`, `backend`

**Body:**

### Summary

Implement an MCP connector for sending email notifications via SMTP, following the existing connector pattern.

### Requirements

- Extend `MCPConnector` from `apps/api/mcp/base.py`
- Implement: `connect()`, `disconnect()`, `health_check()`, `execute()`
- Support basic SMTP (via `aiosmtplib` or similar)
- Register in `apps/api/mcp/registry.py`
- Add to community edition allowlist in `apps/api/config/mcp_allowlist.yaml`

### Files to modify

- New: `apps/api/mcp/connectors/email_smtp.py`
- `apps/api/mcp/registry.py`
- `apps/api/config/mcp_allowlist.yaml`
- New test: `apps/api/tests/unit/mcp/test_email_smtp.py`

### Reference Implementation

See `apps/api/mcp/connectors/web_scraper.py` for the pattern.

### Acceptance Criteria

- [ ] Connector follows `MCPConnector` interface
- [ ] `health_check()` verifies SMTP connectivity
- [ ] `execute()` sends an email with configurable to/subject/body
- [ ] Unit tests with mocked SMTP
- [ ] Listed under `community_edition` in allowlist

---

## Issue 5: Add iCal Export for Saved Property Searches

**Title:** `[Community] Add iCal export for saved search schedules`

**Labels:** `good first issue`, `enhancement`, `full-stack`

**Body:**

### Summary

Allow users to export saved search schedules as iCal `.ics` files for calendar integration.

### Requirements

- Backend endpoint: `GET /api/v1/saved-searches/{id}/export/ics`
- Generate valid iCal format (RFC 5545)
- Frontend: "Add to Calendar" button on saved searches
- Support Google Calendar, Apple Calendar, Outlook

### Files to modify

- New: `apps/api/api/routers/saved_searches.py` (add export endpoint)
- New: `apps/api/services/ical_service.py`
- `apps/web/src/components/saved-searches/SavedSearchCard.tsx` (add button)

### Acceptance Criteria

- [ ] `.ics` file downloads and imports into Google Calendar
- [ ] Event contains property details (address, price, link)
- [ ] Frontend button triggers download
- [ ] Handles missing saved search with 404

---

## Issue 6: Improve Mobile Responsiveness for Property Cards

**Title:** `[Community] Improve mobile responsiveness for property cards`

**Labels:** `good first issue`, `bug`, `frontend`

**Body:**

### Summary

Property cards in the search results grid overflow on viewports below 375px. Fix the layout and add touch-friendly interactions.

### Requirements

- Fix card overflow on 320-375px viewports
- Add swipe gesture for image carousel on cards
- Ensure tap targets are at least 44x44px
- Test on iOS Safari and Android Chrome

### Files to modify

- `apps/web/src/components/property/PropertyCard.tsx`
- `apps/web/src/components/ui/ImageCarousel.tsx` (if exists)

### Acceptance Criteria

- [ ] No horizontal scroll on 320px viewport
- [ ] Image swipe works on touch devices
- [ ] All buttons meet 44x44px minimum tap target
- [ ] Screenshots attached showing before/after

---

## Publishing Checklist

Before publishing these issues on GitHub:

1. Verify each issue references correct file paths (check current codebase)
2. Add `good first issue` and area labels to the repo
3. Assign a maintainer for initial response
4. Cross-link from CONTRIBUTING.md "Good First Issues" section
5. Pin 2-3 issues to the top of the issue list for visibility
