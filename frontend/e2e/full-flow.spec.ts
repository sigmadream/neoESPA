import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createHomeworkViaAdminApi,
  gradeSubmissionViaApi,
  registerUserViaApi,
  relativeDate,
  uniqueUser,
} from './helpers';

test('student_submission_flow', async ({ page, request }) => {
  const user = uniqueUser('full-flow');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Full Flow Homework ${Date.now()}`,
    intro: 'Flow intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'full-flow',
    allowed_languages: ['python'],
    testcases: [
      {
        name: 'sample',
        input: '2 3\n',
        expected_output: '5\n',
        score: 100,
        is_hidden: false,
      },
    ],
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto('/homework');
  await page.getByText(`Full Flow Homework`).click();
  await expect(page).toHaveURL(new RegExp(`/homework/${homework.num}$`));

  await page.getByLabel('Source Code').fill(
    'a, b = map(int, input().split())\nprint(a + b)\n',
  );
  await page.getByRole('button', { name: 'Submit Assignment' }).click();
  await page.waitForURL(/\/homework\/result\?id=/);

  const currentUrl = new URL(page.url());
  const submissionId = Number(currentUrl.searchParams.get('id'));
  await gradeSubmissionViaApi(request, submissionId);

  await page.reload();
  await expect(page.getByText('Grading Complete')).toBeVisible();
  await page.goto('/dashboard');
  await expect(
    page.getByRole('link', {
      name: new RegExp(`#${homework.num}\\s+Full Flow Homework`),
    }).first(),
  ).toBeVisible();
});
