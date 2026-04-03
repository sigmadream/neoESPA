import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createHomeworkViaAdminApi,
  createNoticeViaAdminApi,
  createSubmissionViaApi,
  gradeSubmissionViaApi,
  loginViaApi,
  registerUserViaApi,
  relativeDate,
  uniqueUser,
} from './helpers';

test('student_can_submit_assignment', async ({ page, request }) => {
  const user = uniqueUser('submit-ui');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Submit UI Homework ${Date.now()}`,
    intro: 'Submit UI intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'submit-ui',
    allowed_languages: ['python'],
    testcases: [],
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto(`/homework/${homework.num}`);
  await expect(page.locator('#language option')).toHaveCount(1);
  await expect(page.locator('#language option')).toHaveText(['Python']);
  await page.getByLabel('Source Code').fill("print('submitted')\n");
  await page.getByRole('button', { name: 'Submit Assignment' }).click();

  await page.waitForURL(/\/homework\/result\?id=/);
  await expect(page.getByText('Grading Pending')).toBeVisible();
});

test('student_can_view_submission_history', async ({ page, request }) => {
  const user = uniqueUser('history');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `History Homework ${Date.now()}`,
    intro: 'History intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'history',
    allowed_languages: ['python'],
    testcases: [],
  });
  const userSession = await loginViaApi(request, {
    id: user.id,
    password: user.password,
  });
  await createSubmissionViaApi(request, userSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "print('first')\n",
    original_filename: 'main.py',
  });
  const secondSubmission = await createSubmissionViaApi(request, userSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "print('second')\n",
    original_filename: 'main.py',
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto(`/homework/result?id=${secondSubmission.id}`);

  await expect(page.getByText('2 attempts')).toBeVisible();
  await expect(page.getByRole('cell', { name: '#2' }).first()).toBeVisible();
  await expect(page.getByRole('cell', { name: '#1' }).first()).toBeVisible();
});

test('legacy_submit_result_route_redirects_to_homework_result', async ({ page, request }) => {
  const user = uniqueUser('legacy-result');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Legacy Result Homework ${Date.now()}`,
    intro: 'Legacy result intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'legacy-result',
    allowed_languages: ['python'],
    testcases: [],
  });
  const userSession = await loginViaApi(request, {
    id: user.id,
    password: user.password,
  });
  const submission = await createSubmissionViaApi(request, userSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "print('legacy')\n",
    original_filename: 'main.py',
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto(`/submit/result?id=${submission.id}`);

  await expect(page).toHaveURL(new RegExp(`/homework/result\\?id=${submission.id}$`));
  await expect(page.getByText('Grading Pending')).toBeVisible();
});

test('grading_status_updates_are_visible', async ({ page, request }) => {
  const user = uniqueUser('grading-status');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Grading Status Homework ${Date.now()}`,
    intro: 'Status intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'grading-status',
    allowed_languages: ['python'],
    testcases: [],
  });
  const userSession = await loginViaApi(request, {
    id: user.id,
    password: user.password,
  });
  const submission = await createSubmissionViaApi(request, userSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "print('ok')\n",
    original_filename: 'main.py',
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto(`/homework/result?id=${submission.id}`);
  await expect(page.getByText('Grading Pending')).toBeVisible();

  await gradeSubmissionViaApi(request, submission.id);
  await page.reload();

  await expect(page.getByText('Grading Complete')).toBeVisible();
});

test('student_sees_feedback_links_after_grading', async ({ page, request }) => {
  const user = uniqueUser('feedback');
  await registerUserViaApi(request, user);
  await createNoticeViaAdminApi(request, {
    title: `Feedback Notice ${Date.now()}`,
    author: 'Administrator',
    content: 'Check the latest grading policy update.',
    is_pinned: true,
    is_published: true,
  });
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Feedback Homework ${Date.now()}`,
    intro: 'Feedback intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(0, 4),
    codeName: 'feedback',
    allowed_languages: ['python'],
    testcases: [],
  });
  const userSession = await loginViaApi(request, {
    id: user.id,
    password: user.password,
  });
  const submission = await createSubmissionViaApi(request, userSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "def broken(:\n    pass\n",
    original_filename: 'broken.py',
  });
  await gradeSubmissionViaApi(request, submission.id);

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto(`/homework/result?id=${submission.id}`);

  await expect(page.getByTestId('feedback-hints')).toBeVisible();
  await expect(page.getByText('최신 공지 보기:')).toBeVisible();
});

test('student_sees_weekly_code_quality_guide', async ({ page, request }) => {
  const user = uniqueUser('lint-guide');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Lint Homework ${Date.now()}`,
    intro: 'Lint intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'lint-guide',
    isLint: true,
    lint_week: '2',
    allowed_languages: ['python'],
    testcases: [],
  });
  const userSession = await loginViaApi(request, {
    id: user.id,
    password: user.password,
  });
  const submission = await createSubmissionViaApi(request, userSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "def main():\n    unused_value = 1\n    print('ok')\n\nmain()\n",
    original_filename: 'main.py',
  });
  await gradeSubmissionViaApi(request, submission.id);

  await authenticatePage(page, request, { id: user.id, password: user.password });
  await page.goto(`/homework/result?id=${submission.id}`);

  await expect(page.getByTestId('weekly-code-quality-guide')).toBeVisible();
  await expect(page.getByText('코딩 규칙 가이드')).toBeVisible();
});
