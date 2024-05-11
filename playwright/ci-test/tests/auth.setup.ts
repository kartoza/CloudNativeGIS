import { test as setup, expect } from '@playwright/test';

let url = '/';

let user_email = 'admin@example.com';
let password = 'admin';
const authFile = 'auth.json';


setup.describe('login', () => {

  setup('login', async ({page}) => {

    await page.goto(url);

    const buttonSelector = 'LOGIN';

    await page.waitForSelector(buttonSelector, {timeout: 2000});

    const initialURL = page.url();

    await page.click(buttonSelector);

    await page.waitForURL('**/login/');

    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible();

    await page.getByPlaceholder('E-mail address').fill(user_email);
    
    await page.getByPlaceholder('Password').fill(password);
    
    await page.getByRole('button', { name: 'LOGIN' }).click();

    await page.context().storageState({ path: authFile });
    
  });

});
