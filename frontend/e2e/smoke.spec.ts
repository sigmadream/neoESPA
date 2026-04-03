import { expect, test } from '@playwright/test';

test('home_page_loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Welcome to neoESPA' })).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'View Notices' }),
  ).toBeVisible();
});
