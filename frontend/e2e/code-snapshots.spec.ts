import { expect, test } from '@playwright/test';

import {
  BACKEND_BASE_URL,
  adminUser,
  authenticatePage,
  createHomeworkViaAdminApi,
  loginViaApi,
  registerUserViaApi,
  relativeDate,
  uniqueUser,
} from './helpers';

test('student_code_is_autosaved_and_restored', async ({ page, request }) => {
  const user = uniqueUser('autosave');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Autosave Homework ${Date.now()}`,
    intro: 'Autosave test intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'autosave-test',
    allowed_languages: ['python'],
    testcases: [],
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  
  // 1. Navigate to homework page
  await page.goto(`/homework/${homework.num}`);
  
  // 2. Type code in the editor
  const testCode = "print('Hello World')";
  const editor = page.locator('#code');
  await editor.pressSequentially(testCode, { delay: 30 });
  
  // 3. Verify "Saved" indicator appears
  await expect(page.getByText('Saved')).toBeVisible({ timeout: 15000 });
  
  // 4. Refresh the page
  await page.reload();
  
  // 5. Verify the code is restored in the editor
  await expect(editor).toHaveValue(testCode);
  await expect(page.getByText('Saved')).toBeVisible();
});

test('admin_can_view_student_snapshot_timeline', async ({ page, request }) => {
  const user = uniqueUser('snap-admin');
  await registerUserViaApi(request, user);
  const homework = await createHomeworkViaAdminApi(request, {
    title: `Admin Snapshot Homework ${Date.now()}`,
    intro: 'Admin snapshot intro',
    starttime: relativeDate(-1),
    deadline: relativeDate(2),
    codeName: 'snap-admin',
    allowed_languages: ['python'],
    testcases: [],
  });

  await authenticatePage(page, request, { id: user.id, password: user.password });
  
  // 1. Student types version 1
  await page.goto(`/homework/${homework.num}`);
  const editor = page.locator('#code');
  await editor.fill("print('v1')");
  await expect(page.getByText('Saved')).toBeVisible({ timeout: 15000 });
  
  // 2. Student types version 2 (Must be different content)
  // Wait longer to avoid rapid collision and clear debounce
  await page.waitForTimeout(5000);
  await editor.fill("print('version two is different')");

  // Autosave is debounced, so wait until the second snapshot is actually
  // persisted before leaving the page.
  const adminSession = await loginViaApi(request, adminUser);
  await expect
    .poll(async () => {
      const response = await request.get(
        `${BACKEND_BASE_URL}/api/admin/homeworks/${homework.num}/snapshots/${user.id}`,
        { headers: { Authorization: `Bearer ${adminSession.token}` } },
      );
      if (!response.ok()) return 0;
      const snapshots = (await response.json()) as unknown[];
      return Array.isArray(snapshots) ? snapshots.length : 0;
    }, { timeout: 20_000 })
    .toBeGreaterThanOrEqual(2);

  // 3. Login as Admin and check timeline
  await authenticatePage(page, request, adminUser);
  await page.goto(`/admin/snapshots/${homework.num}/${user.id}`);
  
  // 4. Verify timeline has 2 snapshots
  await expect(page.getByText('Snapshot Timeline')).toBeVisible();
  const snapshotButtons = page.locator('aside button');
  await expect(snapshotButtons).toHaveCount(2, { timeout: 10000 });
  
  // 5. Check Monaco Diff Editor content
  await snapshotButtons.nth(0).click(); // Newest (v2)
  await expect(page.locator('main')).toContainText("version two is different", { timeout: 10000 });
  
  await snapshotButtons.nth(1).click(); // Older (v1)
  await expect(page.locator('main')).toContainText("v1", { timeout: 10000 });
});
