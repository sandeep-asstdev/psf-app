import { test, expect, loginAs } from './test-fixture.js';

test.describe('CRE Calling Workflow & Survey Execution', () => {
  test('CRE opens PSF dashboard and sees correct column order and rows', async ({ page }) => {
    await loginAs(page, 'cre1@demomotors.com', 'Password@12345');
    await page.goto('/psf');
    await page.waitForLoadState('networkidle');

    // 1. Column order validation: Customer Name, Reg No, Job Card No, Service Advisor
    const ths = page.locator('table thead th');
    await expect(ths.nth(0)).toContainText(/Customer Name/i);
    await expect(ths.nth(1)).toContainText(/Reg No/i);
    await expect(ths.nth(2)).toContainText(/Job Card/i);
    await expect(ths.nth(3)).toContainText(/Service Advisor/i);

    // 2. Rows should be visible
    const rows = page.locator('table tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10000 });
  });

  test('CRE opens a call modal, fills survey, and uses Save & Next', async ({ page }) => {
    await loginAs(page, 'cre1@demomotors.com', 'Password@12345');
    await page.goto('/psf');
    await page.waitForLoadState('networkidle');

    // Open first row's call console
    const firstRow = page.locator('table tbody tr').first();
    await firstRow.click();

    // Call console modal should appear
    const modal = page.locator('div:has-text("PSF Console")').first();
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify timer is running (non-empty duration)
    const timer = page.locator('span.font-mono').first();
    await expect(timer).toBeVisible();

    // Fill VOC notes
    const vocInput = page.locator('textarea').first();
    if (await vocInput.isVisible()) {
      await vocInput.fill('Customer confirmed vehicle is in great condition, no concerns.');
    }

    // Click "Save & Next Customer"
    const saveNextBtn = page.locator('button:has-text("Save & Next Customer")');
    await expect(saveNextBtn).toBeVisible();
    await saveNextBtn.click();

    // Expect success toast
    const toast = page.locator('div[role="status"]').filter({ hasText: /recorded successfully|Loading next/i }).first();
    await expect(toast).toBeVisible({ timeout: 10000 });
  });

  test('CRE saves call with Save & Close', async ({ page }) => {
    await loginAs(page, 'cre1@demomotors.com', 'Password@12345');
    await page.goto('/psf');
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('table tbody tr').first();
    await firstRow.click();

    const saveCloseBtn = page.locator('button:has-text("Save & Close")');
    await expect(saveCloseBtn).toBeVisible();
    await saveCloseBtn.click();

    // Console modal closes
    await expect(page.locator('button:has-text("Save & Close")')).not.toBeVisible({ timeout: 10000 });
  });
});
