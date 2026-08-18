# neoESPA Backend API Reference

이 문서는 현재 FastAPI 애플리케이션의 runtime router와 OpenAPI 스키마를 기준으로 등록된 API를 업무 카테고리별로 정리합니다. OpenAPI에 노출되지 않는 WebSocket route도 포함합니다.

- 기준 계약: [openapi.json](./openapi.json) — **154개** operation
- 이 문서의 표에 있는 행: **159개**. 차이 5개의 내역은 아래와 같으며 모두 OpenAPI 스키마에 노출되지 않습니다.
  - Swagger UI·ReDoc·OpenAPI 스키마 route 4개 (1번 섹션). FastAPI가 자동 생성하며 API 표면이 아닙니다.
  - WebSocket route 1개 (8번 섹션, `WS` method 표기).
- 모든 path의 중괄호 표기는 path parameter이며, 이름까지 runtime router와 일치합니다.
- 관리자 경로는 각 작업에 필요한 capability, 소유권, step-up 또는 승인 정책을 추가로 검사할 수 있습니다.

## API 목록

### 1. 시스템 상태 및 진단 (9개)

| Method | Path                    | Description             |
| ------ | ----------------------- | ----------------------- |
| GET    | `/api/ping`             | Ping                    |
| GET    | `/docs`                 | Swagger UI              |
| GET    | `/docs/oauth2-redirect` | Swagger OAuth2 redirect |
| GET    | `/health/judge`         | Health Judge            |
| GET    | `/health/live`          | Health Live             |
| GET    | `/health/ready`         | Health Ready            |
| GET    | `/api/admin/health/judge` | Detailed Judge Health |
| GET    | `/openapi.json`         | OpenAPI schema          |
| GET    | `/redoc`                | ReDoc UI                |

### 2. 인증 및 관리자 인증 (9개)

| Method | Path                                 | Description             |
| ------ | ------------------------------------ | ----------------------- |
| POST   | `/api/admin-auth/bootstrap`          | Bootstrap First Admin   |
| POST   | `/api/admin-auth/invitations`        | Create Admin Invitation |
| POST   | `/api/admin-auth/invitations/accept` | Accept Invitation       |
| GET    | `/api/auth/assurance`                | Auth Assurance          |
| POST   | `/api/auth/change-password`          | Change Password         |
| POST   | `/api/auth/login`                    | Login                   |
| POST   | `/api/auth/logout`                   | Logout                  |
| POST   | `/api/auth/register`                 | Register                |
| POST   | `/api/auth/step-up`                  | Step Up Authentication  |

### 3. 사용자 프로필 및 분석 동의 (4개)

| Method | Path                      | Description       |
| ------ | ------------------------- | ----------------- |
| GET    | `/api/analytics-consents` | List My Consents  |
| POST   | `/api/analytics-consents` | Record My Consent |
| GET    | `/api/users/me`           | Read Users Me     |
| PATCH  | `/api/users/me`           | Update My Profile |

### 4. 학습 대시보드 및 알림 (3개)

| Method | Path                      | Description             |
| ------ | ------------------------- | ----------------------- |
| GET    | `/api/dashboard/me`       | Get Student Dashboard   |
| GET    | `/api/notifications`      | List Notifications      |
| POST   | `/api/notifications/read` | Mark Notifications Read |

### 5. 과제 및 제출 (8개)

| Method | Path                                             | Description             |
| ------ | ------------------------------------------------ | ----------------------- |
| GET    | `/api/homework`                                  | Get Homeworks           |
| GET    | `/api/homework/{homework_num}`                   | Get Homework Detail     |
| GET    | `/api/homeworks/{homework_num}/snapshots/latest` | Get Latest Snapshot     |
| GET    | `/api/submissions`                               | List Submissions        |
| POST   | `/api/submissions`                               | Create Submission       |
| POST   | `/api/submissions/snapshots`                     | Save Code Snapshot      |
| GET    | `/api/submissions/{submission_id}`               | Get Submission Detail   |
| GET    | `/api/submissions/{submission_id}/feedback`      | Get Submission Feedback |

### 6. 시험 (5개)

| Method | Path                               | Description           |
| ------ | ---------------------------------- | --------------------- |
| POST   | `/api/admin/exams`                 | Create Exam           |
| GET    | `/api/exams`                       | List Exams            |
| GET    | `/api/exams/{exam_id}`             | Get Exam              |
| GET    | `/api/exams/{exam_id}/submissions` | List Exam Submissions |
| POST   | `/api/exams/{exam_id}/submit`      | Submit Exam           |

### 7. 공지·자료실·Q&A (18개)

| Method | Path                                            | Description                  |
| ------ | ----------------------------------------------- | ---------------------------- |
| POST   | `/api/admin/materials`                          | Create Material              |
| DELETE | `/api/admin/materials/{material_id}`            | Delete Material              |
| PATCH  | `/api/admin/materials/{material_id}`            | Update Material              |
| POST   | `/api/admin/materials/{material_id}/attachment` | Upload Material Attachment   |
| GET    | `/api/admin/notices`                            | Get Admin Notices            |
| POST   | `/api/admin/notices`                            | Create Notice                |
| DELETE | `/api/admin/notices/{notice_num}`               | Delete Notice                |
| PATCH  | `/api/admin/notices/{notice_num}`               | Update Notice                |
| GET    | `/api/materials`                                | List Materials               |
| GET    | `/api/materials/{material_id}`                  | Get Material                 |
| GET    | `/api/materials/{material_id}/attachment`       | Download Material Attachment |
| POST   | `/api/materials/{material_id}/comments`         | Add Material Comment         |
| GET    | `/api/notice`                                   | Get Notices                  |
| GET    | `/api/notice/{notice_num}`                      | Get Notice Detail            |
| GET    | `/api/qa`                                       | List Qa Posts                |
| POST   | `/api/qa`                                       | Create Qa Post               |
| GET    | `/api/qa/{post_id}`                             | Get Qa Post                  |
| POST   | `/api/qa/{post_id}/answers`                     | Add Qa Answer                |

### 8. 협업 (8개)

| Method | Path                                         | Description                                                                                                             |
| ------ | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| WS     | `/ws/collab/sessions/{session_id}`           | Collab Session Websocket — 실시간 세션 채널. query parameter `token` 필수, 인증 실패 시 close code 4401. OpenAPI 미노출 |
| GET    | `/api/collab/sessions`                       | List Collab Sessions                                                                                                    |
| POST   | `/api/collab/sessions`                       | Create Collab Session                                                                                                   |
| POST   | `/api/collab/sessions/{session_id}/close`    | Close Collab Session                                                                                                    |
| PATCH  | `/api/collab/sessions/{session_id}/code`     | Update Collab Code                                                                                                      |
| GET    | `/api/collab/sessions/{session_id}/history`  | Get Collab Session History                                                                                              |
| POST   | `/api/collab/sessions/{session_id}/join`     | Join Collab Session                                                                                                     |
| POST   | `/api/collab/sessions/{session_id}/messages` | Create Collab Message                                                                                                   |

### 9. 대회 참가 (6개)

| Method | Path                                        | Description                |
| ------ | ------------------------------------------- | -------------------------- |
| GET    | `/api/contests`                             | List Open Contests         |
| GET    | `/api/contests/{contest_id}/announcements`  | List Contest Announcements |
| GET    | `/api/contests/{contest_id}/clarifications` | List My Clarifications     |
| POST   | `/api/contests/{contest_id}/clarifications` | Ask Clarification          |
| POST   | `/api/contests/{contest_id}/participations` | Join Contest               |
| GET    | `/api/contests/{contest_id}/scoreboard`     | Contest Scoreboard         |

### 10. 관리자: 대회 운영 (10개)

| Method | Path                                                                 | Description                   |
| ------ | -------------------------------------------------------------------- | ----------------------------- |
| GET    | `/api/admin/contests`                                                | List Contests                 |
| POST   | `/api/admin/contests`                                                | Create Contest                |
| POST   | `/api/admin/contests/{contest_id}/announcements`                     | Create Contest Announcement   |
| GET    | `/api/admin/contests/{contest_id}/clarifications`                    | List Contest Clarifications   |
| PATCH  | `/api/admin/contests/{contest_id}/clarifications/{clarification_id}` | Answer Clarification          |
| POST   | `/api/admin/contests/{contest_id}/operation-approvals`               | Approve Contest Operation     |
| POST   | `/api/admin/contests/{contest_id}/problems`                          | Attach Contest Problem        |
| POST   | `/api/admin/contests/{contest_id}/publish`                           | Publish Contest               |
| POST   | `/api/admin/contests/{contest_id}/result-events`                     | Append Contest Result Event   |
| POST   | `/api/admin/contests/{contest_id}/system-testing`                    | Enable Contest System Testing |

### 11. 관리자: 과제 및 제출 운영 (16개)

| Method | Path                                                      | Description                       |
| ------ | --------------------------------------------------------- | --------------------------------- |
| GET    | `/api/admin/dashboard`                                    | Get Admin Dashboard               |
| GET    | `/api/admin/homeworks`                                    | List Admin Homeworks              |
| POST   | `/api/admin/homeworks`                                    | Create Homework                   |
| POST   | `/api/admin/homeworks/import`                             | Import Homework                   |
| DELETE | `/api/admin/homeworks/{homework_num}`                     | Delete Homework                   |
| GET    | `/api/admin/homeworks/{homework_num}`                     | Get Admin Homework                |
| PATCH  | `/api/admin/homeworks/{homework_num}`                     | Update Homework                   |
| GET    | `/api/admin/homeworks/{homework_num}/grades/export`       | Export Homework Grades            |
| POST   | `/api/admin/homeworks/{homework_num}/plagiarism/run`      | Run Plagiarism Scan               |
| POST   | `/api/admin/homeworks/{homework_num}/problems`            | Attach Problem To Homework        |
| GET    | `/api/admin/homeworks/{homework_num}/snapshots/{user_id}` | Get Student Snapshots             |
| GET    | `/api/admin/homeworks/{homework_num}/submissions/archive` | Export Latest Submissions Archive |
| POST   | `/api/admin/submissions/{submission_id}/grade`            | Grade Submission                  |
| POST   | `/api/admin/submissions/{submission_id}/queue`            | Queue Submission For Grading      |
| POST   | `/api/admin/submissions/{submission_id}/requeue`          | Requeue Submission For Grading    |
| PATCH  | `/api/admin/submissions/{submission_id}/score`            | Adjust Submission Score           |

### 12. 관리자: 문제·Revision·테스트 데이터 (34개)

| Method | Path                                                                                  | Description                        |
| ------ | ------------------------------------------------------------------------------------- | ---------------------------------- |
| GET    | `/api/admin/artifact-jobs`                                                            | List Artifact Jobs                 |
| POST   | `/api/admin/artifact-jobs/reconcile`                                                  | Create Artifact Reconciliation Job |
| GET    | `/api/admin/problem-jobs`                                                             | List Problem Jobs                  |
| GET    | `/api/admin/problem-jobs/{job_id}`                                                    | Get Problem Job                    |
| POST   | `/api/admin/problem-jobs/{job_id}/cancel`                                             | Cancel Problem Job                 |
| GET    | `/api/admin/problem-jobs/{job_id}/events`                                             | Get Problem Job Events             |
| POST   | `/api/admin/problem-jobs/{job_id}/retry`                                              | Retry Problem Job                  |
| GET    | `/api/admin/problems`                                                                 | List Problems                      |
| POST   | `/api/admin/problems`                                                                 | Create Problem                     |
| GET    | `/api/admin/problems/{problem_id}`                                                    | Get Problem                        |
| PATCH  | `/api/admin/problems/{problem_id}`                                                    | Update Problem                     |
| POST   | `/api/admin/problems/{problem_id}/archive`                                            | Archive Problem                    |
| GET    | `/api/admin/problems/{problem_id}/collaborators`                                      | List Problem Collaborators         |
| POST   | `/api/admin/problems/{problem_id}/collaborators`                                      | Add Problem Collaborator           |
| DELETE | `/api/admin/problems/{problem_id}/collaborators/{user_id}`                            | Remove Problem Collaborator        |
| GET    | `/api/admin/problems/{problem_id}/revisions`                                          | List Revisions                     |
| POST   | `/api/admin/problems/{problem_id}/revisions`                                          | Create Revision                    |
| GET    | `/api/admin/problems/{problem_id}/revisions/{revision_id}`                            | Get Revision                       |
| PATCH  | `/api/admin/problems/{problem_id}/revisions/{revision_id}`                            | Update Draft Revision              |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/approvals`                  | Review Problem Revision            |
| GET    | `/api/admin/problems/{problem_id}/revisions/{revision_id}/assets`                     | List Assets                        |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/assets`                     | Upload Problem Asset               |
| GET    | `/api/admin/problems/{problem_id}/revisions/{revision_id}/assets/{asset_id}/download` | Download Asset                     |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/dry-runs`                   | Create Problem Dry Run             |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/publish`                    | Publish Revision                   |
| GET    | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcase-groups`            | List Testcase Groups               |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcase-groups`            | Create Testcase Group              |
| GET    | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcases`                  | List Testcases                     |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcases`                  | Create Testcase                    |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcases/package`          | Import Testcase Package            |
| DELETE | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcases/{testcase_id}`    | Delete Testcase                    |
| PATCH  | `/api/admin/problems/{problem_id}/revisions/{revision_id}/testcases/{testcase_id}`    | Update Testcase                    |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/validate`                   | Validate Revision                  |
| POST   | `/api/admin/problems/{problem_id}/revisions/{revision_id}/validation-jobs`            | Create Validation Job              |

### 13. 관리자: 채점 큐·Worker·재채점 (14개)

| Method | Path                                            | Description               |
| ------ | ----------------------------------------------- | ------------------------- |
| GET    | `/api/admin/grading/incidents`                  | List Grading Incidents    |
| GET    | `/api/admin/grading/metrics`                    | Grading Metrics           |
| POST   | `/api/admin/grading/process-next`               | Process Next Grading Job  |
| GET    | `/api/admin/judge-jobs`                         | List Judge Jobs           |
| GET    | `/api/admin/judge-workers`                      | List Judge Workers        |
| POST   | `/api/admin/judge-workers/{worker_id}/disable`  | Disable Judge Worker      |
| POST   | `/api/admin/judge-workers/{worker_id}/drain`    | Drain Judge Worker        |
| POST   | `/api/admin/judge-workers/{worker_id}/enable`   | Enable Judge Worker       |
| GET    | `/api/admin/rejudge-jobs`                       | List Rejudge Jobs         |
| POST   | `/api/admin/rejudge-jobs`                       | Create Rejudge            |
| POST   | `/api/admin/rejudge-jobs/preview`               | Preview Rejudge           |
| GET    | `/api/admin/rejudge-jobs/{job_id}`              | Get Rejudge Job           |
| POST   | `/api/admin/rejudge-jobs/{job_id}/cancel`       | Cancel Rejudge Job        |
| POST   | `/api/admin/rejudge-jobs/{job_id}/retry-failed` | Retry Failed Rejudge Jobs |

### 14. 관리자: 사용자·권한·설정 (10개)

| Method | Path                                        | Description               |
| ------ | ------------------------------------------- | ------------------------- |
| GET    | `/api/admin/roles/{role_name}/capabilities` | Get Role Capabilities     |
| PUT    | `/api/admin/roles/{role_name}/capabilities` | Replace Role Capabilities |
| GET    | `/api/admin/settings`                       | List Admin Settings       |
| PATCH  | `/api/admin/settings`                       | Update Admin Settings     |
| POST   | `/api/admin/settings/{key}/rollback`        | Rollback Admin Setting    |
| GET    | `/api/admin/users`                          | List Admin Users          |
| POST   | `/api/admin/users/bulk`                     | Bulk Create Users         |
| POST   | `/api/admin/users/{user_id}/reset-password` | Reset User Password       |
| PATCH  | `/api/admin/users/{user_id}/role`           | Update User Role          |
| PATCH  | `/api/admin/users/{user_id}/status`         | Update User Status        |

### 15. 관리자: 감사·관측성·표절 (5개)

| Method | Path                                    | Description           |
| ------ | --------------------------------------- | --------------------- |
| GET    | `/api/admin/audit-logs`                 | List Audit Logs       |
| GET    | `/api/admin/observability/events`       | List System Events    |
| GET    | `/api/admin/plagiarism/pairs`           | List Plagiarism Pairs |
| GET    | `/api/admin/plagiarism/pairs/{pair_id}` | Get Plagiarism Pair   |
| GET    | `/api/admin/plagiarism/runs`            | List Plagiarism Runs  |

## 오류 응답 규격

`HTTPException`과 요청 검증 실패는 `app/main.py`의 exception handler를 거쳐 공통 envelope로 반환됩니다.

| 필드           | 설명                                                                              |
| -------------- | --------------------------------------------------------------------------------- |
| `code`         | 오류 코드. `HTTPException`은 `http_{status_code}`, 검증 실패는 `validation_error` |
| `message`      | 사람이 읽을 수 있는 오류 메시지. `detail`이 문자열이 아니면 `Request failed`      |
| `field_errors` | 필드 단위 오류 목록(`field`, `message`, `type`). 검증 실패(422)가 아니면 빈 배열  |
| `request_id`   | 요청 추적 ID. 응답 헤더 `X-Request-ID`와 동일한 값                                |
| `detail`       | FastAPI 원본 detail                                                               |

## 스펙 검증

```bash
cd backend

# 1. 현재 스키마가 커밋된 기준선 대비 breaking change를 포함하는지 검사
uv run python -m app.cli check-openapi --baseline openapi.json

# 2. 이 문서가 runtime router와 정확히 일치하는지 검사
uv run pytest -q tests/core/test_openapi_contract.py
```

`export-openapi`는 위 검사에 **포함하지 않습니다.** 이 명령은 git에 추적되는 기준선을 현재
스키마로 덮어쓰기 때문에, `check-openapi`보다 먼저 실행하면 현재 스키마를 자기 자신과 비교하게
되어 항상 `compatible: true`가 나오고 breaking change 검출이 무력화됩니다.

기준선 갱신은 API 변경이 의도된 것임을 검토·승인한 뒤 별도 단계로 실행합니다.

```bash
uv run python -m app.cli export-openapi --output openapi.json
```

API를 추가·삭제·변경한 경우 openapi.json과 이 문서를 함께 갱신해야 합니다.
