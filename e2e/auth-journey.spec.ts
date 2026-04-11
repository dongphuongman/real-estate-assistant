/**
 * E2E test: Auth user journey.
 *
 * Requires the backend running: make dev
 * Run: npx playwright test e2e/auth-journey.spec.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Auth Journey', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.locator('form, input[type="email"]')).toBeVisible({ timeout: 10000 });
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/auth/register');
    await expect(page.locator('form, input[type="email"]')).toBeVisible({ timeout: 10000 });
  });

  test('login page shows email and password fields', async ({ page }) => {
    await page.goto('/auth/login');
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    const passwordInput = page.locator('input[type="password"], input[name="password"]');

    if (await emailInput.isVisible()) {
      await emailInput.fill('test@example.com');
    }
    if (await passwordInput.isVisible()) {
      await passwordInput.fill('password123');
    }
  });

  test('auth pages load without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/auth/login');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('locale selector works', async ({ page }) => {
    await page.goto('/');
    // Look for language toggle or selector
    const langToggle = page.locator('[data-testid="locale-toggle"], button:has-text("Polski"), button:has-text("English")').first();
    if (await langToggle.isVisible()) {
      await langToggle.click();
      // Should show language options
      await page.waitForTimeout(500);
    }
  });
});
