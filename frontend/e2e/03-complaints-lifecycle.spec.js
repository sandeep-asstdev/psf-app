import { test, expect, loginAs } from './test-fixture.js';

test.describe('Complaints Lifecycle & Reconfirmation Calling', () => {
  test('CRE Admin views complaints, updates status to RESOLVED, and performs Reconfirmation', async ({ page }) => {
    await loginAs(page, 'creadmin@demomotors.com', 'Password@12345');
    await page.goto('/complaints');
    await page.waitForLoadState('networkidle');

    // 1. Table should be visible
    const table = page.locator('table');
    await expect(table).toBeVisible({ timeout: 10000 });

    // 2. Click "Manage" on the first complaint row
    const manageBtn = page.locator('button:has-text("Manage")').first();
    await expect(manageBtn).toBeVisible({ timeout: 10000 });
    await manageBtn.click();

    // 3. Ticket Detail modal opens - verify lifecycle section
    await expect(page.locator('text=Update Ticket Lifecycle Status')).toBeVisible({ timeout: 10000 });

    // 4. Select New Status: RESOLVED inside modal form
    const statusSelect = page.locator('form select').first();
    await statusSelect.selectOption('RESOLVED');

    // 5. Fill resolution remarks
    const remarksTextarea = page.locator('textarea[placeholder*="Explain how the issue was fixed" i]');
    await expect(remarksTextarea).toBeVisible();
    await remarksTextarea.fill('Brake inspection completed and parts replaced under warranty.');

    // 6. Click Save Lifecycle Status
    const saveBtn = page.locator('button:has-text("Save Lifecycle Status")');
    await saveBtn.click();

    // Verify success toast
    await expect(
      page.locator('div[role="status"]').filter({ hasText: /status updated to RESOLVED/i }).first()
    ).toBeVisible({ timeout: 10000 });

    // 7. Post-Resolution Reconfirmation Call
    await expect(page.locator('text=Post-Resolution Reconfirmation Call')).toBeVisible();
    const reconfFeedback = page.locator('textarea[placeholder*="Customer verbatim remarks" i]');
    if (await reconfFeedback.isVisible()) {
      await reconfFeedback.fill('Customer contacted; confirmed vehicle running well and issue fixed.');
      const confirmBtn = page.locator('button:has-text("Confirm Satisfaction & Close Ticket")');
      await confirmBtn.click();
      await expect(
        page.locator('div[role="status"]').filter({ hasText: /verified satisfaction|CLOSED/i }).first()
      ).toBeVisible({ timeout: 10000 });
    }
  });
});
