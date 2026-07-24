import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createNoticeViaAdminApi,
  registerUserViaApi,
  uniqueUser,
} from './helpers';

test('student_sees_new_notice_notification', async ({ page, request }) => {
  const user = uniqueUser('notification');
  await registerUserViaApi(request, user);
  const notice = await createNoticeViaAdminApi(request, {
    title: `Notification Notice ${Date.now()}`,
    author: 'Administrator',
    content: 'A new notice should produce a student notification.',
    is_pinned: false,
    is_published: true,
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto('/notifications');

  await expect(page.getByText(`새 공지: ${notice.title}`)).toBeVisible();
  await expect(page.getByRole('link', { name: 'View Notice' })).toBeVisible();
});
