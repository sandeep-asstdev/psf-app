import { test, expect, loginAs } from './test-fixture.js';

test.describe('Super Admin Administration & Governance', () => {
  test('Super Admin adds a new staff user in User Management', async ({ page }) => {
    await loginAs(page, 'superadmin@demomotors.com', 'Admin@12345');
    await page.goto('/users');

    await expect(page.locator('text=Dealership User Management')).toBeVisible({ timeout: 15000 });

    // Click "Add New Staff"
    const addStaffBtn = page.locator('button:has-text("Add New Staff")');
    await expect(addStaffBtn).toBeVisible();
    await addStaffBtn.click();

    // Fill form in modal
    const tag = Date.now().toString().slice(-5);
    const modal = page.locator('h3:has-text("Add New Staff Member")');
    await expect(modal).toBeVisible({ timeout: 10000 });

    await page.locator('input[placeholder*="Rahul Verma" i]').fill(`Suresh Kumar ${tag}`);
    await page.locator('input[placeholder*="apexauto.com" i]').fill(`suresh.${tag}@demomotors.com`);
    await page.locator('input[placeholder*="EMP-" i]').fill(`EMP-${tag}`);

    // Submit
    const submitBtn = page.locator('button:has-text("Create User")');
    await submitBtn.click();

    // Verify success toast
    await expect(
      page.locator('div[role="status"]').filter({ hasText: /created successfully/i }).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test('Super Admin adds a new OEM Brand and Workshop Branch', async ({ page }) => {
    await loginAs(page, 'superadmin@demomotors.com', 'Admin@12345');
    await page.goto('/admin-console?tab=brands_branches');

    // 1. Add Brand
    const addBrandBtn = page.locator('button:has-text("Add Brand")').first();
    await expect(addBrandBtn).toBeVisible({ timeout: 15000 });
    await addBrandBtn.click();

    const tag = Date.now().toString().slice(-4);
    await page.locator('input[placeholder="e.g. Hyundai, MG Motors, Tata Motors"]').fill(`Kia Motors ${tag}`);
    await page.locator('input[placeholder="e.g. HYUN, MG, TATA"]').fill(`KIA${tag}`);
    const saveBrandBtn = page.locator('button:has-text("Create Brand")');
    await saveBrandBtn.click();

    await expect(
      page.locator('div[role="status"]').filter({ hasText: /created successfully/i }).first()
    ).toBeVisible({ timeout: 15000 });

    // 2. Add Branch
    const addBranchBtn = page.locator('button:has-text("Add Branch")').first();
    await expect(addBranchBtn).toBeVisible();
    await addBranchBtn.click();

    await page.locator('input[placeholder*="S8211" i]').fill(`DMS${tag}`);
    await page.locator('input[placeholder*="Apex Central Hubli" i]').fill(`South Hubli Workshop ${tag}`);
    await page.locator('input[placeholder*="APEX-HUBLI" i]').fill(`SH${tag}`);
    const saveBranchBtn = page.locator('button:has-text("Create Branch")');
    await saveBranchBtn.click();

    await expect(
      page.locator('div[role="status"]').filter({ hasText: /created successfully/i }).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test('Super Admin views Questionnaires builder and Role Permission matrix', async ({ page }) => {
    await loginAs(page, 'superadmin@demomotors.com', 'Admin@12345');

    // 1. Questionnaire builder
    await page.goto('/admin-console?tab=questionnaires');
    await expect(
      page.locator('text=Dynamic Questionnaire Builder & Version Control')
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Available Templates')).toBeVisible();

    // 2. Role matrix
    await page.goto('/admin-console?tab=matrix');
    await expect(
      page.locator('text=Matrix Legend:')
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=CRE_ADMIN').first()).toBeVisible();
  });
});

