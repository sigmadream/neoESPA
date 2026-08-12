import { expect, test } from '@playwright/test';

import {
  registerUserViaApi,
  registerViaUi,
  loginViaUi,
  uniqueUser,
} from './helpers';

test('student_can_register_account', async ({ page }) => {
  const user = uniqueUser('register');
  await registerViaUi(page, user);

  await page.waitForURL('/');
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
});

test('student_can_login_and_persist_session', async ({ page, request }) => {
  const user = uniqueUser('login');
  await registerUserViaApi(request, user);

  await loginViaUi(page, { id: user.id, password: user.password });
  await page.waitForURL('/');
  await page.reload();
  await page.goto('/dashboard');

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible();
});

test('protected_pages_redirect_when_unauthenticated', async ({ page }) => {
  await page.goto('/profile');
  await page.waitForURL(/\/login\?next=/);

  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();
});

test('expired_session_forces_relogin', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      'neoespa.auth.session',
      JSON.stringify({
        token: 'expired-token',
        user: {
          id: 'expired',
          sid: 20259999,
          name: 'Expired User',
          phone: '010-0000-0000',
          email: 'expired@example.com',
          user_group: 'student',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      }),
    );
  });

  await page.goto('/profile');
  await page.waitForURL(/\/login\?next=%2Fprofile/);

  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible();
});
