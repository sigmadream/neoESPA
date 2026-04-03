import { expect, test } from '@playwright/test';

import {
  createHomeworkViaAdminApi,
  createSubmissionViaApi,
  loginViaApi,
  loginViaUi,
  registerUserViaApi,
  relativeDate,
  uniqueUser,
} from './helpers';

test('admin_can_compare_flagged_submissions', async ({ page, request }) => {
  const firstUser = uniqueUser('plag-first');
  const secondUser = uniqueUser('plag-second');
  await registerUserViaApi(request, firstUser);
  await registerUserViaApi(request, secondUser);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Plagiarism Homework ${Date.now()}`,
    intro: 'Plagiarism intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'plagiarism-ui',
    allowed_languages: ['python'],
    testcases: [],
  });
  const firstSession = await loginViaApi(request, {
    id: firstUser.id,
    password: firstUser.password,
  });
  const secondSession = await loginViaApi(request, {
    id: secondUser.id,
    password: secondUser.password,
  });
  await createSubmissionViaApi(request, firstSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "print('copied')\n",
    original_filename: 'main.py',
  });
  await createSubmissionViaApi(request, secondSession.token, {
    homework_num: homework.num,
    language: 'python',
    code_text: "print('copied')\n",
    original_filename: 'main.py',
  });

  await loginViaUi(page, { id: 'admin', password: 'pllab818' });
  await page.waitForURL('/');
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Plagiarism' }).click();
  await page.getByRole('combobox').selectOption(String(homework.num));
  await page.getByRole('button', { name: 'Run scan' }).click();

  await expect(page.getByText('flagged 1 pairs')).toBeVisible();
  await page.getByRole('button', { name: new RegExp(`${firstUser.id} vs ${secondUser.id}`) }).click();
  await expect(page.getByText("print('copied')")).toHaveCount(2);
});
