import { test, expect } from '@playwright/test';
import path from 'node:path';
import { preparePage, signedIn } from './support';
const { account, project, fixtures, fixture, success } = require('../../helpers/live');

test.beforeEach(async ({ page }) => preparePage(page));

test('[PROJ-01,UP-01,UI-01] create project with an image through the browser and reload', async ({ page }) => {
  const a = await account(); await signedIn(page, a);
  await page.getByRole('button', { name: /new project/i }).click();
  await page.getByLabel('Project Name').fill('Browser regression project');
  await page.getByRole('dialog').locator('input[type=file]').setInputFiles(fixture('pattern.png'));
  await page.getByRole('button', { name: 'Create', exact: true }).click();
  await expect(page).toHaveURL(/dashboard\/[a-f0-9]{24}/);
  await expect(page.getByRole('img', { name: 'pattern.png', exact: true }).first()).toBeVisible();
  const url = page.url(); await page.reload();
  await expect(page).toHaveURL(url); await expect(page.getByRole('img', { name: 'pattern.png', exact: true }).first()).toBeVisible();
});

test('[SHARE-03] read-only shared project disables editing controls', async ({ page }) => {
  const owner = await account(), guest = await account(), p = await project(owner);
  success(await p.upload(fixture('pattern.png')));
  const share = success(await p.mutate('POST', '/share', { permission: 'read' }));
  await signedIn(page, guest);
  await page.goto(`/dashboard/${p.id}?owner=${owner.id}&share=${share.id}`);
  await expect(page.getByRole('img', { name: 'pattern.png', exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Carousel view' }).click();
  await expect(page).toHaveURL(new RegExp(`share=${share.id}`));
  const apply = page.getByRole('button', { name: 'Apply', exact: true });
  if (await apply.count()) await expect(apply).toBeDisabled();
  const tool = page.getByRole('button', { name: 'Resize', exact: true });
  if (await tool.count()) await expect(tool).toBeDisabled();
});
