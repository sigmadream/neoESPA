import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createExamViaAdminApi,
  registerUserViaApi,
  relativeDate,
  uniqueUser,
} from './helpers';

test('student can view exam list, enter exam, submit code, and view result', async ({
  page,
  request,
}) => {
  const user = uniqueUser('exam-ui');
  await registerUserViaApi(request, user);
  const examTitle = `Exam UI Flow ${Date.now()}`;
  const exam = await createExamViaAdminApi(request, {
    title: examTitle,
    intro: 'Exam UI intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(1),
    codeName: 'exam-ui',
    allowed_languages: ['python'],
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });

  await page.goto('/exam');
  await expect(page.locator('h1')).toContainText('Exams & Assessments');
  await expect(page.getByText(examTitle)).toBeVisible();

  await page.getByText(examTitle).click();
  await page.waitForURL(`/exam/${exam.id}`);
  await expect(page.getByText('Exam Mode')).toBeVisible();
  await expect(page.getByRole('heading', { name: examTitle })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Submit Exam' })).toBeEnabled();

  page.on('dialog', (dialog) => void dialog.accept());
  await page.getByRole('button', { name: 'Submit Exam' }).click();

  await page.waitForURL(`/exam/${exam.id}/result`);
  await expect(page.getByText('Submitted', { exact: true })).toBeVisible();
  await expect(page.getByText('Exam Submission Status')).toBeVisible();
  await expect(page.getByText('Your exam response has been recorded', { exact: false })).toBeVisible();
});

test('exam list renders without errors for anonymous visitors', async ({ page }) => {
  await page.goto('/exam');

  await expect(page.locator('h1')).toContainText('Exams & Assessments');
  await expect(page.locator('text=Failed to load exam list')).not.toBeVisible();
});
