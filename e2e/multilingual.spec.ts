import { test, expect } from '@playwright/test';

test.describe('Multilingual UX Smoke Tests', () => {
  
  test('Spanish UI language shows translated content', async ({ page }) => {
    // Navigate to the root page first
    await page.goto('/');
    
    // Wait for the page to load and i18n to initialize
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Give i18n time to initialize
    
    // Find and click the dev language switcher button
    const languageSwitcher = page.locator('[data-testid="dev-language-switcher"]');
    await expect(languageSwitcher).toBeVisible();
    
    // Click on the language button to open dropdown
    await page.locator('[data-testid="dev-language-switcher"] button').first().click();
    await page.waitForTimeout(500);
    
    // Click on Spanish option (look for the text containing "Español")
    await page.locator('text=Español').first().click();
    await page.waitForTimeout(1000); // Wait for language change to take effect
    
    // Verify the language switcher now shows Spanish
    await expect(page.locator('[data-testid="dev-language-switcher"]')).toContainText('Español');
    
    // Verify current language indicator changed
    await expect(page.locator('text=Current: es')).toBeVisible();
    
    // Verify the fallback test key shows English (since it doesn't exist in Spanish)
    await expect(page.locator('text=/fallback.*test/i')).toBeVisible();
  });

  test('Pseudo-localization shows bracketed strings with ?pseudo=1', async ({ page }) => {
    // Navigate with pseudo-localization enabled
    await page.goto('/?pseudo=1');
    
    // Wait for the page to load and pseudo-loc to initialize
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Check that pseudo indicator shows it's enabled
    await expect(page.locator('text=Pseudo: ON')).toBeVisible();
    
    // Verify pseudo-localization affects the welcome text (should have brackets and special chars)
    // Look for any text with brackets - the auth page should have pseudo-localized content
    const pseudoElements = page.locator('text=/\\[.*\\]/');
    await expect(pseudoElements.first()).toBeVisible();
    
    // Check for accented characters that pseudo-loc adds
    const accentedText = page.locator('text=/[áéíóúñ]/');
    await expect(accentedText.first()).toBeVisible();
  });

  test('Arabic (RTL) language sets html dir="rtl"', async ({ page }) => {
    // Navigate to the root page
    await page.goto('/');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Find and click the dev language switcher button
    const languageSwitcher = page.locator('[data-testid="dev-language-switcher"]');
    await expect(languageSwitcher).toBeVisible();
    
    // Click on the language button to open dropdown
    await page.locator('[data-testid="dev-language-switcher"] button').first().click();
    await page.waitForTimeout(500);
    
    // Click on Arabic option (look for Arabic text العربية)
    await page.locator('text=العربية').first().click();
    await page.waitForTimeout(1000); // Wait for language change
    
    // Verify HTML dir attribute is set to rtl
    const htmlElement = page.locator('html');
    await expect(htmlElement).toHaveAttribute('dir', 'rtl');
    
    // Verify the language switcher now shows Arabic
    await expect(page.locator('[data-testid="dev-language-switcher"]')).toContainText('العربية');
    
    // Verify current language indicator changed
    await expect(page.locator('text=Current: ar')).toBeVisible();
  });

  test('Language persistence works correctly', async ({ page }) => {
    // Start on root page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Switch to Spanish
    await page.locator('[data-testid="dev-language-switcher"] button').first().click();
    await page.waitForTimeout(500);
    await page.locator('text=Español').first().click();
    await page.waitForTimeout(1000);
    
    // Verify Spanish is active
    await expect(page.locator('text=Current: es')).toBeVisible();
    
    // Navigate to another page and verify language persists
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Language should still be Spanish
    await expect(page.locator('text=Current: es')).toBeVisible();
    await expect(page.locator('[data-testid="dev-language-switcher"]')).toContainText('Español');
  });
});
