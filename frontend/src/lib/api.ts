function normalizeBaseUrl(value: string | undefined) {
  if (!value) {
    return '';
  }

  return value.endsWith('/') ? value.slice(0, -1) : value;
}

const configuredApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL;

export const API_BASE_URL = normalizeBaseUrl(configuredApiBaseUrl);

export function getRealtimeBaseUrl() {
  if (API_BASE_URL) {
    return API_BASE_URL;
  }

  if (typeof window !== 'undefined') {
    return window.location.origin;
  }

  return '';
}

export type AuthUser = {
  id: string;
  sid: number;
  name: string;
  phone: string;
  email: string;
  user_group: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type UserRole = 'student' | 'ta' | 'instructor' | 'admin';

export type AdminUserApi = AuthUser;

export type UserRoleUpdatePayload = {
  user_group: UserRole;
};

export type UserProfileUpdatePayload = {
  name: string;
  phone: string;
  email: string;
};

export type PasswordChangePayload = {
  current_password: string;
  new_password: string;
};

export type BulkAdminUserEntry = {
  id: string;
  sid: number;
  name: string;
  phone: string;
  email: string;
  user_group: UserRole;
  ps?: string | null;
  is_active?: boolean;
};

export type BulkAdminUserCreatePayload = {
  users: BulkAdminUserEntry[];
  default_password: string;
  skip_existing?: boolean;
};

export type BulkAdminUserCreateResult = {
  created_count: number;
  skipped_count: number;
  created_users: AdminUserApi[];
  skipped_ids: string[];
};

export type SystemSettingApi = {
  key: string;
  value: string;
  value_type: 'string' | 'number' | 'boolean';
  description: string | null;
  updated_at: string;
};

export type SystemSettingsUpdatePayload = {
  settings: Array<{
    key: string;
    value: string | number | boolean;
  }>;
};

export type CodeSnapshotApi = {
  id: number;
  homework_num: number;
  user_id: string;
  language: string;
  code_text: string;
  snapshot_type: 'auto_save' | 'run' | 'manual_save';
  created_at: string;
};

export type CodeSnapshotCreatePayload = {
  homework_num: number;
  language: string;
  code_text: string;
  snapshot_type?: 'auto_save' | 'run' | 'manual_save';
};

export type HomeworkApi = {
  num: number;
  title: string;
  intro: string;
  deadline: string | null;
  codeName: string;
  filename: string | null;
  ratedatanum: number;
  sec: number;
  sbnum: number;
  starttime: string | null;
  isDetected: boolean;
  vitalSpace: boolean;
  disorderedOutput: boolean;
  isLint: boolean;
  schedule_status: 'upcoming' | 'open' | 'closing_soon' | 'closed';
  can_submit: boolean;
  allowed_languages: string[];
};

export type HomeworkTestCaseApi = {
  name: string;
  input: string;
  expected_output: string;
  score: number;
  is_hidden: boolean;
};

export type HomeworkAdminApi = HomeworkApi & {
  testcases: HomeworkTestCaseApi[];
  lint_week: string | null;
};

export type HomeworkAdminPayload = {
  title: string;
  intro: string;
  deadline?: string | null;
  codeName: string;
  filename?: string | null;
  ratedatanum: number;
  sec: number;
  sbnum: number;
  starttime?: string | null;
  isDetected: boolean;
  vitalSpace: boolean;
  disorderedOutput: boolean;
  isLint: boolean;
  allowed_languages: string[];
  testcases: HomeworkTestCaseApi[];
  lint_week?: string | null;
};

export type NoticeApi = {
  num: number;
  title: string;
  author: string;
  content: string;
  date: string;
  is_pinned: boolean;
  is_published: boolean;
};

export type NoticeAdminPayload = {
  title: string;
  author: string;
  content: string;
  date?: string | null;
  is_pinned: boolean;
  is_published: boolean;
};

export type LectureMaterialApi = {
  id: number;
  title: string;
  description: string;
  url: string;
  is_published: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type LectureMaterialPayload = {
  title: string;
  description: string;
  url: string;
  is_published: boolean;
};

export type SubmissionApi = {
  id: number;
  homework_num: number;
  homework_title: string | null;
  user_id: string;
  submission_mode: string;
  attempt_no: number;
  language: string;
  status: string;
  original_filename: string | null;
  deadline_snapshot: string | null;
  submitted_at: string;
  total_score: number;
  submission_score: number;
  quality_score: number;
  compile_status: string;
  run_status: string;
  grader_summary: string | null;
};

export type StudentDashboardOverviewApi = {
  total_homeworks: number;
  submitted_homeworks: number;
  graded_homeworks: number;
  pending_homeworks: number;
  missing_homeworks: number;
  closing_soon_homeworks: number;
  average_latest_score: number | null;
};

export type StudentDashboardHomeworkItemApi = {
  homework_num: number;
  title: string;
  deadline: string | null;
  starttime: string | null;
  schedule_status: 'upcoming' | 'open' | 'closing_soon' | 'closed';
  can_submit: boolean;
  submission_count: number;
  latest_submission_id: number | null;
  latest_submission_status: string | null;
  latest_submission_at: string | null;
  latest_score: number | null;
  latest_language: string | null;
  remaining_seconds: number | null;
  grader_summary: string | null;
};

export type StudentDashboardApi = {
  generated_at: string;
  overview: StudentDashboardOverviewApi;
  homework_items: StudentDashboardHomeworkItemApi[];
  recent_submissions: SubmissionApi[];
};

export type NotificationApi = {
  id: number;
  kind: string;
  title: string;
  message: string;
  reference_type: string | null;
  reference_id: string | null;
  is_read: boolean;
  created_at: string;
};

export type SubmissionFeedbackGuideApi = {
  rule: string;
  tool: string;
  summary: string;
  description: string;
};

export type SubmissionFeedbackApi = {
  submission_id: number;
  deadline_status: 'upcoming' | 'open' | 'closing_soon' | 'closed';
  deadline_message: string;
  latest_notice: NoticeApi | null;
  hints: string[];
  coding_rule_guides: SubmissionFeedbackGuideApi[];
};

export type AdminDashboardHomeworkMetricApi = {
  homework_num: number;
  title: string;
  submission_rate: number;
  total_students: number;
  submitted_students: number;
  average_latest_score: number | null;
  failed_submission_count: number;
  pending_submission_count: number;
};

export type AdminDashboardFailureMetricApi = {
  failure_type: string;
  count: number;
};

export type AdminDashboardApi = {
  generated_at: string;
  total_homeworks: number;
  active_students: number;
  total_submissions: number;
  queue: {
    queue_size: number;
    queued_submission_ids: number[];
  };
  homework_metrics: AdminDashboardHomeworkMetricApi[];
  failure_metrics: AdminDashboardFailureMetricApi[];
  recent_events: Array<{
    id: number;
    category: string;
    level: string;
    event_type: string;
    message: string;
    submission_id: number | null;
    user_id: string | null;
    request_path: string | null;
    context_json: string | null;
    created_at: string;
  }>;
};

export type PlagiarismRunApi = {
  id: number;
  homework_num: number;
  created_by: string;
  status: string;
  compared_submission_count: number;
  flagged_pair_count: number;
  summary: string | null;
  created_at: string;
};

export type PlagiarismPairApi = {
  id: number;
  run_id: number;
  homework_num: number;
  left_submission_id: number;
  right_submission_id: number;
  left_user_id: string;
  right_user_id: string;
  similarity_score: number;
  status: string;
  summary: string | null;
  left_code: string | null;
  right_code: string | null;
  created_at: string;
};

export type CollabParticipantApi = {
  user_id: string;
  role: string;
  can_edit: boolean;
  joined_at: string;
  left_at: string | null;
};

export type CollabSessionApi = {
  id: number;
  title: string;
  homework_num: number | null;
  mentor_id: string;
  status: string;
  current_code: string;
  participants: CollabParticipantApi[];
  created_at: string;
  closed_at: string | null;
};

export type CollabMessageApi = {
  id: number;
  session_id: number;
  user_id: string;
  content: string;
  created_at: string;
};

export type CollabHistoryApi = {
  session: CollabSessionApi;
  messages: CollabMessageApi[];
  code_snapshots: Array<{
    id: number;
    session_id: number;
    user_id: string | null;
    code_text: string;
    created_at: string;
  }>;
};

export type CollabSessionPayload = {
  title: string;
  homework_num?: number | null;
  initial_code?: string;
  participant_ids?: string[];
};

type ApiRequestOptions = RequestInit & {
  token?: string | null;
};

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}) {
  const { token, headers, body, ...rest } = options;
  const requestHeaders = new Headers(headers);

  if (!requestHeaders.has("Content-Type") && !(body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: requestHeaders,
    body,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String(payload.detail)
        : "Request failed";

    throw new Error(detail);
  }

  return payload as T;
}

export async function loginRequest(id: string, ps: string) {
  return apiRequest<{ access_token: string; token_type: string }>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ id, ps }),
    },
  );
}

export async function registerRequest(payload: {
  id: string;
  sid: number;
  name: string;
  phone: string;
  email: string;
  ps: string;
}) {
  return apiRequest<AuthUser>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCurrentUser(token: string) {
  return apiRequest<AuthUser>("/api/users/me", {
    method: "GET",
    token,
  });
}

export async function updateCurrentUserProfile(
  payload: UserProfileUpdatePayload,
  token: string,
) {
  return apiRequest<AuthUser>('/api/users/me', {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export async function changeCurrentUserPassword(
  payload: PasswordChangePayload,
  token: string,
) {
  return apiRequest<{ message: string }>('/api/auth/change-password', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function getStudentDashboard(token: string) {
  return apiRequest<StudentDashboardApi>('/api/dashboard/me', {
    method: 'GET',
    token,
  });
}

export async function getAdminDashboard(token: string) {
  return apiRequest<AdminDashboardApi>('/api/admin/dashboard', {
    method: 'GET',
    token,
  });
}

export async function getNotifications(token: string) {
  return apiRequest<NotificationApi[]>('/api/notifications', {
    method: 'GET',
    token,
  });
}

export async function markNotificationsRead(
  notificationIds: number[],
  token: string,
) {
  return apiRequest<NotificationApi[]>('/api/notifications/read', {
    method: 'POST',
    token,
    body: JSON.stringify({ notification_ids: notificationIds }),
  });
}

export async function getAdminUsers(
  token: string,
  options?: {
    search?: string;
    role?: UserRole | 'all';
    is_active?: boolean | 'all';
  },
) {
  const params = new URLSearchParams();

  if (options?.search?.trim()) {
    params.set('search', options.search.trim());
  }

  if (options?.role && options.role !== 'all') {
    params.set('role', options.role);
  }

  if (typeof options?.is_active === 'boolean') {
    params.set('is_active', String(options.is_active));
  }

  const query = params.toString();
  return apiRequest<AdminUserApi[]>(`/api/admin/users${query ? `?${query}` : ''}`, {
    method: 'GET',
    token,
  });
}

export async function updateAdminUserRole(
  userId: string,
  payload: UserRoleUpdatePayload,
  token: string,
) {
  return apiRequest<AdminUserApi>(`/api/admin/users/${userId}/role`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateAdminUserStatus(
  userId: string,
  payload: { is_active: boolean },
  token: string,
) {
  return apiRequest<AdminUserApi>(`/api/admin/users/${userId}/status`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export async function resetAdminUserPassword(
  userId: string,
  payload: { new_password: string },
  token: string,
) {
  return apiRequest<AdminUserApi>(`/api/admin/users/${userId}/reset-password`, {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function bulkCreateAdminUsers(
  payload: BulkAdminUserCreatePayload,
  token: string,
) {
  return apiRequest<BulkAdminUserCreateResult>('/api/admin/users/bulk', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function getAdminSettings(
  token: string,
  options?: {
    prefix?: string;
  },
) {
  const params = new URLSearchParams();
  if (options?.prefix?.trim()) {
    params.set('prefix', options.prefix.trim());
  }
  const query = params.toString();
  return apiRequest<SystemSettingApi[]>(
    `/api/admin/settings${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      token,
    },
  );
}

export async function updateAdminSettings(
  payload: SystemSettingsUpdatePayload,
  token: string,
) {
  return apiRequest<SystemSettingApi[]>('/api/admin/settings', {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export async function getHomeworks(
  token?: string | null,
  options?: { limit?: number; offset?: number },
) {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  const query = params.toString();

  return apiRequest<HomeworkApi[]>(`/api/homework${query ? `?${query}` : ""}`, {
    method: "GET",
    token,
  });
}

export async function getHomework(num: number, token?: string | null) {
  return apiRequest<HomeworkApi>(`/api/homework/${num}`, {
    method: "GET",
    token,
  });
}

export async function getAdminHomeworks(
  token: string,
  options?: { limit?: number; offset?: number },
) {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  const query = params.toString();

  return apiRequest<HomeworkAdminApi[]>(
    `/api/admin/homeworks${query ? `?${query}` : ""}`,
    {
      method: "GET",
      token,
    },
  );
}

export async function getAdminHomework(num: number, token: string) {
  return apiRequest<HomeworkAdminApi>(`/api/admin/homeworks/${num}`, {
    method: "GET",
    token,
  });
}

export async function createAdminHomework(
  payload: HomeworkAdminPayload,
  token: string,
) {
  return apiRequest<HomeworkAdminApi>("/api/admin/homeworks", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateAdminHomework(
  homeworkNum: number,
  payload: HomeworkAdminPayload,
  token: string,
) {
  return apiRequest<HomeworkAdminApi>(`/api/admin/homeworks/${homeworkNum}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function deleteAdminHomework(homeworkNum: number, token: string) {
  return apiRequest<{ message: string }>(`/api/admin/homeworks/${homeworkNum}`, {
    method: "DELETE",
    token,
  });
}

export async function getSubmissionFeedback(
  submissionId: number,
  token: string,
) {
  return apiRequest<SubmissionFeedbackApi>(`/api/submissions/${submissionId}/feedback`, {
    method: 'GET',
    token,
  });
}

export async function getNotices(token?: string | null) {
  return apiRequest<NoticeApi[]>("/api/notice", {
    method: "GET",
    token,
  });
}

export async function getNotice(num: number, token?: string | null) {
  return apiRequest<NoticeApi>(`/api/notice/${num}`, {
    method: "GET",
    token,
  });
}

export async function getMaterials(token?: string | null) {
  return apiRequest<LectureMaterialApi[]>('/api/materials', {
    method: 'GET',
    token,
  });
}

export async function getAdminNotices(token: string) {
  return apiRequest<NoticeApi[]>("/api/admin/notices", {
    method: "GET",
    token,
  });
}

export async function createAdminMaterial(
  payload: LectureMaterialPayload,
  token: string,
) {
  return apiRequest<LectureMaterialApi>('/api/admin/materials', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function createAdminNotice(
  payload: NoticeAdminPayload,
  token: string,
) {
  return apiRequest<NoticeApi>("/api/admin/notices", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateAdminNotice(
  noticeNum: number,
  payload: NoticeAdminPayload,
  token: string,
) {
  return apiRequest<NoticeApi>(`/api/admin/notices/${noticeNum}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function deleteAdminNotice(noticeNum: number, token: string) {
  return apiRequest<{ message: string }>(`/api/admin/notices/${noticeNum}`, {
    method: "DELETE",
    token,
  });
}

export async function runHomeworkPlagiarismScan(
  homeworkNum: number,
  token: string,
) {
  return apiRequest<PlagiarismRunApi>(
    `/api/admin/homeworks/${homeworkNum}/plagiarism/run`,
    {
      method: 'POST',
      token,
    },
  );
}

export async function getPlagiarismPairs(
  token: string,
  options?: {
    homework_num?: number;
  },
) {
  const params = new URLSearchParams();
  if (options?.homework_num) {
    params.set('homework_num', String(options.homework_num));
  }
  const query = params.toString();
  return apiRequest<PlagiarismPairApi[]>(
    `/api/admin/plagiarism/pairs${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      token,
    },
  );
}

export async function getPlagiarismPairDetail(pairId: number, token: string) {
  return apiRequest<PlagiarismPairApi>(`/api/admin/plagiarism/pairs/${pairId}`, {
    method: 'GET',
    token,
  });
}

export async function saveCodeSnapshot(
  payload: CodeSnapshotCreatePayload,
  token: string,
) {
  return apiRequest<CodeSnapshotApi>('/api/submissions/snapshots', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function getLatestSnapshot(homeworkNum: number, token: string) {
  return apiRequest<CodeSnapshotApi | null>(
    `/api/homeworks/${homeworkNum}/snapshots/latest`,
    {
      method: 'GET',
      token,
    },
  );
}

export async function getStudentSnapshots(
  homeworkNum: number,
  userId: string,
  token: string,
) {
  return apiRequest<CodeSnapshotApi[]>(
    `/api/admin/homeworks/${homeworkNum}/snapshots/${userId}`,
    {
      method: 'GET',
      token,
    },
  );
}

export async function createSubmission(
  payload: {
    homework_num: number;
    language: string;
    code_text: string;
    original_filename?: string | null;
  },
  token: string,
) {
  return apiRequest<SubmissionApi>("/api/submissions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function getMySubmissions(
  token: string,
  homeworkNum?: number,
) {
  const query = homeworkNum ? `?homework_num=${homeworkNum}` : "";
  return apiRequest<SubmissionApi[]>(`/api/submissions${query}`, {
    method: "GET",
    token,
  });
}

export async function getSubmission(
  submissionId: number,
  token: string,
) {
  return apiRequest<SubmissionApi>(`/api/submissions/${submissionId}`, {
    method: "GET",
    token,
  });
}

export async function getCollabSessions(token: string) {
  return apiRequest<CollabSessionApi[]>('/api/collab/sessions', {
    method: 'GET',
    token,
  });
}

export async function createCollabSession(
  payload: CollabSessionPayload,
  token: string,
) {
  return apiRequest<CollabSessionApi>('/api/collab/sessions', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function joinCollabSession(sessionId: number, token: string) {
  return apiRequest<CollabSessionApi>(`/api/collab/sessions/${sessionId}/join`, {
    method: 'POST',
    token,
  });
}

export async function updateCollabCode(
  sessionId: number,
  code: string,
  token: string,
) {
  return apiRequest<CollabSessionApi>(`/api/collab/sessions/${sessionId}/code`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ code }),
  });
}

export async function postCollabMessage(
  sessionId: number,
  content: string,
  token: string,
) {
  return apiRequest<CollabMessageApi>(`/api/collab/sessions/${sessionId}/messages`, {
    method: 'POST',
    token,
    body: JSON.stringify({ content }),
  });
}

export async function closeCollabSession(sessionId: number, token: string) {
  return apiRequest<CollabSessionApi>(`/api/collab/sessions/${sessionId}/close`, {
    method: 'POST',
    token,
  });
}

export async function getCollabHistory(sessionId: number, token: string) {
  return apiRequest<CollabHistoryApi>(`/api/collab/sessions/${sessionId}/history`, {
    method: 'GET',
    token,
  });
}
