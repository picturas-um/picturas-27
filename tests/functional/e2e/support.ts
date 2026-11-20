import { expect, type Page } from '@playwright/test';
import fs from 'node:fs';
const { registry } = require('../../helpers/live');

export async function preparePage(page: Page) {
  await page.route('https://picsum.photos/**', route => route.abort());
  page.on('response', async response => {
    if (response.request().method() === 'POST' && /\/api-gateway\/users\/?$/.test(response.url()) && response.status() === 201) {
      try {
        const value = await response.json();
        fs.appendFileSync(registry, JSON.stringify({ id: value.user._id, email: value.user.email, createdAt: new Date().toISOString() }) + '\n');
      } catch {}
    }
  });
}

export async function signedIn(page: Page, user: any) {
  await page.goto('/login');
  await page.evaluate(value => localStorage.setItem('session', JSON.stringify(value)), { user: user.user, token: user.token });
  await page.goto('/dashboard');
  await expect(page.getByText(user.email).first()).toBeVisible();
}
