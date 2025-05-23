import { test, expect } from '@playwright/test';

// E2E smoke test for the main user flow: write and submit an entry, then view it in the list
test('User can write an entry and see it in the entries list', async ({ page }) => {
  // Navigate to the new entry page
  await page.goto('/entries/new');
  
  // Verify that the journal editor is visible
  await expect(page.locator('h1:has-text("New Journal Entry")')).toBeVisible();
  
  // Type text into the journal editor textarea
  const entryText = 'Hola, escribí mucho hoy.';
  await page.locator('textarea').fill(entryText);
  
  // Click the submit button
  await page.locator('button:has-text("Submit")').click();
  
  // Wait for the feedback results to appear
  await expect(page.locator('text=Feedback Results')).toBeVisible({ timeout: 10000 });
  
  // Verify that rewrite text has appeared
  await expect(page.locator('.p-4 >> text=Native-like Rewrite')).toBeVisible();
  
  // Navigate to the entries list
  await page.goto('/entries');
  
  // Verify that the entries page loaded
  await expect(page.locator('h1:has-text("Your Journal Entries")')).toBeVisible();
  
  // Check that our new entry is visible in the list
  await expect(page.locator(`text=${entryText.substring(0, 20)}`)).toBeVisible();
}); 