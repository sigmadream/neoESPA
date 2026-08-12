import { expect, test } from '@playwright/test';

import {
  loginViaUi,
  registerUserViaApi,
  uniqueUser,
} from './helpers';

test('user_can_update_profile_from_profile_page', async ({ page, request }) => {
  const user = uniqueUser('profile');
  await registerUserViaApi(request, user);

  await loginViaUi(page, { id: user.id, password: user.password });
  await page.waitForURL('/');
  await page.goto('/profile');

  await page.getByLabel('Name', { exact: true }).fill('Updated Profile User');
  await page.getByLabel('Phone').fill('010-7777-8888');
  await page.getByLabel('Email').fill(`updated-${user.id}@example.com`);
  await page.getByRole('button', { name: 'Update Profile' }).click();

  await expect(page.getByRole('link', { name: 'Updated Profile User' })).toBeVisible();
  await expect(page.getByLabel('Name', { exact: true })).toHaveValue('Updated Profile User');
  await expect(page.getByLabel('Phone')).toHaveValue('010-7777-8888');
  await expect(page.getByLabel('Email')).toHaveValue(`updated-${user.id}@example.com`);
});

test('profile_page_blocks_password_change_when_confirmation_mismatches', async ({ page, request }) => {
  const user = uniqueUser('confirm');
  await registerUserViaApi(request, user);

  await loginViaUi(page, { id: user.id, password: user.password });
  await page.waitForURL('/');
  await page.goto('/profile');

  await page.getByLabel('Current Password').fill(user.password);
  await page.getByLabel('New Password', { exact: true }).fill('new-student-pass');
  await page.getByLabel('Confirm New Password').fill('different-pass');
  await page.getByRole('button', { name: 'Change Password' }).click();

  await expect(page.getByText('Passwords do not match.')).toBeVisible();

  await page.getByRole('button', { name: '로그아웃' }).click();
  await page.waitForURL('/login');
  await loginViaUi(page, { id: user.id, password: user.password });
  await page.waitForURL('/');
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
});

test('user_can_change_password_from_profile_page', async ({ page, request }) => {
  const user = uniqueUser('password');
  await registerUserViaApi(request, user);

  await loginViaUi(page, { id: user.id, password: user.password });
  await page.waitForURL('/');
  await page.goto('/profile');

  await page.getByLabel('Current Password').fill(user.password);
  await page.getByLabel('New Password', { exact: true }).fill('new-student-pass');
  await page.getByLabel('Confirm New Password').fill('new-student-pass');
  await page.getByRole('button', { name: 'Change Password' }).click();

  await expect(page.getByText('Password updated successfully')).toBeVisible();

  await page.getByRole('button', { name: '로그아웃' }).click();
  await page.waitForURL('/login');

  await loginViaUi(page, { id: user.id, password: 'new-student-pass' });
  await page.waitForURL('/');
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
});
