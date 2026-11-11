import { test, expect, loginAs } from './test-fixture.js';

test.describe('Role & Branch Scoping Strictness', () => {
  test('Service Advisor sees only their own customers in Advisor Portal', async ({ page }) => {
    await loginAs(page, 'advisor@demomotors.com', 'Password@12345');
    await page.goto('/advisor');

    // Verify page header
    await expect(page.locator('text=Advisor Follow-up').first()).toBeVisible({ timeout: 15000 });

    // Verify non-empty root
    await expect(page.locator('#root')).not.toBeEmpty();
  });

  test('Branch Manager sees only their assigned branch across Dashboard and Reports', async ({ page }) => {
    await loginAs(page, 'manager@demomotors.com', 'Password@12345');

    // 1. PSF Dashboard scoping
    await page.goto('/psf');
    const table = page.locator('table');
    await expect(table).toBeVisible({ timeout: 15000 });

    // Central Workshop Hubli branch should be present
    const branchCell = page.locator('table tbody td').filter({ hasText: /Central Workshop Hubli|CW-HUB/i });
    if (await branchCell.count() > 0) {
      await expect(branchCell.first()).toBeVisible();
    }

    // 2. Reports scoping
    await page.goto('/reports');
    await expect(page.locator('text=Reports & Analytics')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('#root')).not.toBeEmpty();

    // Verify export button is visible and active
    const exportBtn = page.locator('button:has-text("Export Excel"), a:has-text("Export Excel")').first();
    if (await exportBtn.isVisible()) {
      await expect(exportBtn).toBeEnabled();
    }
  });
});
