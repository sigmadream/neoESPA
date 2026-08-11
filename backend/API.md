# neoESPA Backend API Reference

본 문서는 neoESPA 백엔드 API 명세를 카테고리별로 분류하여 기술합니다. QA 테스트 및 프론트엔드 개발 시 참고하시기 바랍니다.

## 1. 사용자 및 인증 (Auth & Users)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | 신규 사용자 회원가입 |
| POST | `/api/auth/login` | 로그인 및 액세스 토큰 발급 |
| POST | `/api/auth/change-password` | 현재 사용자의 비밀번호 변경 |
| GET | `/api/users/me` | 내 프로필 정보 조회 |
| PATCH | `/api/users/me` | 내 프로필 정보 수정 |

## 2. 과제 및 제출 (Homework & Submissions)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/homework` | 현재 제출 가능한 과제 목록 조회 |
| GET | `/api/homework/{num}` | 특정 과제 상세 정보 조회 |
| POST | `/api/submissions` | 과제 제출 (코드 업로드) |
| GET | `/api/submissions` | 내 제출 이력 조회 (과제별 필터링 가능) |
| GET | `/api/submissions/{id}` | 특정 제출 상세 결과 조회 |
| GET | `/api/submissions/{id}/feedback` | 인공지능 기반 제출 피드백 및 힌트 조회 |

## 3. 학습 현황 및 알림 (Dashboard & Notifications)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard/me` | 내 학습 현황 요약 (과제 상태, 최근 점수 등) |
| GET | `/api/notifications` | 내 알림 목록 조회 |
| POST | `/api/notifications/read` | 알림 읽음 처리 |

## 4. 공지 및 자료실 (Notices & Materials)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notice` | 전체 공지사항 목록 조회 |
| GET | `/api/notice/{num}` | 특정 공지사항 상세 조회 |
| GET | `/api/materials` | 강의 자료 목록 조회 |

## 5. 시험 및 성적 (Exams & Grading)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/exams` | 시험 목록 조회 |
| POST | `/api/exams/{id}/submit` | 시험 답안 제출 |

## 6. 협업 도구 (Collaboration)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/collab/sessions` | 활성화된 협업 세션 목록 조회 |
| POST | `/api/collab/sessions` | 신규 협업 세션 생성 |
| POST | `/api/collab/sessions/{id}/join` | 협업 세션 참여 |
| PATCH | `/api/collab/sessions/{id}/code` | 공유 코드 실시간 업데이트 |
| POST | `/api/collab/sessions/{id}/messages` | 세션 내 채팅 메시지 전송 |
| GET | `/api/collab/sessions/{id}/history` | 세션 활동 이력 (채팅, 코드 스냅샷) 조회 |
| POST | `/api/collab/sessions/{id}/close` | 협업 세션 종료 |

## 7. 관리자 전용 (Admin & System)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/dashboard` | 시스템 관리 대시보드 (전체 통계) |
| GET | `/api/admin/users` | 전체 사용자 목록 조회 및 관리 |
| PATCH | `/api/admin/users/{id}/role` | 사용자 권한(관리자/학생) 변경 |
| POST | `/api/admin/users/bulk` | 사용자 일괄 등록 |
| POST | `/api/admin/homeworks` | 신규 과제 생성 및 설정 |
| POST | `/api/admin/homeworks/import` | ZIP 파일을 이용한 과제 및 테스트케이스 일괄 임포트 |
| DELETE | `/api/admin/homeworks/{num}` | 과제 삭제 |
| POST | `/api/admin/submissions/{id}/grade` | 특정 제출건 수동 채점 요청 |
| PATCH | `/api/admin/submissions/{id}/score` | 점수 수동 조정 |
| GET | `/api/admin/settings` | 시스템 환경 설정 조회 |
| PATCH | `/api/admin/settings` | 시스템 환경 설정 수정 |
| GET | `/api/admin/audit-logs` | 시스템 감사 로그 조회 |
| POST | `/api/admin/homeworks/{num}/plagiarism/run` | 표절 검사 실행 |
| GET | `/api/admin/problems` | 문제와 revision 목록 조회 |
| POST | `/api/admin/problems` | 문제 초안 생성 |
| POST | `/api/admin/problems/{problem_id}/revisions/{revision_id}/validate` | revision 비동기 검증 |
| POST | `/api/admin/problems/{problem_id}/revisions/{revision_id}/publish` | 검증된 revision 게시 |
| POST | `/api/admin/rejudge-jobs/preview` | 일괄 재채점 대상 미리보기 |
| POST | `/api/admin/rejudge-jobs` | 영속 일괄 재채점 작업 생성 |
| GET | `/api/admin/judge-jobs` | 채점 작업 상태 및 오류 조회 |
| GET | `/api/admin/judge-workers` | worker heartbeat·상태·capability 조회 |
| GET | `/api/admin/grading/metrics` | 큐 및 판정 지표 조회 |
| GET | `/api/admin/grading/incidents` | 문제·worker·runtime별 장애 조회 |
| POST | `/api/admin/contests` | 대회 초안 생성 |
| POST | `/api/admin/contests/{contest_id}/publish` | revision을 고정하여 대회 게시 |
| GET | `/api/contests/{contest_id}/scoreboard` | live/system-testing event replay 스코어보드 |

---
*주의: `/api/admin` 경로는 단일 `admin` 역할이 아니라 작업별 capability와 문제 소유권 범위를 검사합니다. 위험 작업은 step-up 인증 또는 2인 승인 정책이 추가로 적용될 수 있습니다.*

기계 판독 가능한 전체 계약은 `openapi.json`이며 `python -m app.cli
check-openapi --baseline openapi.json`으로 breaking change를 검사합니다. 오류 응답에는
`code`, `message`, `field_errors`, `request_id`가 포함됩니다.
