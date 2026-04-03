import { expect, test } from '@playwright/test';

import { loginViaUi } from './helpers';

test('admin_can_publish_notice', async ({ page, browser }) => {
  const title = `Published Notice ${Date.now()}`;

  await loginViaUi(page, { id: 'admin', password: 'pllab818' });
  await page.waitForURL('/');
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Notices' }).click();

  await page.getByLabel('Title').fill(title);
  await page.getByLabel('Author').fill('Administrator');
  await page.getByLabel('Content').fill('Notice created from Playwright.');
  await page.getByRole('button', { name: 'Create notice' }).click();

  await expect(page.getByText('Notice created successfully.')).toBeVisible();

  const publicPage = await browser.newPage();
  await publicPage.goto('/notice');
  await expect(publicPage.getByText(title)).toBeVisible();
});
