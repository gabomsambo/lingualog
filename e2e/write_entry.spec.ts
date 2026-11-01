import { test, expect } from '@playwright/test';

// E2E smoke test for the main user flow: write and submit an entry, then view it in the list
test('User can write an entry and see it in the entries list', async ({ page }) => {
  // The local Supabase seed provides a stable account for the protected app routes.
  await page.goto('/auth/sign-in');
  await page.getByRole('button', { name: 'Sign in with Password' }).click();
  await page.getByLabel('Email').fill('demo@lingualog.dev');
  await page.getByLabel('Password').fill('DemoPass123!');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL('**/dashboard');

  // Navigate to the new entry page
  await page.goto('/entries/new');
  
  // Verify that the journal editor is visible
  await expect(page.getByRole('heading', { name: /New Entry/, level: 1 })).toBeVisible();
  
  // Type text into the journal editor textarea
  const entryText = 'Hola, escribí mucho hoy.';
  await page.locator('textarea').fill(entryText);
  
  // Click the submit button
  await page.locator('button:has-text("Submit")').click();
  
  // Beginners get the calm result first; the existing full result remains one tap away.
  const detailsToggle = page.getByTestId('calm-details-toggle');
  if (await detailsToggle.count()) {
    await expect(page.getByTestId('calm-result')).toBeVisible();
    await expect(page.getByTestId('full-entry-details')).toHaveCount(0);
    await detailsToggle.click();
  }
  await expect(page.locator('text=Feedback Results')).toBeVisible({ timeout: 10000 });
  
  // Verify that rewrite text has appeared
  await expect(page.getByRole('heading', { name: /Native-like Rewrite/ })).toBeVisible();
  
  // Navigate to the entries list
  await page.goto('/entries');
  
  // Verify that the entries page loaded
  await expect(page.locator('h1:has-text("Your Journal Entries")')).toBeVisible();
  
  // Check that our new entry is visible in the list
  await expect(page.getByText(entryText.substring(0, 20)).first()).toBeVisible();

  // The Today card uses the prompt bank and hands a one-sentence starter to the editor.
  await page.goto('/dashboard');
  await expect(page.getByTestId('today-card')).toBeVisible();
  const oneSentence = page.getByTestId('today-write-one-sentence');
  await expect(oneSentence).toBeVisible();
  await oneSentence.click();
  await expect(page).toHaveURL(/today_prompt_id=.*today_entry_mode=one_sentence/);
  await expect(page.getByTestId('today-prompt-context')).toBeVisible();
});
