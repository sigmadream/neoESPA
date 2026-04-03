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

  await page.getByLabel('이름').fill('Updated Profile User');
  await page.getByLabel('전화번호').fill('010-7777-8888');
  await page.getByLabel('이메일').fill(`updated-${user.id}@example.com`);
  await page.getByRole('button', { name: '프로필 저장' }).click();

  await expect(page.getByText('Updated Profile User (student)')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Updated Profile User님의 프로필' })).toBeVisible();
  await expect(page.getByLabel('전화번호')).toHaveValue('010-7777-8888');
  await expect(page.getByLabel('이메일')).toHaveValue(`updated-${user.id}@example.com`);
});

test('profile_page_blocks_password_change_when_confirmation_mismatches', async ({ page, request }) => {
  const user = uniqueUser('confirm');
  await registerUserViaApi(request, user);

  await loginViaUi(page, { id: user.id, password: user.password });
  await page.waitForURL('/');
  await page.goto('/profile');

  await page.getByLabel('현재 비밀번호').fill(user.password);
  await page.getByLabel('새 비밀번호', { exact: true }).fill('new-student-pass');
  await page.getByLabel('새 비밀번호 확인').fill('different-pass');
  await page.getByRole('button', { name: '비밀번호 변경' }).click();

  await expect(
    page.getByText('새 비밀번호와 확인 비밀번호가 일치하지 않습니다.'),
  ).toBeVisible();

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

  await page.getByLabel('현재 비밀번호').fill(user.password);
  await page.getByLabel('새 비밀번호', { exact: true }).fill('new-student-pass');
  await page.getByLabel('새 비밀번호 확인').fill('new-student-pass');
  await page.getByRole('button', { name: '비밀번호 변경' }).click();

  await expect(page.getByText('Password updated successfully')).toBeVisible();

  await page.getByRole('button', { name: '로그아웃' }).click();
  await page.waitForURL('/login');

  await loginViaUi(page, { id: user.id, password: 'new-student-pass' });
  await page.waitForURL('/');
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
});
