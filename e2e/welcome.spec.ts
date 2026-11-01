import { expect, test } from '@playwright/test';

test('a new learner chooses a level and gets a corrected first entry', async ({ page }) => {
  await page.goto('/auth/sign-up');
  await page.getByLabel('Email').fill(`welcome-${Date.now()}@example.com`);
  await page.getByLabel('Password').fill('Welcome123!');
  await page.getByRole('button', { name: /Create Account/ }).click();

  await expect(page).toHaveURL(/\/welcome$/, { timeout: 15000 });
  await expect(page.getByRole('heading', { name: 'What are you learning?' })).toBeVisible();

  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('heading', { name: 'How much Spanish can you write today?' })).toBeVisible();
  await page.getByRole('button', { name: /I'm brand new to writing in Spanish/ }).click();
  await page.getByRole('button', { name: 'Continue' }).click();

  await expect(page.getByRole('heading', { name: 'What brings you here?' })).toBeVisible();
  await page.getByRole('button', { name: "I'm in a class" }).click();
  await page.getByRole('button', { name: 'Continue' }).click();

  await expect(page.getByRole('heading', { name: 'Your first entry' })).toBeVisible();
  await page.getByPlaceholder('Your name').fill('Ana');
  await page.getByPlaceholder('Where you are from').fill('Chile');
  await page.getByPlaceholder('Where you live').fill('Madrid');
  await page.getByPlaceholder('Something you like').fill('el café');
  await page.getByRole('button', { name: 'Check my writing' }).click();

  await expect(page).toHaveURL(/\/entries\/[0-9a-f-]+$/i, { timeout: 30000 });
  await expect(page.getByRole('heading', { name: 'Your entry, side by side' })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('[Mock Corrected]')).toBeVisible();
});
