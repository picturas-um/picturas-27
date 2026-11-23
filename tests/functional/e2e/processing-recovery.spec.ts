import { test, expect } from '@playwright/test';
import { preparePage, signedIn } from './support';
const { account, project, fixture, success } = require('../helpers/live');

test.beforeEach(async ({ page }) => preparePage(page));

// Mock only the run-status/cancel transport, keeping the actual React page and
// project/session loading. The same server response survives page.reload().
test('[UI-04.2] refresh recovers progress and cancellation; a failed cancel keeps the controls', async ({ page }) => {
  const a = await account(), p = await project(a);
  success(await p.upload(fixture('pattern.png')));
  await signedIn(page, a);
  let status = 'processing', rejectCancel = true;
  await page.route('**/api-gateway/projects/**/process/status**', route => route.fulfill({
    json: { status, token: 7, progress: 42, projectVersion: 12, canCancel: status === 'processing' },
  }));
  await page.route('**/api-gateway/projects/**/process', async route => {
    if (route.request().method() !== 'DELETE') return route.continue();
    expect(route.request().headers()['x-process-token']).toBe('7');
    expect(route.request().headers()['x-project-version']).toBe('12');
    if (rejectCancel) return route.fulfill({ status: 503, json: 'Temporarily unavailable' });
    status = 'cancelled';
    return route.fulfill({ status: 204, headers: { 'X-Project-Version': '13' } });
  });
  await page.goto(`/dashboard/${p.id}`);
  await expect(page.getByText('42%', { exact: true })).toBeVisible();
  // Recovery and cancellation must not depend on downloading old results.
  await page.route('**/api-gateway/projects/**/process/url**', route =>
    route.fulfill({ status: 503, json: 'Results temporarily unavailable' }));
  await page.reload();
  await expect(page.getByText('42%', { exact: true })).toBeVisible();
  const cancel = page.getByRole('button', { name: 'Cancelar', exact: true });
  await expect(cancel).toBeEnabled();
  await cancel.click();
  await expect(cancel).toBeEnabled();
  await expect(page.getByText('42%', { exact: true })).toBeVisible();
  rejectCancel = false;
  await cancel.click();
  await expect(page.getByRole('heading', { name: 'Processing', exact: true })).toBeHidden();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Processing', exact: true })).toBeHidden();
});

test('[UI-04.2] completed or failed jobs after reload are not shown as still processing', async ({ page }) => {
  const a = await account(), p = await project(a);
  await signedIn(page, a);
  let status = 'completed';
  await page.route('**/api-gateway/projects/**/process/status**', route => route.fulfill({
    json: { status, token: 8, progress: status === 'completed' ? 100 : 30,
      projectVersion: 13, canCancel: false, error: status === 'failed' ? 'Storage unavailable' : null },
  }));
  await page.goto(`/dashboard/${p.id}`);
  await expect(page.getByRole('button', { name: 'Apply', exact: true })).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'Processing', exact: true })).toBeHidden();
  status = 'failed';
  await page.reload();
  await expect(page.getByText('Storage unavailable', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancelar', exact: true })).toBeHidden();
});
