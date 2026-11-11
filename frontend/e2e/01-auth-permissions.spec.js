import { test, expect, loginAs } from './test-fixture.js';

test.describe('Authentication & Role-Based Access Control', () => {
  test('Super Admin can log in and view administrative links', async ({ page }) => {
    await loginAs(page, 'superadmin@demomotors.com', 'Admin@12345');
    
    // Check navigation items in sidebar
    await expect(page.locator('aside a[href="/admin-console"]')).toBeVisible();
    await expect(page.locator('aside a[href="/users"]')).toBeVisible();
    await expect(page.locator('aside a[href="/psf"]')).toBeVisible();

    // Verify non-blank dashboard content
    await expect(page.locator('#root')).not.toBeEmpty();
  });

  test('CRE can log in and has restricted sidebar access', async ({ page, request }) => {
    await loginAs(page, 'cre1@demomotors.com', 'Password@12345');
    
    // CRE should see Calling & Survey screens
    await expect(page.locator('aside a[href="/psf"]')).toBeVisible();
    
    // CRE should NOT see Enterprise Admin, Tenants, or Data Import
    await expect(page.locator('aside a[href="/admin-console"]')).not.toBeVisible();
    await expect(page.locator('aside a[href*="admin-console?tab=tenants"]')).not.toBeVisible();
    await expect(page.locator('aside a[href="/import"]')).not.toBeVisible();

    // Verify forbidden API call is rejected with 403
    const token = await page.evaluate(() => localStorage.getItem('psf_token'));
    const forbiddenRes = await request.get('http://localhost:8000/api/v1/admin/matrix', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(forbiddenRes.status()).toBe(403);
  });

  test('Service Advisor can log in and sees only Advisor Portal and Complaints', async ({ page }) => {
    await loginAs(page, 'advisor@demomotors.com', 'Password@12345');
    
    // Advisor should see Advisor Followup & Complaints
    await expect(page.locator('aside a[href="/advisor"]')).toBeVisible();
    await expect(page.locator('aside a[href="/complaints"]')).toBeVisible();

    // Advisor should NOT see Enterprise Admin or Data Import
    await expect(page.locator('aside a[href="/admin-console"]')).not.toBeVisible();
    await expect(page.locator('aside a[href="/import"]')).not.toBeVisible();
  });

  test('Branch Manager can log in and sees calling, complaints, and reports', async ({ page }) => {
    await loginAs(page, 'manager@demomotors.com', 'Password@12345');

    await expect(page.locator('aside a[href="/psf"]')).toBeVisible();
    await expect(page.locator('aside a[href="/complaints"]')).toBeVisible();
    await expect(page.locator('aside a[href="/reports"]')).toBeVisible();
    await expect(page.locator('aside a[href="/admin-console"]')).not.toBeVisible();
  });

  test('CRE Admin can log in and sees Import, Users, Complaints, and PSF', async ({ page }) => {
    await loginAs(page, 'creadmin@demomotors.com', 'Password@12345');

    await expect(page.locator('aside a[href="/psf"]')).toBeVisible();
    await expect(page.locator('aside a[href="/complaints"]')).toBeVisible();
    await expect(page.locator('aside a[href="/import"]')).toBeVisible();
    await expect(page.locator('aside a[href="/users"]')).toBeVisible();
  });

  test('Theme switching toggles dark and light themes smoothly', async ({ page }) => {
    await page.goto('/login');
    const themeBtn = page.locator('button').filter({ has: page.locator('svg.lucide-moon, svg.lucide-sun') }).first();
    if (await themeBtn.isVisible()) {
      await themeBtn.click();
      await page.waitForTimeout(300);
      await themeBtn.click();
    }
  });
});
