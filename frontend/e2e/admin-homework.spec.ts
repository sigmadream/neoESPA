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
  await page.getByLabel('Code name').fill('ui-homework');
  await page.getByLabel('Intro').fill('Homework created from Playwright.');
  await page.getByLabel('Start time').fill(relativeDate(-1));
  await page.getByLabel('Deadline').fill(relativeDate(2));
  await page.getByRole('button', { name: 'Create homework' }).click();

  await expect(page.getByText('Homework created successfully.')).toBeVisible();

  const inventoryItem = page.locator('article').filter({ hasText: initialTitle }).first();
  await inventoryItem.getByRole('button', { name: 'Edit' }).click();
  await page.getByLabel('Title').fill(updatedTitle);
  await page.getByRole('button', { name: 'Update homework' }).click();

  await expect(page.getByText('Homework updated successfully.')).toBeVisible();
  await expect(page.getByText(updatedTitle)).toBeVisible();
});
