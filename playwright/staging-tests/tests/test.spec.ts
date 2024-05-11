import { test, expect } from '@playwright/test';

test.use({
  storageState: 'auth.json'
});

test('test', async ({ page }) => {
  await page.goto('https://example.com/');
  await expect(page.getByRole('heading', { name: 'Example Domain' })).toBeVisible();
  await expect(page.getByText('This domain is for use in')).toBeVisible();
  await page.getByRole('heading', { name: 'Example Domain' }).click();
  await page.getByText('This domain is for use in').click();
  await page.getByRole('link', { name: 'More information...' }).click();
  await page.getByRole('heading', { name: 'Example Domains' }).click();
  await page.getByRole('link', { name: 'Homepage' }).click();
  await page.locator('h1').click();
  await page.getByText('The global coordination of').click();
});