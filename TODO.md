# TODO

기능 개발, 오류 수정, 배포 준비 관점에서 남은 작업을 정리한 문서입니다.
완료된 항목은 `DONE.md`로 이동합니다. 기능 로드맵의 근거는 `refs/prd.md`, `refs/plan.md`를 참고합니다.

## 1. 기능 개발

### 1.1 시험 전용 UI — 완료

- [x] 시험 목록 페이지 (`/exam`)
- [x] 시험 응시 페이지 (마감 카운트다운, 제출 흐름 포함)
- [x] 시험 결과 페이지
- [x] Playwright e2e 스펙 추가 (`frontend/e2e/exam.spec.ts`)

완료 기준 충족: 학생 계정으로 목록 조회 → 응시 → 제출 → 결과 확인 전체 흐름을 e2e로 검증했습니다.

### 1.2 게시판형 자료실 — 완료

- [x] 게시글 CRUD API 및 화면 (본문 `content` 작성 포함)
- [x] 첨부 파일 업로드/다운로드 (`/api/admin/materials/{id}/attachment`, `/api/materials/{id}/attachment`)
- [x] 댓글 기능

### 1.3 게시판형 Q&A — 완료

- [x] 질문/답변 도메인 모델 및 API (`backend/app/domains/qa`)
- [x] 질문 작성, 답변 화면 (`/qa`)
- [x] 비공개 질문(작성자와 운영진만 열람) 옵션

### 1.4 멀티 코스 구조

현재는 단일 코스 전제입니다. `refs/prd.md` 6.1의 발전 단계 항목입니다.

- [ ] `courses`, `terms`, `course_offerings`, `course_enrollments` 모델 설계
- [ ] 과제/시험/공지/자료를 offering 단위로 스코프 분리
- [ ] 코스 허브 화면 (`refs/plan.md` 실행 묶음 A)
- [ ] 기존 단일 코스 데이터 마이그레이션 계획

### 1.5 운영 도구 보강 (refs/plan.md 실행 묶음 B)

- [ ] 상세 채점 결과 화면 및 전용 lint 뷰어
- [ ] lint 운영 패리티 UI (Score / Option / Message / Rule 관리)
- [ ] 표절 판정 후속 워크플로 (메모, 점수 반영, 감사 로그)
- [ ] 가입 승인(멤버십 상태) 흐름

## 2. 오류 수정 및 안정화

### 2.1 환경 값 불일치 정리 (우선순위 높음)

`APP_ENV` 기준 값이 파일마다 다릅니다. 시딩/보안 검증 분기가 의도와 다르게 동작할 수 있습니다.

- [x] `docker-compose.yml`은 `development`, `backend/app/core/config.py` 기본값은 `dev`, `backend/app/main.py`는 기본값 `production`으로 읽는 불일치 해소
- [x] 허용 값 집합을 한 곳(config)에서 정의하고 나머지는 참조하도록 정리

### 2.2 마이그레이션 체계 단일화

자체 마이그레이션 체계로 단일화했습니다.

- [x] 자체 체계(`backend/app/migrations/v0001~v0005`) 유지, Alembic 및 의존성 제거 완료
- [x] 신규 스키마 변경 절차를 `DEPLOY.md`에 문서화, `README.md`에서 참조

### 2.3 CORS 설정 환경 변수화

`backend/app/main.py:34-45`에서 `allow_origins`가 localhost 목록으로 하드코딩되어 있어 실제 배포 시 프론트엔드 요청이 차단됩니다.

- [x] 허용 origin을 환경 변수(`CORS_ORIGINS` 등)로 주입
- [x] `env_example`에 항목 추가

### 2.4 테스트 자원 정리

- [x] Hypothesis 및 일부 SQLite 경로에서 발생하는 `ResourceWarning: unclosed database` 원인 추적 및 fixture 구조 점검

완료 기준: `cd backend && uv run pytest` 실행 시 경고가 발생하지 않아야 합니다.

### 2.5 저커버리지 모듈 테스트 보강

현재 전체 커버리지 90% 기준으로 남은 분기 중심 보강이 필요합니다.

- [x] `backend/app/services/grading_service.py` (79%): 컴파일/런타임 실패 상세 분기, 요약 메시지 조합, lint 반영 경계
- [x] `backend/app/core/system_settings.py`: 음수, 빈 string, key error 경계
- [x] `backend/app/core/config.py`: 환경 변수 파싱 및 기본값 경계
- [x] `backend/app/domains/homework/helpers.py`: artifact metadata 정규화 실패, testcase payload fallback, rule 활성/비활성, 언어 정책 JSON 손상 경계
- [x] `backend/app/api/dependencies.py`: 토큰 누락/손상/만료, 비활성 사용자, 권한 부족 분기
- [x] `backend/app/services/observability_service.py`, `notification_service.py`: payload 조합, 알림 누적/정렬/limit 경계

### 2.6 프론트엔드 품질 게이트

- [x] `package.json`에 `typecheck` 스크립트 추가 (`tsc --noEmit`)
- [x] 시험 UI e2e 커버리지 확장 (`frontend/e2e/exam.spec.ts`, 목록→응시→제출→결과 흐름)
- [x] 기존 e2e 스펙 기대값 정합화 — 전체 스위트 28/28 통과. 스펙 갱신과 함께 폼 label-input 연결(`htmlFor`/`id`, profile·admin homework), 아이콘 버튼 aria-label, AdminNoticeManager의 성공/오류 메시지 미표시 버그, 스냅샷 페이지 중첩 `<main>` 문제를 수정

## 3. 손쉬운 배포

### 3.1 프로덕션 Docker 이미지 (우선순위 높음)

- [x] `backend/Dockerfile`: `--reload` 제거, 프로덕션 uvicorn 구성 (채점 큐가 프로세스 내 상태를 사용하므로 단일 worker 유지, 사유는 `DEPLOY.md` 참고)
- [x] `frontend/Dockerfile`: `npm run dev` 대신 `next build` + standalone output 기반 멀티 스테이지 프로덕션 빌드
- [x] 소스 bind mount 없이 이미지 단독으로 동작하는지 확인 (`BACKEND_URL` 빌드 인자로 프록시 대상 주입)
- [ ] 채점 큐/rate limiter 상태를 외부 저장소로 이전한 뒤 다중 worker 확장

### 3.2 프로덕션 compose 구성

- [x] `docker-compose.prod.yml` 작성 (bind mount 제거, 프로덕션 이미지 사용)
- [ ] PostgreSQL 서비스 추가 및 `DATABASE_URL` 전환 (Testcontainers 스모크 테스트로 호환성은 이미 확인됨)
- [ ] reverse proxy(nginx 또는 Caddy) 및 TLS 구성
- [ ] 백엔드/프론트엔드 healthcheck 정의

### 3.3 시크릿 및 환경 변수 정비

- [x] `docker-compose.yml`의 `JWT_SECRET` 기본값 제거 또는 개발 전용임을 명시
- [x] `env_example`의 `"your-secret-key-here"` 등 약한 예시 값 정리 및 필수 항목 주석 보강
- [x] 프로덕션에서 `validate_security()`가 실제로 동작하는지 배포 환경 값으로 확인

### 3.4 CI 파이프라인 구축

`.github/workflows`가 현재 없습니다.

- [x] 백엔드: `uv run pytest` + 커버리지 하한 게이트 (`--cov-fail-under=85`)
- [x] 프론트엔드: `lint`, `typecheck`, `next build`
- [ ] Docker 이미지 빌드 검증
- [ ] Playwright e2e를 별도 lane으로 구성 (compose 기동 포함)
- [ ] Docker 가능 환경에서 Testcontainers Postgres 스위트 실행 lane 검토

### 3.5 운영 준비

- [x] DB 백업/복구 절차 (SQLite 볼륨 또는 Postgres 덤프)
- [x] 배포 절차 문서화 (`README.md` 또는 별도 `DEPLOY.md`)
- [ ] 구조화 로깅 및 오류 추적(Sentry 등) 도입 검토

## 4. 현재 참고 지표 (2026-07-24 재측정)

- 백엔드 테스트: `cd backend && uv run pytest` → 193 passed, 2 skipped, `ResourceWarning` 0건
- 커버리지: `cd backend && uv run pytest --cov=app --cov-report=term-missing` → 전체 92% (`grading_service.py` 96%)
- 프론트엔드: `npm run lint`(오류 0건), `npm run typecheck`, `npm run build` 모두 통과
- E2E: `npm run test:e2e` → 28 passed (전 스펙 통과)
- 프로덕션 이미지: `docker build ./backend`, `docker build ./frontend` 모두 성공
- 기존 DB에 대한 `v0005` 마이그레이션 적용 검증 완료 (qa/자료실 테이블·컬럼 추가)
- Docker daemon 부재 환경에서는 `tests/core/test_testcontainers_postgres.py`가 skip 됩니다.
