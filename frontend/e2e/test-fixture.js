import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    const consoleErrors = [];
    const pageErrors = [];
    const networkFailures = [];

    // Allow tests to opt-out of network failure check for intentional negative calls
    page.__allow4xx = false;

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore favicon 404 or expected dev server hot reload disconnects
        if (!text.includes('favicon.ico') && !text.includes('ERR_CONNECTION_REFUSED')) {
          consoleErrors.push(text);
        }
      }
    });

    page.on('pageerror', (err) => {
      pageErrors.push(err.message || String(err));
    });

    page.on('response', (resp) => {
      const status = resp.status();
      const url = resp.url();
      if (!page.__allow4xx && status >= 400) {
        if (!url.includes('favicon.ico')) {
          networkFailures.push(`[HTTP ${status}] ${url}`);
        }
      }
    });

    await use(page);

    // Fail if screen is completely blank
    const root = page.locator('#root');
    const isRootVisible = await root.isVisible().catch(() => false);
    if (isRootVisible) {
      const rootText = (await root.innerText().catch(() => '')).trim();
      if (rootText.length === 0 && (await root.locator('*').count()) === 0) {
        throw new Error('Blank screen detected: #root container is empty.');
      }
    }

    if (pageErrors.length > 0) {
      throw new Error(`Uncaught page exceptions detected:\n${pageErrors.join('\n')}`);
    }
    if (consoleErrors.length > 0) {
      throw new Error(`Console errors detected:\n${consoleErrors.join('\n')}`);
    }
    if (networkFailures.length > 0) {
      throw new Error(`Unexpected network failure (4xx/5xx) detected:\n${networkFailures.join('\n')}`);
    }
  },
});

export { expect };

export async function loginAs(page, email, password) {
  await page.goto('/login');

  // Fill credentials
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();

  // Wait for navigation away from /login
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
}
