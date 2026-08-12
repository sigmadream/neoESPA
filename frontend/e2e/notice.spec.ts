import { expect, test } from '@playwright/test';

import { authenticatePage } from './helpers';

test('student_can_open_notice_detail', async ({ page, request }) => {
  await authenticatePage(page, request, { id: 'testuser', password: 'qwer1234' });
  await page.goto('/notice');

  await expect(page.getByRole('heading', { name: 'Welcome to neoESPA' })).toBeVisible();
  await page.locator('a').filter({ hasText: 'Welcome to neoESPA' }).click();
  await expect(page).toHaveURL(/\/notice\/1$/);
  await expect(
    page.getByText('Read the first assignment and verify that your account'),
  ).toBeVisible();
});
