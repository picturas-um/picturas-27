import { test, expect } from '@playwright/test';
import path from 'node:path';
import { preparePage, signedIn } from './support';
const { account, project, fixtures, fixture, success } = require('../../helpers/live');

test.beforeEach(async ({ page }) => preparePage(page));

test('[PIPE-02,UI-01] video project hides image-only tools and PDF export', async ({ page }) => {
  const a = await account(), p = await project(a); success(await p.upload(fixture('clip.mp4'), 'video'));
  await signedIn(page, a); await page.goto(`/dashboard/${p.id}`);
  await expect(page.locator('video').first()).toBeVisible();
  await page.getByRole('button', { name: 'Carousel view' }).click();
  await expect(page.getByRole('button', { name: 'Watermark', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Background Removal/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Download project' }).click();
  await expect(page.getByRole('menuitem', { name: /PDF/ })).toHaveCount(0);
  expect(await page.locator('video').first().evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
});
