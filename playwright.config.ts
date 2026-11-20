import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/functional/e2e',
  testMatch: '**/*.spec.ts',
  timeout: 90_000,
  workers: 1,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.TEST_BASE_URL ?? process.env.PLAYWRIGHT_BASE_URL ?? 'https://localhost:8080',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    ignoreHTTPSErrors: true,
  },
  reporter: [['list'], ['html', { outputFolder: 'tests/reports/playwright-html', open: 'never' }]],
  outputDir: 'tests/reports/playwright-results',
});
