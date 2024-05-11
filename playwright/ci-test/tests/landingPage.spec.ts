import { test, expect } from '@playwright/test';

let url = '/';


test.describe('navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Go to the starting url before each test.
    await page.goto(url);
  });

  test('has title', async ({ page }) => {
    await page.waitForSelector('.landing-page-banner-text-header', { timeout: 2000 });
    await expect(page.locator('div.landing-page-banner-text-header')).toHaveText();
  })
  test('navigates', async ({page}) => {
  });
});
