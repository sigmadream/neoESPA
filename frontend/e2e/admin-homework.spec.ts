import { expect, test } from '@playwright/test';

import { loginViaUi, relativeDate } from './helpers';

test('admin_can_edit_homework_settings', async ({ page }) => {
  const initialTitle = `UI Homework ${Date.now()}`;
  const updatedTitle = `${initialTitle} Updated`;

  await loginViaUi(page, { id: 'admin', password: 'pllab818' });
  await page.waitForURL('/');
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Homework' }).click();

  await page.getByLabel('Title').fill(initialTitle);
  await page.getByLabel('Code Name').fill('ui-homework');
  await page.getByLabel('Description (Intro)').fill('Homework created from Playwright.');
  await page.getByLabel('Start Time').fill(relativeDate(-1));
  await page.getByLabel('Deadline').fill(relativeDate(2));
  await page.getByRole('button', { name: 'Create Assignment' }).click();

  await expect(page.getByText('Created successfully.')).toBeVisible();

  const inventoryItem = page
    .locator('div.group')
    .filter({ hasText: initialTitle })
    .first();
  await inventoryItem.getByRole('button', { name: 'Edit homework' }).click();
  await page.getByLabel('Title').fill(updatedTitle);
  await page.getByRole('button', { name: 'Update Assignment' }).click();

  await expect(page.getByText('Updated successfully.')).toBeVisible();
  await expect(page.getByText(updatedTitle)).toBeVisible();
});
