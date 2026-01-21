import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const outputDir = process.env.PLAYWRIGHT_OUTPUT_DIR || 'artifacts/playwright';
const startWeb =
  (process.env.PLAYWRIGHT_START_WEB || '').toLowerCase() === '1' ||
  (process.env.PLAYWRIGHT_START_WEB || '').toLowerCase() === 'true';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL,
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
  outputDir,
  webServer: startWeb
    ? {
        command: 'npm --prefix frontend run dev -- --port 3000',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      }
    : undefined,
  projects: [
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 5'],
      },
    },
    {
      name: 'tablet-chromium',
      use: {
        browserName: 'chromium',
        viewport: { width: 768, height: 1024 },
      },
    },
    {
      name: 'desktop-chromium',
      use: {
        browserName: 'chromium',
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
