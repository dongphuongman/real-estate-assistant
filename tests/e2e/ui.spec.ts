import { test, expect } from '@playwright/test';
import { mkdir } from 'fs/promises';

const SCREENSHOT_DIR = process.env.PLAYWRIGHT_SCREENSHOT_DIR || 'artifacts/playwright/screenshots';

async function ensureScreenshotDir(): Promise<void> {
  await mkdir(SCREENSHOT_DIR, { recursive: true });
}

test.describe('UI Smoke', () => {
  test('home renders and navigation is available @smoke', async ({ page }) => {
    await ensureScreenshotDir();
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'AI Real Estate Assistant' })).toBeVisible({ timeout: 10000 });
    const nav = page.getByRole('navigation');
    await expect(nav.getByRole('link', { name: 'Search', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Assistant', exact: true })).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/home.png`, fullPage: true });
  });

  test('chat streams assistant response @smoke', async ({ page }) => {
    await ensureScreenshotDir();
    await page.route('**/api/v1/chat', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-User-Email',
            'Access-Control-Expose-Headers': 'X-Request-ID',
          },
          body: '',
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Expose-Headers': 'X-Request-ID',
          'X-Request-ID': 'req-stream-ok',
        },
        body: 'data: STREAM_OK\\n\\ndata: [DONE]\\n\\n',
      });
    });

    await page.goto('/chat');
    await expect(page.getByText(/Hello! I'm your AI Real Estate Assistant\./i)).toBeVisible({ timeout: 10000 });
    await page.getByPlaceholder('Ask about properties, market trends, or investment advice...').fill('Test message');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(page.getByText('STREAM_OK')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: `${SCREENSHOT_DIR}/chat_stream.png`, fullPage: true });
  });

  test('chat retry recovers after a failed stream @smoke', async ({ page }) => {
    await ensureScreenshotDir();
    let attempt = 0;
    await page.route('**/api/v1/chat', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-User-Email',
            'Access-Control-Expose-Headers': 'X-Request-ID',
          },
          body: '',
        });
        return;
      }
      attempt += 1;
      if (attempt === 1) {
        await route.fulfill({
          status: 500,
          headers: {
            'Content-Type': 'text/plain',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Expose-Headers': 'X-Request-ID',
            'X-Request-ID': 'req-stream-fail',
          },
          body: 'Simulated failure',
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Expose-Headers': 'X-Request-ID',
          'X-Request-ID': 'req-stream-retry-ok',
        },
        body: 'data: RECOVERED_OK\\n\\ndata: [DONE]\\n\\n',
      });
    });

    await page.goto('/chat');
    await page.getByPlaceholder('Ask about properties, market trends, or investment advice...').fill('Retry message');
    await page.getByRole('button', { name: /send message/i }).click();

    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('request_id=req-stream-fail', { exact: true })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: /retry/i }).click();
    await expect(page.getByText('RECOVERED_OK')).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /retry/i })).toHaveCount(0);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/chat_retry_recovered.png`, fullPage: true });
  });
});
