import { test, expect, firefox } from '@playwright/test';
import fs from 'node:fs';
import { preparePage } from './support';
const { account, project, registry, base } = require('../../helpers/live');

test.beforeEach(async ({ page }) => preparePage(page));

test('[AUTH-01,AUTH-03.2] browser login and logout replace the private session', async ({ page }) => {
  const a = await account();
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill(a.email);
  await page.getByLabel('Password', { exact: true }).fill(a.password);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.getByRole('button', { name: new RegExp(a.email) }).click();
  await page.getByRole('menuitem', { name: 'Logout' }).click();
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('session') || '{}').user?.type)).toBe('anonymous');
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('session') || '{}').token)).not.toBe(a.token);
});

test('[AUTH-01] browser registration establishes a free session', async ({ page }) => {
  const email = `regression-browser-${Date.now()}@example.invalid`;
  await page.goto('/register');
  await page.locator('#first-name').fill('Regression');
  await page.locator('#last-name').fill('Browser');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill('Test-browser-12345');
  await page.locator('#confirm-password').fill('Test-browser-12345');
  await page.getByRole('button', { name: /create|register|sign up/i }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('session') || '{}').user?.email)).toBe(email);
});

test('[UI-03] Firefox can log in and display a saved project', async () => {
  const a = await account(), p = await project(a), browser = await firefox.launch();
  try {
    const page = await browser.newPage({ ignoreHTTPSErrors: true, baseURL: base });
    page.on('response', async response => {
      if (response.request().method() === 'POST' && /\/api-gateway\/users\/?$/.test(response.url()) && response.status() === 201) {
        const value = await response.json();
        fs.appendFileSync(registry, JSON.stringify({ id: value.user._id, createdAt: new Date().toISOString() }) + '\n');
      }
    });
    await page.goto('/login');
    await page.getByLabel('Email', { exact: true }).fill(a.email);
    await page.getByLabel('Password', { exact: true }).fill(a.password);
    await page.getByRole('button', { name: 'Login', exact: true }).click();
    await expect(page).toHaveURL(/dashboard/);
    await page.goto(`/dashboard/${p.id}`); await expect(page.getByText('Regression project').first()).toBeVisible();
  } finally { await browser.close(); }
});
