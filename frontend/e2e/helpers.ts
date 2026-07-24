import { expect, type APIRequestContext, type Page } from '@playwright/test';

const STORAGE_KEY = 'neoespa.auth.session';
export const BACKEND_BASE_URL = 'http://127.0.0.1:8101';

export type TestUser = {
  id: string;
  sid: number;
  name: string;
  phone: string;
  email: string;
  password: string;
};

export const adminUser = {
  id: 'admin',
  password: 'pllab818',
};

export function relativeDate(offsetDays: number, offsetHours = 0) {
  const value = new Date(Date.now() + (offsetDays * 24 + offsetHours) * 60 * 60 * 1000);
  return value.toISOString().slice(0, 19).replace('T', ' ');
}

export function uniqueUser(prefix: string): TestUser {
  const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  return {
    id: `${prefix}-${suffix}`,
    sid: Number(`20${suffix.slice(-6)}`),
    name: `${prefix} User`,
    phone: '010-1234-5678',
    email: `${prefix}-${suffix}@example.com`,
    password: 'student-pass',
  };
}

export async function registerUserViaApi(
  request: APIRequestContext,
  user: TestUser,
) {
  const response = await request.post(`${BACKEND_BASE_URL}/api/auth/register`, {
    data: {
      id: user.id,
      sid: user.sid,
      ps: user.password,
      name: user.name,
      phone: user.phone,
      email: user.email,
    },
  });
  expect(response.ok()).toBeTruthy();
}

export async function loginViaApi(
  request: APIRequestContext,
  credentials: { id: string; password: string },
) {
  const loginResponse = await request.post(`${BACKEND_BASE_URL}/api/auth/login`, {
    data: {
      id: credentials.id,
      ps: credentials.password,
    },
  });
  expect(loginResponse.ok()).toBeTruthy();
  const authPayload = (await loginResponse.json()) as {
    access_token: string;
  };
  const token = authPayload.access_token;
  const meResponse = await request.get(`${BACKEND_BASE_URL}/api/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  expect(meResponse.ok()).toBeTruthy();
  const user = await meResponse.json();
  return { token, user };
}

export async function authenticatePage(
  page: Page,
  request: APIRequestContext,
  credentials: { id: string; password: string },
) {
  const session = await loginViaApi(request, credentials);
  await page.addInitScript(
    ({ storageKey, storageValue }) => {
      window.localStorage.setItem(storageKey, JSON.stringify(storageValue));
    },
    {
      storageKey: STORAGE_KEY,
      storageValue: session,
    },
  );
  return session;
}

export async function loginViaUi(page: Page, credentials: { id: string; password: string }) {
  await page.goto('/login');
  await page.getByLabel('User ID').fill(credentials.id);
  await page.getByLabel('Password').fill(credentials.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
}

export async function registerViaUi(page: Page, user: TestUser) {
  await page.goto('/register');
  await page.getByLabel('Full Name').fill(user.name);
  await page.getByLabel('User ID').fill(user.id);
  await page.getByLabel('Student ID').fill(String(user.sid));
  await page.getByLabel('Email').fill(user.email);
  await page.getByLabel('Phone').fill(user.phone);
  await page.getByLabel('Password', { exact: true }).fill(user.password);
  await page.getByLabel('Confirm', { exact: true }).fill(user.password);
  await page.getByRole('button', { name: 'Create Student Account' }).click();
}

export async function createHomeworkViaAdminApi(
  request: APIRequestContext,
  payload: Record<string, unknown>,
) {
  const session = await loginViaApi(request, adminUser);
  const response = await request.post(`${BACKEND_BASE_URL}/api/admin/homeworks`, {
    data: payload,
    headers: {
      Authorization: `Bearer ${session.token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function updateHomeworkViaAdminApi(
  request: APIRequestContext,
  homeworkNum: number,
  payload: Record<string, unknown>,
) {
  const session = await loginViaApi(request, adminUser);
  const response = await request.patch(
    `${BACKEND_BASE_URL}/api/admin/homeworks/${homeworkNum}`,
    {
      data: payload,
      headers: {
        Authorization: `Bearer ${session.token}`,
      },
    },
  );
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function createExamViaAdminApi(
  request: APIRequestContext,
  payload: Record<string, unknown>,
) {
  const session = await loginViaApi(request, adminUser);
  const response = await request.post(`${BACKEND_BASE_URL}/api/admin/exams`, {
    data: payload,
    headers: {
      Authorization: `Bearer ${session.token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function createNoticeViaAdminApi(
  request: APIRequestContext,
  payload: Record<string, unknown>,
) {
  const session = await loginViaApi(request, adminUser);
  const response = await request.post(`${BACKEND_BASE_URL}/api/admin/notices`, {
    data: payload,
    headers: {
      Authorization: `Bearer ${session.token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function createSubmissionViaApi(
  request: APIRequestContext,
  token: string,
  payload: Record<string, unknown>,
) {
  const response = await request.post(`${BACKEND_BASE_URL}/api/submissions`, {
    data: payload,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function gradeSubmissionViaApi(
  request: APIRequestContext,
  submissionId: number,
) {
  const session = await loginViaApi(request, adminUser);
  const response = await request.post(
    `${BACKEND_BASE_URL}/api/admin/submissions/${submissionId}/grade`,
    {
      headers: {
        Authorization: `Bearer ${session.token}`,
      },
    },
  );
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function createCollabSessionViaAdminApi(
  request: APIRequestContext,
  payload: Record<string, unknown>,
) {
  const session = await loginViaApi(request, adminUser);
  const response = await request.post(`${BACKEND_BASE_URL}/api/collab/sessions`, {
    data: payload,
    headers: {
      Authorization: `Bearer ${session.token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}
