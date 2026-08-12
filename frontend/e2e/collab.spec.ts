import { expect, test } from '@playwright/test';

import {
  authenticatePage,
  createCollabSessionViaAdminApi,
  registerUserViaApi,
  uniqueUser,
} from './helpers';

test('participants_see_shared_code_updates', async ({ browser, request }) => {
  const firstUser = uniqueUser('collab-a');
  const secondUser = uniqueUser('collab-b');
  await registerUserViaApi(request, firstUser);
  await registerUserViaApi(request, secondUser);

  const session = await createCollabSessionViaAdminApi(request, {
    title: `Realtime Session ${Date.now()}`,
    initial_code: "print('ready')\n",
  });

  const firstContext = await browser.newContext();
  const secondContext = await browser.newContext();
  const firstPage = await firstContext.newPage();
  const secondPage = await secondContext.newPage();

  await authenticatePage(firstPage, request, {
    id: firstUser.id,
    password: firstUser.password,
  });
  await authenticatePage(secondPage, request, {
    id: secondUser.id,
    password: secondUser.password,
  });

  await firstPage.goto('/collab');
  await secondPage.goto('/collab');

  await firstPage.getByRole('button', { name: new RegExp(session.title) }).click();
  await firstPage.getByRole('button', { name: '선택한 세션 참가' }).click();
  const firstEditor = firstPage.getByTestId('collab-code-editor');
  await expect(firstEditor).toBeEditable();

  await secondPage.getByRole('button', { name: new RegExp(session.title) }).click();
  await secondPage.getByRole('button', { name: '선택한 세션 참가' }).click();
  const secondEditor = secondPage.getByTestId('collab-code-editor');
  await expect(secondEditor).toBeEditable();

  const syncedCode = "print('sync works')\nprint('shared state')\n";
  await firstEditor.fill(syncedCode);
  await expect(secondEditor).toHaveValue(syncedCode);

  await secondPage.getByPlaceholder('Type a message').fill('hello from second participant');
  await secondPage.getByRole('button', { name: '전송' }).click();
  await expect(firstPage.getByTestId('collab-chat-log')).toContainText(
    'hello from second participant',
  );

  await firstContext.close();
  await secondContext.close();
});
