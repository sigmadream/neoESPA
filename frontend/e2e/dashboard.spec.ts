import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createHomeworkViaAdminApi,
  createSubmissionViaApi,
  gradeSubmissionViaApi,
  loginViaApi,
  registerUserViaApi,
  relativeDate,
  uniqueUser,
} from './helpers';

test('student_can_view_personal_progress', async ({ page, request }) => {
  const user = uniqueUser('dashboard');
  await registerUserViaApi(request, user);
  const gradedHomework = await createHomeworkViaAdminApi(request, {
    title: 'Dashboard Graded Homework',
    intro: 'Graded intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'graded-homework',
    allowed_languages: ['python'],
    testcases: [
      {
        name: 'sample',
        input: '1 2\n',
        expected_output: '3\n',
        score: 100,
        is_hidden: false,
      },
    ],
  });
  const pendingHomework = await createHomeworkViaAdminApi(request, {
    title: 'Dashboard Pending Homework',
    intro: 'Pending intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'pending-homework',
    allowed_languages: ['python'],
    testcases: [],
  });

  const userSession = await loginViaApi(request, {
    id: user.id,
    password: user.password,
  });
  const gradedSubmission = await createSubmissionViaApi(request, userSession.token, {
    homework_num: gradedHomework.num,
    language: 'python',
    code_text: "a, b = map(int, input().split())\nprint(a + b)\n",
    original_filename: 'main.py',
  });
  await gradeSubmissionViaApi(request, gradedSubmission.id);
  await createSubmissionViaApi(request, userSession.token, {
    homework_num: pendingHomework.num,
    language: 'python',
    code_text: "print('pending')\n",
    original_filename: 'main.py',
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto('/dashboard');

  await expect(
    page.getByRole('link', {
      name: new RegExp(`#${gradedHomework.num}\\s+Dashboard Graded Homework`),
    }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole('link', {
      name: new RegExp(`#${pendingHomework.num}\\s+Dashboard Pending Homework`),
    }).first(),
  ).toBeVisible();
  await expect(page.getByText('제출 완료').first()).toBeVisible();
  await expect(page.getByText('채점 대기').first()).toBeVisible();
  await expect(page.getByText('최근 평균 점수').first()).toBeVisible();
});
