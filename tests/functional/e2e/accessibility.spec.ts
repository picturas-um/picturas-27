import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { preparePage, signedIn } from './support';
const { account } = require('../../helpers/live');

test.beforeEach(async ({ page }) => preparePage(page));

test('[UI-02] registration controls have labels and page has no serious accessibility violations', async ({ page }) => {
  await page.goto('/register');
  await expect(page.getByLabel('Last Name', { exact: true })).toBeVisible();
  const result = await new AxeBuilder({ page }).analyze();
  expect(result.violations.filter(x => ['serious', 'critical'].includes(x.impact || ''))).toEqual([]);
});

test('[UI-02] project dialog supports keyboard dismissal and restores focus', async ({ page }) => {
  const a = await account(); await signedIn(page, a);
  const trigger = page.getByRole('button', { name: /new project/i });
  await trigger.focus(); await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test('[UI-03] mobile login is usable without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/login');
  await expect(page.getByLabel('Email', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Login', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
