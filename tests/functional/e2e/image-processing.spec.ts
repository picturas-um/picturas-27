import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { preparePage, signedIn } from './support';
const { account, project, fixtures, fixture, success, request } = require('../../helpers/live');

test.beforeEach(async ({ page }) => preparePage(page));

test('[PIPE-01,IMG-01,OUT-01,UI-01] edit resize apply and download actual browser results', async ({ page }) => {
  const a = await account(), p = await project(a);
  success(await p.upload(fixture('pattern.png')));
  await signedIn(page, a); await page.goto(`/dashboard/${p.id}`);
  await page.getByRole('button', { name: 'Carousel view' }).click();
  await page.getByRole('button', { name: 'Resize', exact: true }).click();
  await page.getByLabel('Width', { exact: true }).fill('80');
  await page.getByLabel('Height', { exact: true }).fill('60');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  await expect.poll(async () => success(await request('GET', p.route + '/process/url', { token: a.token })).imgs.length, { timeout: 60000 }).toBe(1);
  await page.getByRole('button', { name: 'Results mode' }).click();
  await expect(page.getByText('No results found.', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: 'Download project' }).click();
  const downloaded = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: /Download results \(ZIP\)/ }).click();
  const download = await downloaded;
  expect(await download.failure()).toBeNull(); expect(download.suggestedFilename()).toMatch(/\.zip$/);
});

test('[OUT-02] image project exports a readable PDF', async ({ page }) => {
  const a = await account(), p = await project(a); success(await p.upload(fixture('pattern.png')));
  await signedIn(page, a); await page.goto(`/dashboard/${p.id}`);
  await page.getByRole('button', { name: 'Download project' }).click();
  const pending = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: /Download images \(PDF\)/ }).click();
  const download = await pending, file = await download.path();
  expect(file).toBeTruthy(); expect(fs.readFileSync(file!).subarray(0, 5).toString()).toBe('%PDF-');
});
