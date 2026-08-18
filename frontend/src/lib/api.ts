function normalizeBaseUrl(value: string | undefined) {
  if (!value) {
    return '';
  }

  return value.endsWith('/') ? value.slice(0, -1) : value;
}

const configuredApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL;

export const API_BASE_URL = normalizeBaseUrl(configuredApiBaseUrl);
export const COOKIE_SESSION_TOKEN = '__neoespa_cookie_session__';

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
  capabilities: string[];
};

export type UserRole =
  | 'student'
  | 'viewer'
  | 'support'
  | 'judge_operator'
  | 'reviewer'
  | 'problem_setter'
  | 'ta'
  | 'instructor'
  | 'admin'
  | 'super_admin';

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

export type MaterialCommentApi = {
  id: number;
  material_id: number;
  user_id: string;
  user_name: string | null;
  content: string;
  created_at: string;
};

export type LectureMaterialApi = {
  id: number;
  title: string;
  description: string;
  url: string;
  content: string | null;
  attachment_name: string | null;
  attachment_relpath: string | null;
  comments: MaterialCommentApi[];
  is_published: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type LectureMaterialPayload = {
  title: string;
  description: string;
  url: string;
  content?: string | null;
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
  compile_log: string | null;
  run_status: string;
  grader_summary: string | null;
  manual_total_score: number | null;
  score_adjusted_by: string | null;
  score_adjusted_at: string | null;
  score_adjustment_note: string | null;
  problem_revision_id: number | null;
  selected_grading_run_id: number | null;
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
  /** 404를 오류가 아닌 "결과 없음"(null)으로 처리한다. */
  allowNotFound?: boolean;
};

export type ApiFieldError = {
  field: string;
  message: string;
  type?: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null,
    readonly fieldErrors: ApiFieldError[],
    readonly requestId: string | null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}) {
  const { token, headers, body, allowNotFound, ...rest } = options;
  const requestHeaders = new Headers(headers);

  if (!requestHeaders.has("Content-Type") && !(body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (token) {
    if (token !== COOKIE_SESSION_TOKEN) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    credentials: 'include',
    headers: requestHeaders,
    body,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    if (allowNotFound && response.status === 404) {
      return null as T;
    }

    const envelope =
      typeof payload === 'object' && payload !== null
        ? (payload as Record<string, unknown>)
        : null;
    const fieldErrors = Array.isArray(envelope?.field_errors)
      ? (envelope.field_errors as ApiFieldError[])
      : [];
    const message =
      typeof envelope?.message === 'string'
        ? envelope.message
        : typeof envelope?.detail === 'string'
          ? envelope.detail
          : typeof payload === 'string' && payload
            ? payload
            : 'Request failed';
    const displayMessage =
      fieldErrors.length > 0
        ? `${message}: ${fieldErrors.map((item) => `${item.field} ${item.message}`).join(', ')}`
        : message;

    if (response.status === 401 && token && typeof window !== 'undefined') {
      window.dispatchEvent(new Event('neoespa:unauthorized'));
    }

    throw new ApiError(
      displayMessage,
      response.status,
      typeof envelope?.code === 'string' ? envelope.code : null,
      fieldErrors,
      typeof envelope?.request_id === 'string' ? envelope.request_id : null,
    );
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

export async function logoutRequest() {
  return apiRequest<void>("/api/auth/logout", { method: "POST" });
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

export type ExamApi = {
  id: number;
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
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ExamSubmissionApi = {
  id: number;
  exam_id: number;
  user_id: string;
  language: string;
  status: string;
  original_filename: string | null;
  submitted_at: string;
};

export async function getExams(token?: string | null) {
  return apiRequest<ExamApi[]>('/api/exams', {
    method: 'GET',
    token,
  });
}

export async function getExam(examId: number, token?: string | null) {
  return apiRequest<ExamApi>(`/api/exams/${examId}`, {
    method: 'GET',
    token,
  });
}

export async function getExamSubmissions(examId: number, token: string) {
  return apiRequest<ExamSubmissionApi[]>(`/api/exams/${examId}/submissions`, {
    method: 'GET',
    token,
  });
}

export async function submitExam(
  examId: number,
  payload: {
    language: string;
    code_text: string;
    original_filename?: string | null;
  },
  token: string,
) {
  return apiRequest<ExamSubmissionApi>(`/api/exams/${examId}/submit`, {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function addMaterialComment(
  materialId: number,
  content: string,
  token: string,
) {
  return apiRequest<LectureMaterialApi>(`/api/materials/${materialId}/comments`, {
    method: 'POST',
    token,
    body: JSON.stringify({ content }),
  });
}

export async function uploadMaterialAttachment(
  materialId: number,
  file: File,
  token: string,
) {
  const formData = new FormData();
  formData.append('upload', file);
  return apiRequest<LectureMaterialApi>(`/api/admin/materials/${materialId}/attachment`, {
    method: 'POST',
    token,
    body: formData,
  });
}

export function getMaterialAttachmentUrl(materialId: number) {
  return `${API_BASE_URL}/api/materials/${materialId}/attachment`;
}

/**
 * 인증이 필요한 첨부/내보내기 응답을 파일로 저장한다.
 * 토큰을 헤더로 실어야 하므로 단순 링크로는 내려받을 수 없다.
 */
async function apiDownload(
  path: string,
  token: string,
  fallbackFilename: string,
) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      const payload = await response.json();
      throw new Error(
        typeof payload === 'object' && payload !== null && 'detail' in payload
          ? String(payload.detail)
          : 'Download failed',
      );
    }
    throw new Error('Download failed');
  }

  const disposition = response.headers.get('content-disposition') ?? '';
  const matched = /filename="?([^"]+)"?/.exec(disposition);
  const filename = matched?.[1] ?? fallbackFilename;
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);

  try {
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }

  return filename;
}

/* -------------------------------------------------------------------------
 * 채점 운영 (채점 지표 · 워커 · 작업 큐)
 * ---------------------------------------------------------------------- */

export type GradingMetricsApi = {
  queued_jobs: number;
  running_jobs: number;
  failed_jobs: number;
  dead_letter_jobs: number;
  average_queue_wait_ms: number;
  workers_online: number;
  workers_offline: number;
  worker_failure_rate: number;
  verdict_counts: Record<string, number>;
  problem_error_counts: Record<string, number>;
};

export type JudgeJobApi = {
  id: number;
  job_type: string;
  status: string;
  priority: number;
  progress: number;
  attempt_count: number;
  max_attempts: number;
  lease_owner: string | null;
  lease_generation: number;
  parent_job_id: number | null;
  problem_id: number | null;
  revision_id: number | null;
  submission_id: number | null;
  result_json: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type JudgeWorkerApi = {
  worker_id: string;
  status: string;
  concurrency: number;
  current_job_id: number | null;
  capabilities_json: string;
  last_error: string | null;
  heartbeat_at: string;
};

export async function getGradingMetrics(token: string) {
  return apiRequest<GradingMetricsApi>('/api/admin/grading/metrics', {
    method: 'GET',
    token,
  });
}

export async function getGradingIncidents(
  token: string,
  options?: { problem_id?: number; worker_id?: string; limit?: number },
) {
  const params = new URLSearchParams();
  if (options?.problem_id) params.set('problem_id', String(options.problem_id));
  if (options?.worker_id) params.set('worker_id', options.worker_id);
  if (options?.limit) params.set('limit', String(options.limit));
  const query = params.toString();

  return apiRequest<JudgeJobApi[]>(
    `/api/admin/grading/incidents${query ? `?${query}` : ''}`,
    { method: 'GET', token },
  );
}

/** 대기 중인 채점 작업이 없으면 백엔드가 404를 돌려주므로 null로 처리한다. */
export async function processNextGradingJob(token: string) {
  return apiRequest<SubmissionApi | null>('/api/admin/grading/process-next', {
    method: 'POST',
    token,
    allowNotFound: true,
  });
}

export async function getJudgeJobs(
  token: string,
  options?: {
    status?: string;
    job_type?: string;
    problem_id?: number;
    worker_id?: string;
    limit?: number;
  },
) {
  const params = new URLSearchParams();
  if (options?.status) params.set('status', options.status);
  if (options?.job_type) params.set('job_type', options.job_type);
  if (options?.problem_id) params.set('problem_id', String(options.problem_id));
  if (options?.worker_id) params.set('worker_id', options.worker_id);
  if (options?.limit) params.set('limit', String(options.limit));
  const query = params.toString();

  return apiRequest<JudgeJobApi[]>(
    `/api/admin/judge-jobs${query ? `?${query}` : ''}`,
    { method: 'GET', token },
  );
}

export async function getJudgeWorkers(token: string) {
  return apiRequest<JudgeWorkerApi[]>('/api/admin/judge-workers', {
    method: 'GET',
    token,
  });
}

export async function setJudgeWorkerState(
  workerId: string,
  action: 'enable' | 'disable' | 'drain',
  token: string,
) {
  return apiRequest<JudgeWorkerApi>(
    `/api/admin/judge-workers/${encodeURIComponent(workerId)}/${action}`,
    { method: 'POST', token },
  );
}

/* -------------------------------------------------------------------------
 * 제출물 채점 조작
 * ---------------------------------------------------------------------- */

export async function queueSubmissionForGrading(
  submissionId: number,
  token: string,
) {
  return apiRequest<SubmissionApi>(
    `/api/admin/submissions/${submissionId}/queue`,
    { method: 'POST', token },
  );
}

export async function requeueSubmissionForGrading(
  submissionId: number,
  token: string,
) {
  return apiRequest<SubmissionApi>(
    `/api/admin/submissions/${submissionId}/requeue`,
    { method: 'POST', token },
  );
}

export async function gradeSubmissionNow(submissionId: number, token: string) {
  return apiRequest<SubmissionApi>(
    `/api/admin/submissions/${submissionId}/grade`,
    { method: 'POST', token },
  );
}

export async function adjustSubmissionScore(
  submissionId: number,
  payload: { manual_total_score: number; adjustment_note?: string | null },
  token: string,
) {
  return apiRequest<SubmissionApi>(
    `/api/admin/submissions/${submissionId}/score`,
    { method: 'PATCH', token, body: JSON.stringify(payload) },
  );
}

/* -------------------------------------------------------------------------
 * 재채점 작업
 * ---------------------------------------------------------------------- */

export type RejudgeScopePayload = {
  homework_num?: number | null;
  user_id?: string | null;
  submission_ids?: number[];
  statuses?: string[];
  verdicts?: string[];
  submitted_after?: string | null;
  submitted_before?: string | null;
};

export type RejudgePreviewApi = {
  target_count: number;
  submission_ids: number[];
  truncated: boolean;
};

export async function previewRejudge(
  payload: RejudgeScopePayload,
  token: string,
) {
  return apiRequest<RejudgePreviewApi>('/api/admin/rejudge-jobs/preview', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function createRejudgeJob(
  payload: RejudgeScopePayload & { reason: string; idempotency_key: string },
  token: string,
) {
  return apiRequest<JudgeJobApi>('/api/admin/rejudge-jobs', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function getRejudgeJobs(token: string, limit?: number) {
  const query = limit ? `?limit=${limit}` : '';
  return apiRequest<JudgeJobApi[]>(`/api/admin/rejudge-jobs${query}`, {
    method: 'GET',
    token,
  });
}

export async function cancelRejudgeJob(jobId: number, token: string) {
  return apiRequest<JudgeJobApi>(`/api/admin/rejudge-jobs/${jobId}/cancel`, {
    method: 'POST',
    token,
  });
}

export async function retryFailedRejudgeJob(jobId: number, token: string) {
  return apiRequest<JudgeJobApi>(
    `/api/admin/rejudge-jobs/${jobId}/retry-failed`,
    { method: 'POST', token },
  );
}

/* -------------------------------------------------------------------------
 * 운영 로그 (감사 로그 · 시스템 이벤트)
 * ---------------------------------------------------------------------- */

export type AuditLogApi = {
  id: number;
  actor_user_id: string | null;
  action_type: string;
  target_type: string;
  target_id: string | null;
  result: string;
  request_id: string | null;
  job_id: number | null;
  payload_json: string | null;
  before_json: string | null;
  after_json: string | null;
  created_at: string;
};

export type SystemEventApi = {
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
};

export async function getAuditLogs(
  token: string,
  options?: {
    actor_user_id?: string;
    action_type?: string;
    target_type?: string;
    result?: string;
    limit?: number;
  },
) {
  const params = new URLSearchParams();
  if (options?.actor_user_id?.trim()) {
    params.set('actor_user_id', options.actor_user_id.trim());
  }
  if (options?.action_type?.trim()) {
    params.set('action_type', options.action_type.trim());
  }
  if (options?.target_type?.trim()) {
    params.set('target_type', options.target_type.trim());
  }
  if (options?.result?.trim()) params.set('result', options.result.trim());
  if (options?.limit) params.set('limit', String(options.limit));
  const query = params.toString();

  return apiRequest<AuditLogApi[]>(
    `/api/admin/audit-logs${query ? `?${query}` : ''}`,
    { method: 'GET', token },
  );
}

export async function getSystemEvents(
  token: string,
  options?: { category?: string },
) {
  const params = new URLSearchParams();
  if (options?.category?.trim()) {
    params.set('category', options.category.trim());
  }
  const query = params.toString();

  return apiRequest<SystemEventApi[]>(
    `/api/admin/observability/events${query ? `?${query}` : ''}`,
    { method: 'GET', token },
  );
}

/* -------------------------------------------------------------------------
 * 역할 권한
 * ---------------------------------------------------------------------- */

export type RoleCapabilitiesApi = {
  role_name: string;
  capabilities: string[];
};

/**
 * 백엔드 authorization_service.DEFAULT_ROLE_CAPABILITIES 의 권한 이름 목록.
 * 권한 목록 조회 API가 없어 화면에서 선택지를 제공하기 위해 둔다. 서버가
 * 여기에 없는 권한을 돌려주면 화면에서 함께 표시한다.
 */
export const KNOWN_CAPABILITIES = [
  'problem:create',
  'problem:edit',
  'problem:review',
  'problem:publish',
  'problem:data.read',
  'submission:rejudge',
  'judge:operate',
  'homework:manage',
  'grading:manual',
  'content:manage',
  'exam:manage',
  'plagiarism:operate',
  'observability:read',
  'collaboration:manage',
  'audit:read',
  'user:manage',
  'settings:manage',
] as const;

/**
 * 초대로 부여할 수 있는 역할.
 * 백엔드 admin_invitation_service.ADMIN_INVITABLE_ROLES 와 일치해야 한다.
 * (instructor·ta 는 초대 대상이 아니며 사용자 관리에서 역할을 바꿔 부여한다.)
 */
export const ADMIN_INVITABLE_ROLES = [
  'admin',
  'problem_setter',
  'reviewer',
  'judge_operator',
  'support',
  'viewer',
] as const;

export const MANAGED_ROLES = [
  'instructor',
  'ta',
  'problem_setter',
  'reviewer',
  'judge_operator',
  'support',
  'viewer',
  'student',
] as const;

export async function getRoleCapabilities(roleName: string, token: string) {
  return apiRequest<RoleCapabilitiesApi>(
    `/api/admin/roles/${encodeURIComponent(roleName)}/capabilities`,
    { method: 'GET', token },
  );
}

export async function updateRoleCapabilities(
  roleName: string,
  capabilities: string[],
  token: string,
) {
  return apiRequest<RoleCapabilitiesApi>(
    `/api/admin/roles/${encodeURIComponent(roleName)}/capabilities`,
    { method: 'PUT', token, body: JSON.stringify({ capabilities }) },
  );
}

/* -------------------------------------------------------------------------
 * 표절 검사 실행 이력 · 시스템 설정 롤백
 * ---------------------------------------------------------------------- */

export async function getPlagiarismRuns(token: string) {
  return apiRequest<PlagiarismRunApi[]>('/api/admin/plagiarism/runs', {
    method: 'GET',
    token,
  });
}

export async function rollbackAdminSetting(key: string, token: string) {
  return apiRequest<SystemSettingApi>(
    `/api/admin/settings/${encodeURIComponent(key)}/rollback`,
    { method: 'POST', token },
  );
}

/* -------------------------------------------------------------------------
 * 과제 성적/제출물 내보내기 · 과제 가져오기
 * ---------------------------------------------------------------------- */

export async function downloadHomeworkGrades(
  homeworkNum: number,
  token: string,
) {
  return apiDownload(
    `/api/admin/homeworks/${homeworkNum}/grades/export`,
    token,
    `homework_${homeworkNum}_grades.csv`,
  );
}

export async function downloadHomeworkSubmissionArchive(
  homeworkNum: number,
  token: string,
) {
  return apiDownload(
    `/api/admin/homeworks/${homeworkNum}/submissions/archive`,
    token,
    `homework_${homeworkNum}_latest_submissions.zip`,
  );
}

export type HomeworkImportPayload = {
  title: string;
  intro: string;
  codeName: string;
  isLint: boolean;
  problemFile: File;
  inputZip: File;
  outputZip: File;
  deadline?: string | null;
  starttime?: string | null;
  lintWeek?: string | null;
  allowedLanguages?: string[];
};

export async function importAdminHomework(
  payload: HomeworkImportPayload,
  token: string,
) {
  const formData = new FormData();
  formData.append('title', payload.title);
  formData.append('intro', payload.intro);
  formData.append('codeName', payload.codeName);
  formData.append('isLint', String(payload.isLint));
  formData.append('problem_file', payload.problemFile);
  formData.append('input_zip', payload.inputZip);
  formData.append('output_zip', payload.outputZip);
  formData.append(
    'allowed_languages',
    JSON.stringify(payload.allowedLanguages ?? []),
  );
  if (payload.deadline) formData.append('deadline', payload.deadline);
  if (payload.starttime) formData.append('starttime', payload.starttime);
  if (payload.lintWeek) formData.append('lint_week', payload.lintWeek);

  return apiRequest<HomeworkAdminApi>('/api/admin/homeworks/import', {
    method: 'POST',
    token,
    body: formData,
  });
}

/* -------------------------------------------------------------------------
 * 분석 데이터 활용 동의
 * ---------------------------------------------------------------------- */

export type AnalyticsConsentApi = {
  id: number;
  user_id: string;
  purpose: string;
  scopes: string[];
  granted: boolean;
  policy_version: string;
  created_at: string;
};

export type AnalyticsConsentCreatePayload = {
  purpose: string;
  scopes: string[];
  granted: boolean;
  policy_version: string;
};

/* -------------------------------------------------------------------------
 * 관리자 인증 (재인증 · 초대 · 최초 부트스트랩)
 * ---------------------------------------------------------------------- */

export type AuthAssuranceApi = {
  mfa_required: boolean;
  mfa_enrolled: boolean;
  mfa_method: string | null;
};

export type AdminInvitationIssuedApi = {
  id: number;
  email: string;
  role_name: string;
  token: string;
  expires_at: string;
};

export async function getAuthAssurance(token: string) {
  return apiRequest<AuthAssuranceApi>('/api/auth/assurance', {
    method: 'GET',
    token,
  });
}

/**
 * 민감한 관리 작업(초대 발급, 역할 권한 변경 등)에 필요한 재인증.
 * 응답으로 step-up 정보가 담긴 새 access token 을 받는다.
 */
export async function stepUpRequest(password: string, token: string) {
  return apiRequest<{ access_token: string; token_type: string }>(
    '/api/auth/step-up',
    { method: 'POST', token, body: JSON.stringify({ password }) },
  );
}

export async function createAdminInvitation(
  payload: { email: string; role_name: string; ttl_minutes?: number },
  token: string,
) {
  return apiRequest<AdminInvitationIssuedApi>('/api/admin-auth/invitations', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function acceptAdminInvitation(payload: {
  token: string;
  id: string;
  sid: number;
  name: string;
  phone: string;
  password: string;
}) {
  return apiRequest<AuthUser>('/api/admin-auth/invitations/accept', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function bootstrapFirstAdmin(payload: {
  token: string;
  id: string;
  sid: number;
  name: string;
  phone: string;
  email: string;
  password: string;
}) {
  return apiRequest<AuthUser>('/api/admin-auth/bootstrap', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/* -------------------------------------------------------------------------
 * 아티팩트 정합성 작업 · 시험 관리
 * ---------------------------------------------------------------------- */

export async function getArtifactJobs(token: string) {
  return apiRequest<JudgeJobApi[]>('/api/admin/artifact-jobs', {
    method: 'GET',
    token,
  });
}

export async function createArtifactReconcileJob(token: string) {
  return apiRequest<JudgeJobApi>('/api/admin/artifact-jobs/reconcile', {
    method: 'POST',
    token,
  });
}

export type ExamWritePayload = {
  title: string;
  intro: string;
  codeName: string;
  starttime?: string | null;
  deadline?: string | null;
  allowed_languages?: string[];
};

export async function createAdminExam(
  payload: ExamWritePayload,
  token: string,
) {
  return apiRequest<ExamApi>('/api/admin/exams', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

/* -------------------------------------------------------------------------
 * 문제 뱅크 (문제 · Revision · 테스트케이스)
 * ---------------------------------------------------------------------- */

export type ProblemApi = {
  id: number;
  code: string;
  title: string;
  owner_id: string | null;
  is_active: boolean;
  latest_revision_no: number | null;
  published_revision_id: number | null;
  created_at: string;
  updated_at: string;
};

export type ProblemRevisionApi = {
  id: number;
  problem_id: number;
  revision_no: number;
  status: string;
  statement: string;
  input_description: string;
  output_description: string;
  problem_mode: string;
  checker_type: string;
  time_limit_ms: number;
  memory_limit_mb: number;
  output_limit_kb: number;
  source_limit_kb: number;
  process_limit: number;
  allowed_languages: string[];
  validation_report: string | null;
  published_at: string | null;
  created_by: string | null;
  created_at: string;
};

export type ProblemTestCaseApi = {
  id: number;
  revision_id: number;
  group_id: number | null;
  case_name: string;
  position: number;
  score: number;
  is_sample: boolean;
  input_asset_id: number;
  output_asset_id: number;
  created_at: string;
};

export type ProblemCollaboratorApi = {
  id: number;
  problem_id: number;
  user_id: string;
  can_edit: boolean;
  created_at: string;
};

export async function getProblems(
  token: string,
  options?: { limit?: number; offset?: number },
) {
  const params = new URLSearchParams();
  if (options?.limit) params.set('limit', String(options.limit));
  if (options?.offset) params.set('offset', String(options.offset));
  const query = params.toString();
  return apiRequest<ProblemApi[]>(
    `/api/admin/problems${query ? `?${query}` : ''}`,
    { method: 'GET', token },
  );
}

export async function createProblem(
  payload: {
    code: string;
    title: string;
    statement?: string;
    input_description?: string;
    output_description?: string;
    time_limit_ms?: number;
    memory_limit_mb?: number;
    allowed_languages?: string[];
  },
  token: string,
) {
  return apiRequest<ProblemApi>('/api/admin/problems', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function updateProblem(
  problemId: number,
  payload: { title?: string | null; is_active?: boolean | null },
  token: string,
) {
  return apiRequest<ProblemApi>(`/api/admin/problems/${problemId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export async function archiveProblem(problemId: number, token: string) {
  return apiRequest<ProblemApi>(`/api/admin/problems/${problemId}/archive`, {
    method: 'POST',
    token,
  });
}

export async function getProblemRevisions(problemId: number, token: string) {
  return apiRequest<ProblemRevisionApi[]>(
    `/api/admin/problems/${problemId}/revisions`,
    { method: 'GET', token },
  );
}

export async function createProblemRevision(
  problemId: number,
  payload: {
    clone_from_revision_id?: number | null;
    statement?: string | null;
    input_description?: string | null;
    output_description?: string | null;
    time_limit_ms?: number | null;
    memory_limit_mb?: number | null;
    allowed_languages?: string[] | null;
  },
  token: string,
) {
  return apiRequest<ProblemRevisionApi>(
    `/api/admin/problems/${problemId}/revisions`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function updateProblemRevision(
  problemId: number,
  revisionId: number,
  payload: Record<string, unknown>,
  token: string,
) {
  return apiRequest<ProblemRevisionApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}`,
    { method: 'PATCH', token, body: JSON.stringify(payload) },
  );
}

export async function validateProblemRevision(
  problemId: number,
  revisionId: number,
  token: string,
) {
  return apiRequest<ProblemRevisionApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/validate`,
    { method: 'POST', token },
  );
}

export async function createProblemValidationJob(
  problemId: number,
  revisionId: number,
  idempotencyKey: string,
  token: string,
) {
  return apiRequest<JudgeJobApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/validation-jobs?idempotency_key=${encodeURIComponent(idempotencyKey)}`,
    { method: 'POST', token },
  );
}

export async function approveProblemRevision(
  problemId: number,
  revisionId: number,
  payload: { decision: string; note?: string | null },
  token: string,
) {
  return apiRequest<{ id: number; decision: string; reviewer_id: string }>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/approvals`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function publishProblemRevision(
  problemId: number,
  revisionId: number,
  token: string,
) {
  return apiRequest<ProblemRevisionApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/publish`,
    { method: 'POST', token },
  );
}

export async function getProblemTestcases(
  problemId: number,
  revisionId: number,
  token: string,
) {
  return apiRequest<ProblemTestCaseApi[]>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/testcases`,
    { method: 'GET', token },
  );
}

export async function createProblemTestcase(
  problemId: number,
  revisionId: number,
  payload: {
    caseName: string;
    position: number;
    score?: number;
    isSample?: boolean;
    inputFile: File;
    outputFile: File;
  },
  token: string,
) {
  const formData = new FormData();
  formData.append('case_name', payload.caseName);
  formData.append('position', String(payload.position));
  formData.append('score', String(payload.score ?? 0));
  formData.append('is_sample', String(payload.isSample ?? false));
  formData.append('input_file', payload.inputFile);
  formData.append('output_file', payload.outputFile);

  return apiRequest<ProblemTestCaseApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/testcases`,
    { method: 'POST', token, body: formData },
  );
}

export async function importProblemTestcasePackage(
  problemId: number,
  revisionId: number,
  packageFile: File,
  token: string,
) {
  const formData = new FormData();
  formData.append('package', packageFile);
  return apiRequest<ProblemTestCaseApi[]>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/testcases/package`,
    { method: 'POST', token, body: formData },
  );
}

export async function deleteProblemTestcase(
  problemId: number,
  revisionId: number,
  testcaseId: number,
  token: string,
) {
  return apiRequest<null>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/testcases/${testcaseId}`,
    { method: 'DELETE', token },
  );
}

export async function getProblemCollaborators(
  problemId: number,
  token: string,
) {
  return apiRequest<ProblemCollaboratorApi[]>(
    `/api/admin/problems/${problemId}/collaborators`,
    { method: 'GET', token },
  );
}

export async function addProblemCollaborator(
  problemId: number,
  payload: { user_id: string; can_edit: boolean },
  token: string,
) {
  return apiRequest<ProblemCollaboratorApi>(
    `/api/admin/problems/${problemId}/collaborators`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function removeProblemCollaborator(
  problemId: number,
  userId: string,
  token: string,
) {
  return apiRequest<null>(
    `/api/admin/problems/${problemId}/collaborators/${encodeURIComponent(userId)}`,
    { method: 'DELETE', token },
  );
}

export type ProblemAssetApi = {
  id: number;
  revision_id: number;
  asset_kind: string;
  display_name: string;
  content_type: string | null;
  size_bytes: number;
  sha256: string | null;
  is_hidden: boolean;
  created_at: string;
};

export type TestCaseGroupApi = {
  id: number;
  revision_id: number;
  group_key: string;
  position: number;
  score: number;
  scoring_policy: string;
  dependency_group_id: number | null;
  created_at: string;
};

export type JudgeJobEventApi = {
  id: number;
  job_id: number;
  sequence_no: number;
  event_type: string;
  message: string;
  payload_json: string | null;
  created_at: string;
};

export async function getProblemAssets(
  problemId: number,
  revisionId: number,
  token: string,
) {
  return apiRequest<ProblemAssetApi[]>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/assets`,
    { method: 'GET', token },
  );
}

export async function uploadProblemAsset(
  problemId: number,
  revisionId: number,
  payload: { assetKind: string; file: File },
  token: string,
) {
  const formData = new FormData();
  formData.append('asset_kind', payload.assetKind);
  formData.append('asset_file', payload.file);
  return apiRequest<ProblemAssetApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/assets`,
    { method: 'POST', token, body: formData },
  );
}

export async function downloadProblemAsset(
  problemId: number,
  revisionId: number,
  assetId: number,
  fallbackFilename: string,
  token: string,
) {
  return apiDownload(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/assets/${assetId}/download`,
    token,
    fallbackFilename,
  );
}

export async function createProblemDryRun(
  problemId: number,
  revisionId: number,
  payload: { language: string; sourceFile: File },
  token: string,
) {
  const formData = new FormData();
  formData.append('language', payload.language);
  formData.append('source_file', payload.sourceFile);
  return apiRequest<JudgeJobApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/dry-runs`,
    { method: 'POST', token, body: formData },
  );
}

export async function getTestcaseGroups(
  problemId: number,
  revisionId: number,
  token: string,
) {
  return apiRequest<TestCaseGroupApi[]>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/testcase-groups`,
    { method: 'GET', token },
  );
}

export async function createTestcaseGroup(
  problemId: number,
  revisionId: number,
  payload: {
    group_key: string;
    position?: number;
    score?: number;
    scoring_policy?: string;
  },
  token: string,
) {
  return apiRequest<TestCaseGroupApi>(
    `/api/admin/problems/${problemId}/revisions/${revisionId}/testcase-groups`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function getProblemJobEvents(jobId: number, token: string) {
  return apiRequest<JudgeJobEventApi[]>(
    `/api/admin/problem-jobs/${jobId}/events`,
    { method: 'GET', token },
  );
}

export async function attachProblemToHomework(
  homeworkNum: number,
  payload: { revision_id: number; position?: number },
  token: string,
) {
  return apiRequest<{
    id: number;
    homework_num: number;
    revision_id: number;
    position: number;
  }>(`/api/admin/homeworks/${homeworkNum}/problems`, {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function getProblemJobs(
  token: string,
  options?: { status?: string; revision_id?: number; limit?: number },
) {
  const params = new URLSearchParams();
  if (options?.status) params.set('status', options.status);
  if (options?.revision_id) {
    params.set('revision_id', String(options.revision_id));
  }
  if (options?.limit) params.set('limit', String(options.limit));
  const query = params.toString();
  return apiRequest<JudgeJobApi[]>(
    `/api/admin/problem-jobs${query ? `?${query}` : ''}`,
    { method: 'GET', token },
  );
}

export async function retryProblemJob(jobId: number, token: string) {
  return apiRequest<JudgeJobApi>(`/api/admin/problem-jobs/${jobId}/retry`, {
    method: 'POST',
    token,
  });
}

export async function cancelProblemJob(jobId: number, token: string) {
  return apiRequest<JudgeJobApi>(`/api/admin/problem-jobs/${jobId}/cancel`, {
    method: 'POST',
    token,
  });
}

/* -------------------------------------------------------------------------
 * 대회 (Contests)
 * ---------------------------------------------------------------------- */

export type ContestApi = {
  id: number;
  code: string;
  title: string;
  status: string;
  visibility: string;
  scoring_format: string;
  starts_at: string;
  ends_at: string;
  freeze_at: string | null;
  allow_virtual: boolean;
  allowed_organizations: string[];
  system_testing: boolean;
  created_by: string;
  created_at: string;
};

export type ContestCreatePayload = {
  code: string;
  title: string;
  starts_at: string;
  ends_at: string;
  freeze_at?: string | null;
  access_code?: string | null;
  visibility?: string;
  scoring_format?: string;
  allow_virtual?: boolean;
  allowed_organizations?: string[];
};

export type ContestProblemApi = {
  id: number;
  contest_id: number;
  revision_id: number;
  label: string;
  position: number;
  points: number;
};

export type ContestAnnouncementApi = {
  id: number;
  contest_id: number;
  title: string;
  message: string;
  created_by: string;
  created_at: string;
};

export type ClarificationApi = {
  id: number;
  contest_id: number;
  user_id: string;
  problem_id: number | null;
  question: string;
  answer: string | null;
  status: string;
  answered_at: string | null;
  created_at: string;
};

export type ContestParticipationApi = {
  id: number;
  contest_id: number;
  user_id: string;
  participation_type: string;
  started_at: string;
  ends_at: string | null;
};

export type ContestScoreboardRowApi = {
  rank: number;
  user_id: string;
  score: number;
  solved: number;
  penalty_minutes: number;
};

export type ContestOperationApprovalApi = {
  id: number;
  contest_id: number;
  operation: string;
  reason: string;
  approved_by: string;
  used_at: string | null;
  used_by_job_id: number | null;
  created_at: string;
};

/** 운영진 전용 목록. 초안·비공개 대회까지 모두 포함한다. */
export async function getContests(token: string) {
  return apiRequest<ContestApi[]>('/api/admin/contests', {
    method: 'GET',
    token,
  });
}

/** 참가자에게 보이는 대회 목록. 게시된 공개 대회와 이미 참가한 대회만 내려온다. */
export async function getOpenContests(token: string) {
  return apiRequest<ContestApi[]>('/api/contests', {
    method: 'GET',
    token,
  });
}

export async function getContestClarifications(
  contestId: number,
  token: string,
  statusFilter: 'all' | 'open' | 'answered' = 'all',
) {
  return apiRequest<ClarificationApi[]>(
    `/api/admin/contests/${contestId}/clarifications?status_filter=${statusFilter}`,
    { method: 'GET', token },
  );
}

export async function createContest(
  payload: ContestCreatePayload,
  token: string,
) {
  return apiRequest<ContestApi>('/api/admin/contests', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export async function publishContest(contestId: number, token: string) {
  return apiRequest<ContestApi>(`/api/admin/contests/${contestId}/publish`, {
    method: 'POST',
    token,
  });
}

/**
 * 시스템 테스트는 operation="system_testing" 으로 발급된, 아직 사용되지 않은
 * 운영 승인 번호가 있어야 시작할 수 있다.
 */
export async function enableContestSystemTesting(
  contestId: number,
  approvalId: number,
  token: string,
) {
  return apiRequest<ContestApi>(
    `/api/admin/contests/${contestId}/system-testing?approval_id=${approvalId}`,
    { method: 'POST', token },
  );
}

export async function attachContestProblem(
  contestId: number,
  payload: {
    revision_id: number;
    label: string;
    position: number;
    points?: number;
  },
  token: string,
) {
  return apiRequest<ContestProblemApi>(
    `/api/admin/contests/${contestId}/problems`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function createContestAnnouncement(
  contestId: number,
  payload: { title: string; message: string },
  token: string,
) {
  return apiRequest<ContestAnnouncementApi>(
    `/api/admin/contests/${contestId}/announcements`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function answerContestClarification(
  contestId: number,
  clarificationId: number,
  answer: string,
  token: string,
) {
  return apiRequest<ClarificationApi>(
    `/api/admin/contests/${contestId}/clarifications/${clarificationId}`,
    { method: 'PATCH', token, body: JSON.stringify({ answer }) },
  );
}

export async function approveContestOperation(
  contestId: number,
  payload: { operation: string; reason: string },
  token: string,
) {
  return apiRequest<ContestOperationApprovalApi>(
    `/api/admin/contests/${contestId}/operation-approvals`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function joinContest(
  contestId: number,
  payload: { participation_type: 'official' | 'virtual'; access_code?: string | null },
  token: string,
) {
  return apiRequest<ContestParticipationApi>(
    `/api/contests/${contestId}/participations`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function getContestAnnouncements(
  contestId: number,
  token: string,
) {
  return apiRequest<ContestAnnouncementApi[]>(
    `/api/contests/${contestId}/announcements`,
    { method: 'GET', token },
  );
}

export async function getMyContestClarifications(
  contestId: number,
  token: string,
) {
  return apiRequest<ClarificationApi[]>(
    `/api/contests/${contestId}/clarifications`,
    { method: 'GET', token },
  );
}

export async function askContestClarification(
  contestId: number,
  payload: { question: string; problem_id?: number | null },
  token: string,
) {
  return apiRequest<ClarificationApi>(
    `/api/contests/${contestId}/clarifications`,
    { method: 'POST', token, body: JSON.stringify(payload) },
  );
}

export async function getContestScoreboard(
  contestId: number,
  token: string,
  phase: 'current' | 'live' | 'system' = 'current',
) {
  return apiRequest<ContestScoreboardRowApi[]>(
    `/api/contests/${contestId}/scoreboard?phase=${phase}`,
    { method: 'GET', token },
  );
}

/* -------------------------------------------------------------------------
 * 분석 데이터 활용 동의 (계속)
 * ---------------------------------------------------------------------- */

export async function getAnalyticsConsents(token: string) {
  return apiRequest<AnalyticsConsentApi[]>('/api/analytics-consents', {
    method: 'GET',
    token,
  });
}

export async function recordAnalyticsConsent(
  payload: AnalyticsConsentCreatePayload,
  token: string,
) {
  return apiRequest<AnalyticsConsentApi>('/api/analytics-consents', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}
