# neoESPA 백엔드 API 가이드

이 문서는 현재 저장소의 백엔드 HTTP API를 실제 사용 관점에서 정리한 문서다. 엔드포인트 전체 목록은 [openapi-reference.md](./openapi-reference.md)를 기준으로 하고, 요청/응답 예시와 실패 계약은 `backend/tests/test_*api.py`의 검증 흐름을 우선 근거로 삼는다.

## 문서 사용 방법

- 빠르게 전체 경로를 훑고 싶다면 [openapi-reference.md](./openapi-reference.md)를 먼저 본다.
- 실제 요청 본문, 응답 필드, 상태 코드는 각 섹션의 테스트 파일을 함께 본다.
- 관리자 운영 절차가 필요하면 API 문서 대신 [GUIDE.md](./GUIDE.md)를 본다.

## 공통 규칙

### 기본 주소

- 프론트엔드: `http://localhost:3000`
- 백엔드 API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### 인증 방식

인증이 필요한 API는 로그인 후 받은 JWT를 `Authorization: Bearer <token>` 헤더로 전달한다.

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"id":"admin","ps":"pllab818"}'
```

성공 응답 예시:

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer"
}
```

### 자주 만나는 상태 코드

- `200 OK`: 조회/수정/운영 작업 성공
- `201 Created`: 생성 성공 (`/api/submissions`, `/api/admin/notices` 등)
- `400 Bad Request`: 입력값 또는 도메인 규칙 위반
- `401 Unauthorized`: 토큰 없음, 로그인 실패, 잘못된 자격 증명
- `403 Forbidden`: 권한 부족, 비활성 계정, 타인 리소스 접근
- `404 Not Found`: 비공개/미존재 리소스 조회 실패
- `422 Unprocessable Entity`: multipart 필수 필드 누락 같은 요청 형식 오류

## 1. 시스템

### `GET /api/ping`

서버 생존 여부를 확인하는 가장 단순한 헬스 체크 API다.

```bash
curl "http://localhost:8000/api/ping"
```

응답 예시:

```json
{
  "status": "ok",
  "backend": "python/fastapi"
}
```

테스트 근거:

- `backend/tests/test_api.py`

## 2. 인증

### `POST /api/auth/register`

회원가입 요청이다. 학번(`sid`) 중복과 이메일 정책을 검증한다.

요청 예시:

```json
{
  "id": "fresh-user",
  "sid": 20240205,
  "ps": "password",
  "name": "Fresh User",
  "phone": "010-4444-4444",
  "email": "fresh-user@example.com"
}
```

성공 시 사용자 레코드가 생성되고 `register_success` 이벤트 로그가 기록된다.

대표 실패:

- 중복 학번: `400` / `Student ID already exists`
- 이메일 정책 위반: `400` / `Email does not satisfy the registration policy`

### `POST /api/auth/login`

로그인 성공 시 access token을 반환한다.

요청 예시:

```json
{
  "id": "fresh-user",
  "ps": "password"
}
```

응답 예시:

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer"
}
```

대표 실패:

- 잘못된 비밀번호: `401`
- 비활성 계정: `403`

### `POST /api/auth/change-password`

로그인된 사용자의 비밀번호를 변경한다.

요청 예시:

```json
{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

성공 후에는 기존 비밀번호로 다시 로그인되지 않아야 한다.

테스트 근거:

- `backend/tests/test_auth_api.py`
- `backend/tests/test_api.py`

## 3. 사용자, 대시보드, 알림

### `GET /api/users/me`

현재 로그인한 사용자 정보를 조회한다.

### `PATCH /api/users/me`

본인 프로필을 수정한다.

요청 예시:

```json
{
  "name": "Updated Student",
  "phone": "010-9876-5432",
  "email": "updated-student@example.com"
}
```

응답 예시:

```json
{
  "id": "profile-student",
  "sid": 20246021,
  "name": "Updated Student",
  "phone": "010-9876-5432",
  "email": "updated-student@example.com",
  "user_group": "student",
  "is_active": true
}
```

대표 실패:

- 이메일 정책 위반: `400` / `Email does not satisfy the registration policy`

### `GET /api/dashboard/me`

학생 전용 대시보드 요약 API다. 미래 과제는 제외하고, 제출·채점 상태를 요약한다.

응답 예시:

```json
{
  "overview": {
    "total_homeworks": 4,
    "submitted_homeworks": 2,
    "graded_homeworks": 1,
    "pending_homeworks": 1,
    "missing_homeworks": 1,
    "closing_soon_homeworks": 1,
    "average_latest_score": 96.0
  },
  "homework_items": [
    {
      "homework_num": 1,
      "schedule_status": "closing_soon",
      "submission_count": 0,
      "remaining_seconds": 28800,
      "latest_submission_status": null,
      "latest_score": null
    }
  ],
  "recent_submissions": [
    {
      "homework_num": 3,
      "attempt_no": 1,
      "status": "pending"
    }
  ]
}
```

### `GET /api/notifications`

사용자 알림 목록을 반환한다. 공지 게시 같은 운영 이벤트가 알림으로 연결된다.

### `POST /api/notifications/read`

알림 읽음 처리 API다.

요청 예시:

```json
{
  "notification_ids": [1, 2, 3]
}
```

테스트 근거:

- `backend/tests/test_user_admin_api.py`
- `backend/tests/test_dashboard_api.py`
- `backend/tests/test_notification_api.py`

## 4. 과제, 제출, 시험

### `GET /api/homework`

학생에게 보이는 과제 목록을 반환한다. 아직 시작되지 않은 과제는 숨겨진다.

### `GET /api/homework/{homework_num}`

과제 상세를 반환한다. 허용 언어와 과제 정책이 학생 클라이언트에 노출된다.

### `POST /api/submissions`

코드 제출 API다. 제출 생성 직후 자동 채점을 시도한다.

요청 예시:

```json
{
  "homework_num": 1,
  "language": "python",
  "code_text": "print('hello world')",
  "original_filename": "main.py"
}
```

응답 예시:

```json
{
  "id": "<submission-id>",
  "homework_num": 1,
  "homework_title": "Open Homework",
  "attempt_no": 1,
  "status": "retryable",
  "compile_status": "not_started",
  "run_status": "not_started"
}
```

대표 실패:

- 마감 후 제출: `400` / `Submission deadline has passed`
- 허용되지 않은 언어: `400` / `Submission language is not allowed for this homework`

### `GET /api/submissions`

본인 제출 목록을 반환한다. `homework_num` 필터를 줄 수 있고 최신 시도가 먼저 온다.

### `GET /api/submissions/{submission_id}`

제출 상세를 반환한다. 타인 제출은 볼 수 없다.

대표 실패:

- 타인 제출 접근: `403` / `You cannot access this submission`

### `GET /api/submissions/{submission_id}/feedback`

제출 피드백을 조회한다.

### `GET /api/exams`

시험 목록을 조회한다.

### `POST /api/exams/{exam_id}/submit`

시험 코드를 제출한다.

요청 예시:

```json
{
  "language": "python",
  "code_text": "print('answer')\n",
  "original_filename": "main.py"
}
```

테스트 근거:

- `backend/tests/test_homework_api.py`
- `backend/tests/test_submission_api.py`
- `backend/tests/test_exam_api.py`
- `backend/tests/test_end_to_end_api.py`

## 5. 공지와 강의자료

### `GET /api/notice`

학생 공개용 공지 목록을 반환한다. 고정 공지는 상단에 오고 예약 공지는 공개 시점 전까지 숨겨진다.

응답 예시:

```json
[
  {
    "num": 2,
    "title": "Pinned Notice",
    "author": "Instructor",
    "content": "Pinned content",
    "date": "2026-03-02 08:00:00",
    "is_pinned": true
  },
  {
    "num": 3,
    "title": "Newest Notice",
    "author": "Instructor",
    "content": "Newest content",
    "date": "2026-03-03 08:00:00",
    "is_pinned": false
  }
]
```

### `GET /api/notice/{notice_num}`

공지 상세를 조회한다.

### `GET /api/materials`

강의자료 목록을 조회한다. 학생은 공개 자료만 보고, 관리자는 비공개 자료까지 확인할 수 있다.

자료 생성 요청 예시는 관리자 섹션의 `POST /api/admin/materials`를 참고한다.

테스트 근거:

- `backend/tests/test_notice_api.py`
- `backend/tests/test_material_api.py`

## 6. 협업

실시간 협업 기능은 HTTP API와 WebSocket을 함께 사용한다.

### HTTP 엔드포인트

- `GET /api/collab/sessions`
- `POST /api/collab/sessions`
- `POST /api/collab/sessions/{session_id}/join`
- `PATCH /api/collab/sessions/{session_id}/code`
- `POST /api/collab/sessions/{session_id}/messages`
- `POST /api/collab/sessions/{session_id}/close`
- `GET /api/collab/sessions/{session_id}/history`

### WebSocket 엔드포인트

- `/ws/collab/sessions/{session_id}`

세션 생성 요청 예시:

```json
{
  "title": "Mentoring Room",
  "initial_code": "print('hello')\n"
}
```

세션 참여 응답 예시:

```json
{
  "participants": [
    { "user_id": "mentor" },
    { "user_id": "student-member" }
  ]
}
```

코드 수정 요청 예시:

```json
{
  "code": "print('changed')\n"
}
```

대표 실패:

- 비참여자 수정 시도: `403`

테스트 근거:

- `backend/tests/test_collab_api.py`

## 7. 관리자 API

관리자 API는 모두 Bearer 토큰이 필요하다. 프론트엔드 `/admin`에서 일부 기능을 사용하지만, 전체 관리자 API가 UI에 모두 연결되어 있지는 않다. 운영 흐름 설명은 [GUIDE.md](./GUIDE.md), 순수 계약은 이 섹션을 기준으로 본다.

### 7-1. 관리자 대시보드와 운영 관찰

- `GET /api/admin/dashboard`
- `GET /api/admin/audit-logs`
- `GET /api/admin/observability/events`

대시보드 응답 예시:

```json
{
  "total_homeworks": 2,
  "active_students": 2,
  "total_submissions": 3,
  "queue": {
    "queue_size": 1,
    "queued_submission_ids": ["<submission-id>"]
  },
  "homework_metrics": [
    {
      "homework_num": 1,
      "submitted_students": 2,
      "submission_rate": 100.0,
      "failed_submission_count": 1
    }
  ]
}
```

### 7-2. 사용자 관리

- `GET /api/admin/users`
- `POST /api/admin/users/bulk`
- `PATCH /api/admin/users/{user_id}/role`
- `PATCH /api/admin/users/{user_id}/status`
- `POST /api/admin/users/{user_id}/reset-password`

역할 변경 요청 예시:

```json
{
  "user_group": "instructor"
}
```

역할 변경 응답 예시:

```json
{
  "id": "managed-user",
  "user_group": "instructor",
  "is_active": true
}
```

대량 등록 요청 예시:

```json
{
  "default_password": "welcome-pass",
  "skip_existing": true,
  "users": [
    {
      "id": "new-student",
      "sid": 20246012,
      "name": "New Student",
      "phone": "010-2222-2222",
      "email": "new-student@example.com",
      "user_group": "student"
    }
  ]
}
```

운영 포인트:

- 비활성화된 사용자는 이후 로그인 시 `403`을 받는다.
- 검색은 `search`, `role`, `is_active` 같은 쿼리 파라미터로 좁힐 수 있다.

### 7-3. 과제 관리

- `GET /api/admin/homeworks`
- `GET /api/admin/homeworks/{homework_num}`
- `POST /api/admin/homeworks`
- `POST /api/admin/homeworks/import`
- `PATCH /api/admin/homeworks/{homework_num}`
- `DELETE /api/admin/homeworks/{homework_num}`

#### JSON 생성 API

요청 예시:

```json
{
  "title": "Scheduled Homework",
  "intro": "Managed through the admin API.",
  "deadline": "2026-03-31 12:00:00",
  "starttime": "2026-03-26 12:00:00",
  "codeName": "scheduled",
  "filename": "guide.pdf",
  "ratedatanum": 3,
  "sec": 2,
  "sbnum": 4,
  "isLint": true,
  "allowed_languages": ["python", "cpp"],
  "lint_week": "4",
  "testcases": [
    {
      "name": "public-1",
      "input": "1 2\n",
      "expected_output": "3\n",
      "score": 40,
      "is_hidden": false
    },
    {
      "name": "hidden-1",
      "input": "10 5\n",
      "expected_output": "15\n",
      "score": 60,
      "is_hidden": true
    }
  ]
}
```

응답 예시:

```json
{
  "num": 1,
  "title": "Scheduled Homework",
  "schedule_status": "upcoming",
  "can_submit": false,
  "allowed_languages": ["cpp", "python"],
  "lint_week": "4",
  "testcases": [
    { "name": "public-1", "is_hidden": false },
    { "name": "hidden-1", "is_hidden": true }
  ]
}
```

#### Multipart import API

문제 파일과 입출력 ZIP을 함께 등록하는 관리자 전용 API다.

- 텍스트 필드: `title`, `intro`, `codeName`, `starttime`, `deadline`, `allowed_languages`, `isLint`, `lint_week`
- 파일 필드: `problem_file`, `input_zip`, `output_zip`
- `allowed_languages`는 JSON 배열이 아니라 JSON 문자열로 보낸다. 예: `"[\"python\",\"cpp\"]"`

성공 요청 흐름 예시:

```bash
TOKEN=$(curl -sS -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"id":"admin","ps":"pllab818"}' | python -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

curl -sS -X POST "http://localhost:8000/api/admin/homeworks/import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "title=Imported Homework" \
  -F "intro=Testing import endpoint" \
  -F "codeName=imported" \
  -F "starttime=2026-03-26 12:00:00" \
  -F "deadline=2026-04-02 12:00:00" \
  -F 'allowed_languages=["python","cpp"]' \
  -F "isLint=false" \
  -F "lint_week=" \
  -F "problem_file=@tests/fixtures/homework_import/problem.pdf;type=application/pdf" \
  -F "input_zip=@tests/fixtures/homework_import/inputs.zip;type=application/zip" \
  -F "output_zip=@tests/fixtures/homework_import/outputs.zip;type=application/zip"
```

성공 응답 예시:

```json
{
  "num": 1,
  "title": "Imported Homework",
  "codeName": "imported",
  "parsed_testcase_count": 2,
  "problem_file_name": "problem.pdf",
  "input_zip_name": "inputs.zip",
  "output_zip_name": "outputs.zip"
}
```

대표 실패:

- 무토큰: `401`
- 학생 토큰: `403`
- `problem_file` 또는 ZIP 누락: `422`
- 손상 ZIP: `400` / `Input ZIP is corrupt or unreadable`
- 파일명 불일치: `400` / `Input and output ZIP archives must contain matching filenames`
- 확장자 오류: `400` / `Problem file extension must be one of: .pdf, .md, .txt`
- 날짜 역전: `400` / `deadline must be later than starttime`

운영 포인트:

- 성공 응답은 `problem_file_name`, `input_zip_name`, `output_zip_name`, `parsed_testcase_count` 같은 안전 요약만 노출한다.
- import 도중 서버 내부 오류가 나면 DB와 아티팩트가 함께 롤백되도록 테스트되어 있다.

### 7-4. 채점, 재채점, 내보내기

- `POST /api/admin/submissions/{submission_id}/grade`
- `POST /api/admin/submissions/{submission_id}/queue`
- `POST /api/admin/submissions/{submission_id}/requeue`
- `PATCH /api/admin/submissions/{submission_id}/score`
- `POST /api/admin/grading/process-next`
- `GET /api/admin/homeworks/{homework_num}/grades/export`
- `GET /api/admin/homeworks/{homework_num}/submissions/archive`

재채점 응답 예시:

```json
{
  "status": "pending",
  "compile_status": "not_started",
  "run_status": "not_started",
  "total_score": 0.0
}
```

점수 조정 요청 예시:

```json
{
  "manual_total_score": 87.5,
  "adjustment_note": "Late penalty applied"
}
```

점수 조정 응답 예시:

```json
{
  "total_score": 87.5,
  "manual_total_score": 87.5,
  "score_adjustment_note": "Late penalty applied",
  "score_adjusted_by": "admin-adjust"
}
```

내보내기 포인트:

- 성적 export는 `text/csv`와 `homework_<num>_grades.csv` 파일명을 반환한다.
- 제출 archive는 최신 제출만 ZIP으로 묶어 내려준다.

### 7-5. 공지, 자료, 표절, 설정, 시험

- 공지: `GET/POST/PATCH/DELETE /api/admin/notices*`
- 자료: `POST /api/admin/materials`
- 표절: `POST /api/admin/homeworks/{homework_num}/plagiarism/run`, `GET /api/admin/plagiarism/runs`, `GET /api/admin/plagiarism/pairs`, `GET /api/admin/plagiarism/pairs/{pair_id}`
- 설정: `GET /api/admin/settings`, `PATCH /api/admin/settings`
- 시험 생성: `POST /api/admin/exams`

공지 생성 요청 예시:

```json
{
  "title": "Initial Notice",
  "author": "Admin",
  "content": "Initial content",
  "date": "2026-03-12 09:00:00",
  "is_pinned": true,
  "is_published": false
}
```

자료 생성 요청 예시:

```json
{
  "title": "Week 6 Slides",
  "description": "Recursion lecture deck",
  "url": "https://example.com/week6.pdf",
  "is_published": true
}
```

설정 변경 요청 예시:

```json
{
  "settings": [
    { "key": "lint_calc_weight", "value": 20 },
    { "key": "lint_set_default", "value": true }
  ]
}
```

표절 실행 응답 예시:

```json
{
  "flagged_pair_count": 1
}
```

테스트 근거:

- `backend/tests/test_dashboard_api.py`
- `backend/tests/test_user_admin_api.py`
- `backend/tests/test_homework_admin_api.py`
- `backend/tests/test_grading_admin_api.py`
- `backend/tests/test_export_api.py`
- `backend/tests/test_notice_admin_api.py`
- `backend/tests/test_material_api.py`
- `backend/tests/test_plagiarism_api.py`
- `backend/tests/test_settings_api.py`
- `backend/tests/test_exam_api.py`

## 8. 비 OpenAPI 경로

- WebSocket: `/ws/collab/sessions/{session_id}`

이 경로는 OpenAPI operation 목록에는 포함되지 않지만 현재 협업 기능의 핵심 경로다.

## 9. 문서 작성 기준

- 전체 경로 수와 그룹 분류는 `refs/openapi-reference.md`를 기준으로 유지했다.
- 요청/응답 예시는 `backend/tests/test_*api.py`에서 확인 가능한 값만 반영했다.
- 운영 UI 설명은 이 문서에 넣지 않았고, 관리자 작업 방식은 `refs/GUIDE.md`로 분리했다.
