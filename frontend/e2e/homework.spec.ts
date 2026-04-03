import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createHomeworkViaAdminApi,
  relativeDate,
  uniqueUser,
  registerUserViaApi,
} from './helpers';

test('student_can_browse_homework_list', async ({ page, request }) => {
  await authenticatePage(page, request, { id: 'testuser', password: 'qwer1234' });
  await page.goto('/homework');

  await expect(page.getByText('Sample Problem: A+B')).toBeVisible();
  await page.getByRole('link', { name: 'Sample Problem: A+B' }).click();
  await expect(page).toHaveURL(/\/homework\/1$/);
  await expect(page.getByText('Sample Problem: A+B')).toBeVisible();
});

test('status_badges_follow_assignment_schedule', async ({ page, request }) => {
  const user = uniqueUser('homework-status');
  await registerUserViaApi(request, user);
  const closingSoonHomework = await createHomeworkViaAdminApi(request, {
    title: `Closing Soon Homework ${Date.now()}`,
    intro: 'Closing soon intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(0, 6),
    codeName: 'closing-soon',
    allowed_languages: ['python'],
    testcases: [],
  });
  const closedHomework = await createHomeworkViaAdminApi(request, {
    title: `Closed Homework ${Date.now()}`,
    intro: 'Closed intro',
    starttime: relativeDate(-3),
    deadline: relativeDate(-1),
    codeName: 'closed',
    allowed_languages: ['python'],
    testcases: [],
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto('/homework');

  await expect(page.getByText('진행 중').first()).toBeVisible();

  const closingSoonRow = page
    .getByRole('row', { name: new RegExp(`#${closingSoonHomework.num}`) })
    .first();
  await expect(closingSoonRow.getByText('마감 임박')).toBeVisible();

  const closedRow = page
    .getByRole('row', { name: new RegExp(`#${closedHomework.num}`) })
    .first();
  await expect(closedRow.getByText('마감 완료')).toBeVisible();
});
