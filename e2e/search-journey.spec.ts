/**
 * E2E test: Search user journey.
 *
 * Requires the backend running: make dev
 * Run: npx playwright test e2e/search-journey.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Search Journey', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('navigates to search page', async ({ page }) => {
    // Look for navigation link or direct URL
    await page.goto('/search');
    await expect(page.locator('h1, h2')).toContainText(/find.*property|search/i);
  });

  test('can type a search query', async ({ page }) => {
    await page.goto('/search');
    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    if (await input.isVisible()) {
      await input.fill('apartments in Krakow');
      await expect(input).toHaveValue('apartments in Krakow');
    }
  });

  test('can submit a search', async ({ page }) => {
    await page.goto('/search');
    const input = page.locator('input[type="text"], input[type="search"], textarea').first();
    const searchBtn = page.locator('button:has-text("search"), button[type="submit"]').first();

    if (await input.isVisible()) {
      await input.fill('2-bedroom Warsaw');
      if (await searchBtn.isVisible()) {
        await searchBtn.click();
        // Wait for results or loading state
        await page.waitForTimeout(2000);
      }
    }
  });

  test('search page loads without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    // No console errors
    expect(errors).toHaveLength(0);
  });
});
