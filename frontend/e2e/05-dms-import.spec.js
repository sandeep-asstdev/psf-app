import { test, expect, loginAs } from './test-fixture.js';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('DMS Import & Automatic Call Allocation', () => {
  test('CRE Admin imports a DMS file, calls split equally among present CREs, and counts are shown', async ({ page }) => {
    // Generate fresh non-duplicate job card numbers
    const batchTag = Date.now().toString().slice(-6);
    const testCsvPath = path.join(__dirname, `test_dms_batch_${batchTag}.csv`);
    const csvContent = [
      'brand,branch,job_card_no,job_card_date,customer_name,contact_number,vin_no,reg_no,model,service_advisor,service_type,total_service_amount',
      `Hyundai,Central Workshop Hubli,RO-DMS-${batchTag}-01,11-11-2026,Amit Patil,9876543210,MALBA51BLM${batchTag}1,KA-25-EA-1001,Creta,Mahesh Joshi,Paid Service,4500`,
      `Hyundai,Central Workshop Hubli,RO-DMS-${batchTag}-02,11-11-2026,Priya Kulkarni,9876543211,MALBA51BLM${batchTag}2,KA-25-EA-1002,Venue,Mahesh Joshi,Periodic Maintenance,5200`,
      `Hyundai,Central Workshop Hubli,RO-DMS-${batchTag}-03,11-11-2026,Rahul Deshmukh,9876543212,MALBA51BLM${batchTag}3,KA-25-EA-1003,i20,Mahesh Joshi,General Repair,3100`,
      `Hyundai,Central Workshop Hubli,RO-DMS-${batchTag}-04,11-11-2026,Sneha Joshi,9876543213,MALBA51BLM${batchTag}4,KA-25-EA-1004,Verna,Mahesh Joshi,Running Repair,6800`,
      `Hyundai,Central Workshop Hubli,RO-DMS-${batchTag}-05,11-11-2026,Vikram Rao,9876543214,MALBA51BLM${batchTag}5,KA-25-EA-1005,Tucson,Mahesh Joshi,Periodic Maintenance,8900`,
      `Hyundai,Central Workshop Hubli,RO-DMS-${batchTag}-06,11-11-2026,Deepa Hegde,9876543215,MALBA51BLM${batchTag}6,KA-25-EA-1006,Alcazar,Mahesh Joshi,Paid Service,7400`,
    ].join('\n');

    fs.writeFileSync(testCsvPath, csvContent);

    try {
      await loginAs(page, 'creadmin@demomotors.com', 'Password@12345');
      await page.goto('/import');

      await expect(page.locator('h1').filter({ hasText: 'DMS Data Import' })).toBeVisible({ timeout: 15000 });
      // Ensure dropdown options have loaded
      await expect(page.locator('select').first()).not.toBeEmpty();

      // File path to upload
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testCsvPath);

      // Verify file name shows in UI
      await expect(page.locator(`text=test_dms_batch_${batchTag}.csv`)).toBeVisible({ timeout: 10000 });

      // Click Import & Assign Calls to CREs button
      const importBtn = page.locator('button:has-text("Import & Assign Calls to CREs")');
      await expect(importBtn).toBeVisible();
      await importBtn.click();

      // Verify success toast or Import Complete heading
      await expect(
        page.locator('h2:has-text("Import Complete & Calls Assigned!"), div[role="status"]:has-text("Successfully imported")').first()
      ).toBeVisible({ timeout: 15000 });

      // Verify summary section
      await expect(page.locator('text=Calls Assigned to Present CREs')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Equal Split')).toBeVisible();

      // Verify assigned CREs cards are visible
      const creCards = page.locator('text=Assigned CRE');
      await expect(creCards.first()).toBeVisible({ timeout: 10000 });
      expect(await creCards.count()).toBeGreaterThanOrEqual(1);
    } finally {
      // Clean up temporary CSV file
      if (fs.existsSync(testCsvPath)) {
        fs.unlinkSync(testCsvPath);
      }
    }
  });
});
