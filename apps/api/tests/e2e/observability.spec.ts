import { test, expect } from '@playwright/test';
import { writeFile, mkdir } from 'fs/promises';

test('collect console and network metrics', async ({ page }) => {
  const logsDir = process.env.PLAYWRIGHT_LOG_DIR || 'artifacts/playwright/logs';
  await mkdir(logsDir, { recursive: true });
  const logs: Array<{ level: string; text: string; ts: number }> = [];
  const responses: Array<{ url: string; status: number; ok: boolean; ts: number }> = [];

  page.on('console', (msg) => {
    logs.push({ level: msg.type(), text: msg.text(), ts: Date.now() });
  });
  page.on('pageerror', (err) => {
    logs.push({ level: 'pageerror', text: String(err), ts: Date.now() });
  });

  page.on('response', async (res) => {
    responses.push({ url: res.url(), status: res.status(), ok: res.ok(), ts: Date.now() });
  });

  await page.goto('/');
  await page.waitForURL('**/');
  await expect(page.getByRole('heading', { name: 'AI Real Estate Assistant' })).toBeVisible({ timeout: 10000 });

  await page.goto('/search');
  await page.waitForURL('**/search');
  await expect(page.getByRole('heading', { name: 'Find Your Property' })).toBeVisible({ timeout: 10000 });

  await page.goto('/chat');
  await page.waitForURL('**/chat');
  await expect(page.getByRole('button', { name: /send message/i })).toBeVisible({ timeout: 10000 });

  const perf = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation');
    const res = performance.getEntriesByType('resource');
    return { navigation: nav, resources: res };
  });

  // keep raw logs and performance, omit derived summary for minimal footprint

  await writeFile(
    `${logsDir}/browser_console.json`,
    JSON.stringify({ logs }, null, 2)
  );
  await writeFile(
    `${logsDir}/browser_network.json`,
    JSON.stringify({ responses }, null, 2)
  );
  await writeFile(
    `${logsDir}/browser_performance.json`,
    JSON.stringify(perf, null, 2)
  );
});
