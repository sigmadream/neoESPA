# neoESPA 기능 검증 및 코드 리뷰 (REVIEW1)

- 리뷰 일자: 2026-08-18
- 대상 커밋: `e85524d` (main, working tree clean)
- 대상 범위: `backend/` (FastAPI + SQLModel), `frontend/` (Next.js 16 / React 19), 배포 구성, 검증 하네스
- 방식: 전체 정적 리뷰 + 실행 검증(테스트 스위트, 타입/린트/포매팅, 계약 검사) + 개별 결함에 대한 PoC 재현

---

## 1. 요약

**기능 검증은 전부 통과했습니다.** 백엔드 테스트 269건 통과(13건은 nsjail 바이너리 부재로 정상 skip), 프론트엔드 타입체크 통과, OpenAPI 계약 호환, 마이그레이션 ↔ 모델 스키마 드리프트 0건입니다. API 라우트 152개 중 미인증 접근이 가능한 것은 8개이며 전부 공개가 타당한 엔드포인트입니다.

직전 사이클에서 눈에 띄게 좋아진 부분이 있습니다. **OS 비의존 컨테이너 검증 하네스**(`docker-compose.test.yml`, `backend/scripts/test.*`)와 **실제 nsjail 바이너리로 격리를 검증하는 테스트**(`tests/sandbox/test_nsjail_real.py`)가 추가되었고, Dockerfile이 multi-stage로 정리되어 런타임 이미지에서 테스트 코드가 빠졌습니다. `.dockerignore`에 `.env`가 추가된 것도 좋은 변화입니다. 관리자 콘솔은 탭 7개에서 15개로 확장되며 문제 뱅크·대회 운영·재채점·감사 로그까지 UI로 들어왔습니다.

다만 **인가(authorization) 계층에 서로 어긋나는 정의가 공존하는 문제**는 그대로 남아 있습니다. 아래 High 5건은 이번 리뷰에서 PoC로 실제 재현을 확인했으며, 재현 출력을 본문에 그대로 인용했습니다. 특히 다음 두 건은 배포 전 처리를 권합니다.

1. **관리자 API 호출 한 번으로 사용자·설정 관리 기능이 영구히 잠깁니다.** 복구 CLI가 없어 DB 직접 수정 외에는 되돌릴 방법이 없습니다. (H-1)
2. **권한이 0개로 정의된 `viewer` 역할이 모든 학생의 제출 소스코드를 열람합니다.** (H-2)

또한 이번에 추가된 재인증(step-up) UI는 **연결된 백엔드 경로가 동작하지 않는 상태**여서, 기능이 늘어난 만큼 새로 생긴 문제도 함께 정리했습니다. (H-6, M-1)

### 심각도별 집계

| 심각도 | 건수 | 항목 |
|---|---|---|
| High | 6 | H-1 ~ H-6 |
| Medium | 8 | M-1 ~ M-8 |
| Low | 9 | L-1 ~ L-9 |

---

## 2. 기능 검증 결과

모든 항목을 실제로 실행해 확인했습니다. 호스트에 `uv`가 없어 standalone 설치 후 진행했습니다.

| 검증 항목 | 명령 | 결과 |
|---|---|---|
| 백엔드 테스트 | `uv run pytest -q` | ✅ **269 passed, 13 skipped** (98.9s), 실패 0 |
| skip 사유 확인 | `uv run pytest -q -rs tests/sandbox` | ✅ 전부 `nsjail 바이너리가 없습니다` — 환경 의존 테스트의 정상 skip |
| 프론트엔드 타입체크 | `npx tsc --noEmit` | ✅ 오류 0 |
| 프론트엔드 린트 | `npx eslint .` | ⚠️ 오류 0 / **경고 18** (L-8) |
| 백엔드 포매팅 | `uv run black --check app tests` | ✅ 202개 파일 변경 없음 |
| OpenAPI 계약 | `python -m app.cli check-openapi --baseline openapi.json` | ✅ `{"compatible": true, "breaking_changes": []}` |
| 마이그레이션 ↔ 모델 | `apply_migrations` 결과와 `metadata.create_all` 결과 스키마 비교 | ✅ 테이블 차이 0, 컬럼 드리프트 0 |
| 라우트 인증 커버리지 | `app.routes` 순회하여 인증 의존성 유무 집계 | ✅ 152개 중 미인증 8개, 전부 공개가 타당 |

미인증 라우트 8개: `/api/ping`, `/health/live`, `/health/ready`, `/health/judge`, `/api/auth/login`, `/api/auth/register`, `/api/admin-auth/bootstrap`, `/api/admin-auth/invitations/accept`

### 검증하지 못한 범위

- **Playwright E2E (`frontend/e2e/*.spec.ts` 16개)**: 백엔드·프론트엔드 동시 기동과 브라우저 바이너리가 필요해 미실행입니다.
- **실제 nsjail 격리 (`sandbox-tests` 서비스)**: `privileged: true` + `cgroup: host` 컨테이너와 nsjail 소스 빌드가 필요합니다. 하네스 구성 자체는 리뷰했고 타당합니다.
- **프로덕션 컴포즈 기동**: `JUDGE_RUNTIME_VERSION` 등 필수 변수와 attestation 파일이 필요해 미실행입니다.

> 참고: `app/core/config.py`, `app/core/compression.py` 등의 `except OSError, ValueError:` 는 오타가 아니라 **PEP 758(Python 3.14+)의 괄호 없는 except 문법**입니다. 실행 환경(3.14.4)에서 정상 파싱을 확인했습니다. `requires-python = ">=3.14"`에 강하게 묶이므로 3.13 이하 툴체인에서는 구문 오류로 보인다는 점만 유의하면 됩니다.

---

## 3. High — 배포 전 처리 권장

### H-1. 역할 권한 API 호출 한 번으로 관리자 기능이 영구 잠김 (복구 불가)

**위치**: `backend/app/services/authorization_service.py:48`, `backend/app/domains/users/router.py:318-360`

`KNOWN_CAPABILITIES`는 `DEFAULT_ROLE_CAPABILITIES`에 실제로 등장하는 capability의 합집합으로 계산됩니다. 그런데 라우터가 요구하는 capability 중 **`user:manage`와 `settings:manage`는 어떤 역할의 기본 집합에도 없습니다.** 따라서 이 둘은 `KNOWN_CAPABILITIES`에 포함되지 않고, `replace_role_capabilities`의 검증(`requested - KNOWN_CAPABILITIES`)을 절대 통과할 수 없습니다.

```
backend KNOWN_CAPABILITIES count: 15
라우터가 요구하지만 API로 부여할 수 없는 capability:
   - settings:manage
   - user:manage
```

즉 이 두 권한은 오직 `*`를 가진 `admin` / `super_admin`만 보유할 수 있습니다. 그런데 `replace_role_capabilities`는 `super_admin`만 변경을 막고 **`admin` 역할은 변경을 허용합니다**. 관리자가 `admin` 역할의 권한을 명시적 목록으로 교체하는 순간 `*`가 사라지고, 그 목록에 `user:manage`를 넣을 수 없으므로 되돌릴 수도 없습니다.

**재현 (PoC 실행 결과)**

```
list users BEFORE                : 200
PUT /admin/roles/admin/capabilities: 200 ['grading:manual', 'homework:manage']
list users AFTER                 : 403
read settings AFTER              : 403
restore attempt                  : 403
```

**영향**: 전체 사용자 관리(역할 변경, 계정 활성화, 비밀번호 초기화, 대량 등록)와 시스템 설정 관리가 플랫폼 전체에서 영구 차단됩니다. `app/cli.py`의 서브커맨드를 확인했으나 **role capability를 복구하는 명령이 없어**, `sqlite3`로 `role_capabilities` 테이블을 직접 지우는 것 외에 복구 경로가 없습니다.

**완화 요인**: 프론트엔드의 `MANAGED_ROLES`(`frontend/src/lib/api.ts:1487`)에 `admin`과 `super_admin`이 빠져 있어, **관리자 콘솔 UI만 사용하는 한 이 상태를 만들 수 없습니다.** API를 직접 호출하거나 스크립트를 쓸 때만 발생합니다. 다만 UI 노출 여부는 서버 측 방어가 아니므로, 발생 가능성이 낮아졌을 뿐 심각도는 그대로입니다.

**권장 조치**
1. `KNOWN_CAPABILITIES`를 파생값이 아닌 **명시적 상수 집합**으로 정의하고 `user:manage`, `settings:manage`를 포함시킵니다.
2. `replace_role_capabilities`에서 `admin` 역할도 `super_admin`과 함께 변경 금지로 막거나, 최소한 결과적으로 `user:manage`를 잃게 되는 요청을 거부합니다.
3. 회귀 테스트로 "라우터가 요구하는 모든 capability ⊆ `KNOWN_CAPABILITIES`"를 강제합니다. 본 리뷰의 교차 검증 스크립트를 그대로 테스트로 옮기면 됩니다.
4. 안전망으로 `neoespa-admin reset-role-capabilities <role>` CLI를 추가합니다.

---

### H-2. 권한이 0개인 `viewer` 역할이 모든 학생의 제출 소스코드를 열람

**위치**: `backend/app/services/user_management.py:10-21`, `backend/app/domains/submissions/router.py:273,297`, `backend/app/domains/users/serializers.py:22`

"스태프"의 정의가 코드베이스에 **두 가지**로 존재합니다.

| 정의 | 값 | 사용처 |
|---|---|---|
| `require_staff` (`api/dependencies.py:87`) | `{admin, instructor, ta}` | 일부 관리 라우트 |
| `ADMIN_ROLES` / `is_staff()` | 위 3개 + `super_admin, problem_setter, reviewer, judge_operator, support, viewer` (총 9개) | 제출물 조회, 공지/자료 비공개 열람, 예정 과제·시험 열람, QA 게시글 수정·삭제 |

`DEFAULT_ROLE_CAPABILITIES`에서 `viewer`는 명시적으로 **`set()` (권한 없음)** 으로 정의되어 있는데도, `ADMIN_ROLES`에 포함된 탓에 스태프로 취급됩니다.

**재현 (PoC 실행 결과)**

```
viewer   caps=[] -> GET /submissions/1: 200 owner=alice
support  caps=['audit:read', 'observability:read', 'problem:data.read'] -> GET /submissions/1: 200 owner=alice
```

**영향**: 권한 없음으로 설계된 `viewer`가 임의 학생의 제출 소스코드 전문과 채점 피드백을 조회합니다. 동일 경로로 미공개 공지·자료, 시작 전 과제/시험, 타인 QA 게시글 수정·삭제까지 열립니다.

**권장 조치**: `ADMIN_ROLES`를 "관리 계열 역할 목록"(인증용)과 "스태프 판정"(인가용)으로 분리하십시오. 제출물 열람은 이미 있는 `grading:manual` 또는 신설 `submission:read.any` capability로 전환하는 것이 구조적으로 맞습니다. 최소 조치로는 `is_staff()`를 `{admin, instructor, ta, super_admin}`으로 좁히십시오.

---

### H-3. 협업 세션에 누구나 무단 참여·코드 열람·덮어쓰기 가능

**위치**: `backend/app/domains/collab/router.py:44-161`

- `list_collab_sessions`: 인증된 아무 사용자나 **모든 active 세션 목록**을 조회합니다.
- `join_collab_session`: 멤버십·초대 검증이 전혀 없습니다. 누구나 임의 `session_id`로 참여하며, 생성되는 `CollabParticipant`는 **`can_edit=True`** 입니다.
- 결과적으로 세션 생성 시 지정한 `participant_ids`가 실질적으로 아무 의미가 없습니다.

**재현 (PoC 실행 결과)** — `prof`가 `alice`만 지정해 만든 1:1 세션에 무관한 `mallory`가 접근:

```
uninvited can LIST               : True
uninvited JOIN                   : 200
uninvited OVERWRITE code         : 200 'OVERWRITTEN'
uninvited read chat history      : 200
```

**영향**: 1:1 멘토링 세션의 코드와 전체 채팅 이력이 전교생에게 노출되고, 진행 중인 공유 코드를 제3자가 임의로 덮어쓸 수 있습니다.

**권장 조치**: `join`에서 사전 등록된 `CollabParticipant` 행이 있는 경우에만 재입장을 허용하고 그 외에는 403을 반환하십시오. 공개형 세션이 필요하다면 `CollabSession`에 `visibility`(private/open) 컬럼을 추가해 명시적으로 구분하고, 신규 참여자의 `can_edit` 기본값을 `False`로 바꾸십시오. `list_collab_sessions`도 본인 참여 세션으로 제한해야 합니다.

---

### H-4. 비밀번호 정책 전무 + 로그인 시도 제한 없음

**위치**: `backend/app/models/schemas.py` (UserCreate / PasswordChangeRequest / AdminPasswordResetRequest), `backend/app/domains/auth/router.py:71-118`

`app/models/schemas.py` 전체에 **`field_validator` / `model_validator`가 0개**입니다(grep 확인). 비밀번호 관련 스키마에 길이·복잡도 제약이 전혀 없습니다.

**재현 (PoC 실행 결과)**

```
register 1-char password         : 200
change own password to 'a'       : 200
```

여기에 `/api/auth/login`에는 **rate limit도 계정 잠금도 없습니다.** 스냅샷(`SNAPSHOT_RATE_LIMIT_COUNT`)과 제출(`submission_rate_limit_per_minute`)에는 제한이 있는데 인증 경로에만 없는 비대칭 상태입니다.

**영향**: 1자리 비밀번호 계정이 만들어질 수 있고, 무제한 온라인 브루트포스가 가능합니다. 샘플 계정(`admin / pllab2026`)이 문서에 공개되어 있어 운영 시 위험이 배가됩니다.

**권장 조치**
1. `PasswordPolicy` 검증기(최소 10자 + 문자군 혼합 등)를 만들어 register / change-password / reset-password / bulk-create 네 경로에 모두 적용하십시오. 서비스 계층(`user_management.create_managed_user`)에 두면 우회 경로가 생기지 않습니다.
2. 로그인 실패 카운터를 두고 IP·계정 단위 지연 또는 일시 잠금을 적용하십시오.

---

### H-5. 테스트케이스마다 소스를 다시 컴파일 (채점 시간 N배)

**위치**: `backend/app/services/grading_service.py:188-211`

`_grade_with_test_cases`는 테스트케이스 루프 안에서 `runner.run_code(...)` / `run_code_with_limits(...)`를 호출합니다. 이 메서드는 **매번 임시 디렉터리를 새로 만들고 소스를 쓰고 컴파일한 뒤 실행**합니다.

**재현 (PoC 실행 결과)** — `gcc` 호출 횟수 계측:

```
test cases=8  gcc compiles=8 (needed: 1)  program runs=8
duplicated compile-log entries: 8
```

**영향**: 채점 비용이 `N × (컴파일 + 실행)`입니다. C++ `-O2` 컴파일이 1~3초인 과제에 테스트케이스 50개면 컴파일에만 50~150초가 소요되며, 실제 실행 시간은 그중 일부입니다. 마감 직전 제출이 몰릴 때 채점 큐 적체의 직접적 원인이 됩니다. 동일한 컴파일 경고가 로그에 N번 중복 기록되는 것도 같은 원인입니다. nsjail 경로(`NsJailCodeRunner.run_code_with_limits`)도 구조가 같아 똑같이 영향을 받습니다.

**권장 조치**: 컴파일과 실행을 분리하십시오. `CodeRunner`에 `prepare(language, source) -> Workspace` / `execute(workspace, input_data, limits)` 형태의 2단계 인터페이스를 두고 워크스페이스 하나를 케이스 루프 전체에서 재사용합니다. 컴파일 실패를 루프 진입 전에 한 번만 판정하면 되므로 현재의 조기 반환 로직도 단순해지고, 컴파일 로그 중복도 자연히 해소됩니다.

---

### H-6. 재인증(step-up) UI가 동작하지 않는 백엔드 경로에 연결됨 (신규)

**위치**: `frontend/src/components/StepUpDialog.tsx`, `frontend/src/components/AuthProvider.tsx:184-193`, `backend/app/api/dependencies.py:100-125`, `backend/app/domains/auth/router.py:140-166`

이번에 재인증 UI(`StepUpDialog`)와 `AuthProvider.stepUp`이 추가되고 `AdminRoleManager`·`AdminInvitationManager`가 이를 사용합니다. 그런데 연결된 백엔드 경로에 세 가지 문제가 겹쳐 있습니다.

**재현 (PoC 실행 결과)**

```
[A] login token lifetime      : 24.0 h
[B] step-up 없이 민감 작업(PUT role caps) -> 200   (재인증이 실제로 요구되지 않음)
[C] step-up token lifetime    : 10.0 min   claims=['amr','auth_time','exp','role','step_up_until','sub']
    -> 프론트엔드는 세션 토큰을 이 토큰으로 "교체"한다
[D] mfa_required=True 설정 후 POST /auth/step-up -> 403 MFA verification provider is not configured
    민감 작업                  -> 403 Recent step-up authentication is required  (토큰 획득 경로 없음)
```

1. **[B] 기본 상태에서 재인증이 강제되지 않습니다.** `require_step_up`은 `AdminAuthAssurance` 행이 없거나 `mfa_required`가 아니면 그대로 통과시킵니다. 역할 변경, 비밀번호 초기화, 대량 계정 생성, 관리자 초대 발급 등 최고 위험 작업이 일반 액세스 토큰만으로 수행됩니다. 즉 UI 다이얼로그는 실제로 열릴 일이 없습니다.
2. **[C] 재인증하면 관리자가 10분 뒤 로그아웃됩니다.** `AuthProvider.stepUp`이 24시간짜리 세션 토큰을 10분짜리 step-up 토큰으로 **교체**하고(`writeStoredSession({ token: elevated.access_token, user })`), 원래 토큰을 복원하지 않습니다. 재인증이 실제로 요구되는 순간 관리자 세션 수명이 10분으로 줄어듭니다.
3. **[D] 재인증을 켜면 해당 엔드포인트가 영구히 잠깁니다.** `mfa_required = True`로 설정하면 `/api/auth/step-up`이 항상 403을 반환해 step-up 토큰을 발급받을 방법이 없고, 그 결과 step-up으로 보호된 모든 엔드포인트를 쓸 수 없게 됩니다.

**권장 조치**
1. MFA 제공자 연동 전까지는 "비밀번호 재확인 기반 step-up"이 실제로 동작하도록, `mfa_required`와 무관하게 `/auth/step-up`이 토큰을 발급하고 `require_step_up`이 유효한 `step_up_until`을 요구하게 바꾸십시오.
2. 프론트엔드는 step-up 토큰을 세션과 **별도로** 보관하고(예: 메모리 내 `elevatedToken`), 민감 요청에만 사용한 뒤 만료 시 원래 세션으로 자연히 되돌아가게 하십시오.
3. 위 정리 전까지는 재인증 UI가 사실상 죽은 코드라는 점을 문서에 명시하는 편이 낫습니다.

---

## 4. Medium

### M-1. 역할 권한 편집 UI에 저장이 항상 실패하는 체크박스가 있음 (신규)

**위치**: `frontend/src/lib/api.ts:1454-1471`, `frontend/src/components/admin/AdminRoleManager.tsx:45`, `backend/app/domains/users/router.py:333-336`

프론트엔드 `KNOWN_CAPABILITIES`는 **16개**이고 `user:manage`("사용자 관리")를 포함합니다. 백엔드 `KNOWN_CAPABILITIES`는 **15개**이며 `user:manage`를 포함하지 않습니다(H-1과 같은 원인).

**재현 (PoC 실행 결과)**

```
frontend KNOWN_CAPABILITIES : 16
backend  KNOWN_CAPABILITIES : 15
in frontend list but backend rejects: ['user:manage']

UI 시나리오: 조교(ta) 역할에 '사용자 관리' 체크 후 저장
  -> 400 Unknown or unsafe capability
```

운영자가 역할 권한 화면에서 "사용자 관리"를 체크하고 저장하면 항상 400이 나며, 오류 메시지에 **어떤 capability가 문제인지 나오지 않아** 원인을 알 수 없습니다. H-1을 고치면 함께 해소되지만, 그 전까지는 프론트 목록에서 `user:manage`를 제거하거나 비활성 표시하고, 백엔드 오류 메시지에 거부된 항목명을 포함시키십시오.

### M-2. CSV 수식 인젝션 (학생이 자기 프로필로 주입 가능)

**위치**: `backend/app/services/export_service.py:22-135`

`build_grade_csv`가 `user.name`, `user.email`, `homework.title`을 이스케이프 없이 기록합니다. 학생은 `PATCH /api/users/me`로 자기 이름을 자유롭게 바꿀 수 있습니다.

**재현 (PoC 실행 결과)**

```
PATCH /users/me formula name     : 200 "=cmd|' /c calc'!A1"
exported CSV name cell           : "=cmd|' /c calc'!A1" | formula trigger: True
```

**영향**: 교수·조교가 성적 CSV를 Excel/LibreOffice로 열면 DDE 수식이 실행될 수 있습니다. 성적 산출은 반드시 스태프가 수행하는 작업이므로 표적이 명확합니다.

**권장 조치**: CSV 셀 값이 `=`, `+`, `-`, `@`, 탭, 캐리지리턴으로 시작하면 앞에 `'`를 붙이는 sanitize 헬퍼를 만들어 모든 문자열 셀에 적용하십시오. `UserProfileUpdate.name`에 제어문자 금지 검증을 추가하는 것도 권합니다.

### M-3. `super_admin` 계정이 관리자 콘솔에 전혀 진입할 수 없음

**위치**: `frontend/src/app/admin/page.tsx:64-86`, `frontend/src/components/AuthGate.tsx:32-38`

`<AuthGate roles={['admin', 'instructor', 'ta']}>` 로 하드코딩되어 `super_admin` 사용자는 `/`로 리다이렉트됩니다. 탭 노출 규칙(`ADMIN_ONLY_TABS`, `INSTRUCTOR_TABS`)도 역할 문자열을 직접 비교하므로 `super_admin`은 **15개 탭 중 하나도** 볼 수 없습니다. 백엔드는 `super_admin`에게 `*` 권한을 부여하고 `update_user_role`로 승격도 가능한데, 정작 UI에서는 최고 권한 계정이 콘솔을 못 씁니다. `/admin/snapshots/[homework_num]/[user_id]/page.tsx:76`도 동일합니다.

**권장 조치**: 이번 개편에서 탭↔capability 매핑을 주석으로 정리한 것은 좋은 방향입니다. 이제 한 걸음 더 나아가 `/api/users/me` 응답에 **유효 capability 목록**을 실어 보내고 UI가 그것으로 노출을 결정하게 하십시오. 즉시 조치로는 세 곳 모두에 `super_admin`을 추가하면 됩니다.

### M-4. 표절 검사가 O(N²) 동기 실행이며, 이중 루프 안에서 매번 압축 해제

**위치**: `backend/app/services/plagiarism_service.py:196-209`, `backend/app/domains/plagiarism/router.py:17-31`

`left_code`는 바깥 루프에서 한 번만 계산하면 되는데 안쪽 루프에서 매번 재계산됩니다.

**재현 (PoC 실행 결과)** — `decompress_text` 호출 횟수 계측:

```
[plagiarism] submissions=21  decompress_text calls=441  (minimum needed: 21)
```

제출 21건에 441회, 즉 **21배**입니다. 제출 200건이면 약 40,000회가 됩니다. 여기에 `SequenceMatcher`가 소스 길이에 대해 다시 O(n²)이라 전체 비용이 급격히 커집니다. 게다가 이 작업은 HTTP 요청 안에서 동기적으로 완료됩니다. 이미 `judge_jobs` 기반 비동기 큐가 구축되어 있는데 표절 검사만 이를 사용하지 않습니다.

**권장 조치**: 정규화된 소스를 루프 진입 전에 한 번만 계산해 보관하십시오(이것만으로 큰 개선). 이어서 표절 검사를 `judge_job_service.enqueue`로 옮겨 비동기 실행하고, 이미 존재하는 `PlagiarismRun.status`를 `running → completed`로 전이시키십시오. 토큰 해시 기반 사전 필터를 두면 O(N²) 상수도 크게 낮출 수 있습니다.

### M-5. 사용자 입력 크기 제한 누락 (스냅샷 / 협업 코드)

**위치**: `backend/app/models/schemas.py` (CodeSnapshotCreate), `backend/app/domains/submissions/router.py:318-350`, `backend/app/domains/collab/router.py:329-350`

제출(`create_submission`)에는 `submission_max_source_bytes` 검증이 있지만 다음 경로에는 크기 제한이 전혀 없습니다.

- `CodeSnapshotCreate.code_text` — 자동 저장이 분당 20회 허용되므로 대용량 페이로드를 반복 저장할 수 있습니다.
- WebSocket `code_update` 메시지 — `str(message.get("code", ""))`를 그대로 저장하며, **매 업데이트마다 `CollabCodeSnapshot` 행을 하나씩 생성**합니다.

**권장 조치**: `submission_max_source_bytes`를 스냅샷과 협업 코드에도 공통 적용하고, WebSocket 메시지에 크기 상한과 스냅샷 생성 디바운스(예: N초당 1회)를 두십시오.

### M-6. WebSocket 핸들러의 세션·권한·연결 수명 관리

**위치**: `backend/app/domains/collab/router.py:275-367`, `backend/app/services/collab_ws.py`

1. **DB 세션 점유**: `Depends(get_session)`가 WebSocket 연결이 유지되는 **내내** DB 세션 하나를 붙잡습니다. 동시 접속자가 늘면 커넥션 풀이 고갈됩니다.
2. **권한 스냅샷 고착**: `participant`를 연결 시점에 한 번 읽고 재확인하지 않습니다. 멘토가 `can_edit`를 회수해도 이미 열린 소켓은 계속 편집할 수 있고, `user.is_active`도 연결 시점에만 확인하므로 비활성화된 계정의 소켓이 살아남습니다.
3. **연결 누수**: `except WebSocketDisconnect` 만 처리합니다. 클라이언트가 잘못된 JSON을 보내면 `receive_json()`이 `JSONDecodeError`를 던지고 그대로 전파되어 `_connections`에서 소켓이 제거되지 않습니다.
4. **다중 워커 불가**: `CollabConnectionManager`가 프로세스 내 dict입니다. 워커 2개 이상이나 다중 레플리카에서는 브로드캐스트가 워커 경계를 넘지 못해 협업 기능이 조용히 깨집니다. Dockerfile이 `--workers 1`로 고정된 이유로 보이나 이 제약이 코드에 명시되어 있지 않습니다.

**권장 조치**: (1) 요청 단위로 짧게 세션을 열고, (2) 각 메시지 처리 전에 참가자·계정 상태를 재확인하며, (3) `try/finally`로 `disconnect`를 보장하고 `Exception`을 폭넓게 처리하십시오. (4) 다중 워커가 필요해지면 Redis pub/sub 등 외부 브로커로 전환하되, 그전까지는 `--workers 1` 제약을 README에 명시하십시오.

### M-7. 프론트엔드가 백엔드의 에러 봉투(error envelope)를 무시

**위치**: `frontend/src/lib/api.ts:417-455`

백엔드는 `main.py`에서 `{detail, code, message, field_errors, request_id}` 형태의 일관된 에러 봉투를 내려줍니다. 그런데 프론트는 여전히 이렇게 처리합니다.

```ts
const detail = typeof payload === "object" && payload !== null && "detail" in payload
    ? String(payload.detail) : "Request failed";
throw new Error(detail);
```

422 검증 오류에서 `detail`은 **객체의 배열**이므로 `String(...)` 결과는 `"[object Object]"`입니다. 백엔드가 준비한 `message`와 `field_errors`는 완전히 버려집니다. 이번에 `allowNotFound` 옵션이 추가되었지만 봉투 활용은 그대로입니다. 또한 401(토큰 만료) 공통 처리가 없어 세션 만료 시 로그인 화면으로 유도되지 않습니다. 이는 M-1의 "무엇이 거부됐는지 알 수 없다" 증상과도 직결됩니다.

**권장 조치**: `message`를 우선 사용하고 `field_errors`를 필드별 메시지로 매핑하는 `ApiError` 클래스를 도입하십시오. `request_id`를 함께 보관하면 장애 문의 시 서버 로그와 즉시 대조할 수 있습니다. 401에서는 세션을 비우고 `/login`으로 보내는 공통 처리를 추가하십시오.

### M-8. JWT를 localStorage에 저장하며 보안 헤더가 전혀 없음

**위치**: `frontend/src/components/AuthProvider.tsx:48-80`, `frontend/next.config.ts`, `backend/app/main.py`

- 액세스 토큰이 `localStorage['neoespa.auth.session']`에 평문 저장되어 XSS로 탈취 가능합니다. 만료는 24시간이고 서버 측 무효화 수단이 없어, 비밀번호를 변경해도 기존 토큰은 계속 유효합니다.
- `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security` 중 어느 것도 백엔드 미들웨어와 `next.config.ts` 양쪽에 설정되어 있지 않습니다(grep 확인).

현재 XSS 표면 자체는 좁습니다(`dangerouslySetInnerHTML` 사용 0건, `react-markdown`은 기본적으로 raw HTML을 이스케이프). 그래도 방어 계층이 하나뿐인 상태입니다.

**권장 조치**: `next.config.ts`의 `headers()`에 CSP와 기본 보안 헤더를 추가하십시오. 중기적으로는 토큰을 `httpOnly` + `SameSite=Strict` 쿠키로 옮기고, 비밀번호 변경 시 기존 토큰이 무효화되도록 사용자 레코드에 토큰 세대(generation) 값을 두는 것을 권합니다.

---

## 5. Low / 개선 제안

| ID | 내용 | 위치 |
|---|---|---|
| **L-1** | 로그인 시 사용자가 없으면 bcrypt 검증을 건너뛰어 응답 시간 차이로 **계정 존재 여부를 알 수 있습니다.** 더미 해시로 항상 검증을 수행해 시간을 균일화하십시오. | `domains/auth/router.py:80-83` |
| **L-2** | `list_admin_users`가 **전체 사용자를 메모리로 로드한 뒤 파이썬에서 검색·필터**합니다. 페이지네이션도 없습니다. 검색·필터·페이징을 SQL로 내리십시오. | `domains/users/router.py:71-107` |
| **L-3** | `list_homeworks`가 DB에서 `limit/offset`을 적용한 뒤 파이썬에서 `upcoming` 과제를 제거합니다. **페이지마다 반환 개수가 달라지고 항목이 누락**됩니다. 가시성 조건을 SQL WHERE로 옮기십시오. | `domains/homework/router.py:184-211` |
| **L-4** | 대회 참가 코드가 **솔트 없는 단일 SHA-256**으로 저장되고(`hashlib.sha256(code).hexdigest()`), 참가 시도에 **rate limit이 없습니다.** 비교 자체는 `hmac.compare_digest`로 안전합니다. 코드 추측 시도 제한을 추가하십시오. | `domains/contests/router.py:355-380` |
| **L-5** | `env_example`의 `JWT_SECRET="your-secret-key-here-must-be-32-bytes"`가 **37자라 32자 검증을 통과합니다.** 그대로 복사해도 경고 없이 부팅되어 공개된 시크릿으로 운영될 위험이 있습니다. 플레이스홀더 문자열 자체를 거부하십시오. | `env_example:23`, `core/config.py:181-197` |
| **L-6** | multi-stage 정리는 개선되었으나 **런타임 이미지가 여전히 root로 실행**되며(`USER` 지시자 없음), 채점에 쓰지 않는 `gcc/g++/make`를 `base`에서 그대로 상속합니다. 프로덕션에서는 `HOST_CODE_EXECUTION_ALLOWED`가 항상 False이므로 API 이미지에 컴파일러가 필요 없습니다. | `backend/Dockerfile` |
| **L-7** | `/health/judge`가 **인증 없이** `sandbox_ready`, `automatic_grading_enabled`, 온라인 워커 ID 목록을 노출합니다. 상세 필드는 인증 뒤로 옮기고 공개 응답은 ready/not_ready만 남기십시오. | `main.py:66-88` |
| **L-8** | ESLint 경고 18건(오류 0). 미사용 import 다수와 `react-hooks/exhaustive-deps` 다수입니다. 후자는 관리자 화면들이 `useEffect`에서 로더 함수를 참조하면서 의존성에 넣지 않은 패턴으로 데이터 갱신 누락의 씨앗입니다. `AdminRoleManager`처럼 `useCallback`으로 감싸는 방식이 이미 코드베이스에 있으니 그 패턴으로 통일하십시오. | `components/admin/*.tsx` |
| **L-9** | 테스트케이스가 `grading_rules` 한 행의 **JSON blob**(`rule_name="testcases"`)으로 저장됩니다. 개별 케이스 조회·수정·통계가 불가능하고 동시 수정 시 통째로 덮어쓰기가 발생합니다. 이미 `ProblemTestCase` 테이블이 있으므로 그쪽으로 통합하는 방향이 자연스럽습니다. | `services/grading_service.py:478-540` |

---

## 6. 잘 되어 있는 점

리뷰 과정에서 확인한 강점입니다. 유지할 가치가 있습니다.

- **검증 하네스가 이번에 크게 좋아졌습니다.** `docker-compose.test.yml`은 `network_mode: none`으로 네트워크를 끊고, `PYTHONPYCACHEPREFIX`로 호스트 `__pycache__` 영향을 차단하며, `supportFiles`를 named build context로 이미지에 구워 바인드 마운트 없이 재현합니다. `NEOESPA_SUPPORT_DIR`을 일부러 설정하지 않아 탐색 로직까지 검증되게 한 판단도 좋습니다. `LANG`/`TZ` 고정으로 로케일 의존성까지 제거했습니다.
- **샌드박스를 mock 없이 실제로 검증하기 시작했습니다.** `tests/sandbox/test_nsjail_real.py`가 운영과 동일한 `privileged` + `cgroup: host` 환경에서 실제 nsjail로 격리를 확인하고, 바이너리가 없는 환경에서는 명확한 사유와 함께 skip합니다. 환경 의존 테스트를 다루는 좋은 방식입니다.
- **Dockerfile multi-stage 분리가 적절합니다.** 런타임 이미지에서 `tests`가 빠졌고 `.dockerignore`에 `.env`가 추가되었습니다. `COPY . .` 대신 필요한 경로만 명시적으로 복사합니다.
- **채점 잡 큐의 동시성 처리가 정확합니다.** `claim_next`가 SQLite에서 `BEGIN IMMEDIATE`로 직렬화한 뒤 `UPDATE ... WHERE status='queued'` + `rowcount != 1` 검사로 조건부 클레임을 수행합니다. 리스 만료 회수와 `max_attempts` 초과 시 dead-letter 전이까지 갖췄습니다.
- **아티팩트 저장소가 견고합니다.** SHA-256 콘텐츠 주소화, 스테이징 → `os.replace` 원자적 이동, `fsync`, 동일 파일시스템 검사, `resolve()`의 경로 탈출 차단, 실패 트랜잭션에서 중복 객체를 지우지 않는 `was_created` 구분까지 세심합니다.
- **ZIP 파서에 zip-slip 방어가 제대로 들어 있습니다.** `..`·절대경로·역슬래시·Windows 드라이브 문자를 거부하고 `Path(name).name`만 취하며, 아카이브 크기·전개 크기·케이스 개수 상한을 모두 둡니다.
- **샌드박스가 fail-closed로 설계되었습니다.** `HOST_CODE_EXECUTION_ALLOWED`가 프로덕션에서 무조건 False이고, `SANDBOX_READY`는 attestation의 정책 해시·런타임 버전·6종 적대적 픽스처 결과가 전부 일치해야만 True가 됩니다.
- **마이그레이션과 모델이 완전히 일치합니다.** v0001~v0025 적용 결과와 `metadata.create_all` 결과 사이에 테이블·컬럼 차이가 0건입니다.
- **인증 커버리지가 좋습니다.** 라우트가 152개로 늘었는데도 미인증 접근 가능한 것은 여전히 8개, 전부 공개가 타당한 엔드포인트입니다.
- **버그 수정에 회귀 테스트가 함께 들어왔습니다.** `replace_role_capabilities`의 flush 순서 문제를 고치면서 `test_role_capabilities_can_be_replaced_with_overlapping_set`를 추가하고, 주석에 원인(UNIQUE 제약 위반)까지 남겼습니다.
- **관리자 UI 노출 규칙을 백엔드 권한과 맞추려는 의도가 코드에 드러납니다.** `admin/page.tsx`의 탭↔capability 매핑 주석이 그 예입니다. 다음 단계로 실제 capability 기반 제어까지 가면 M-3이 함께 해소됩니다.

---

## 7. 권장 조치 순서

**1단계 — 배포 차단 항목**

1. H-1 `KNOWN_CAPABILITIES`에 `user:manage`, `settings:manage` 추가 + `admin` 역할 변경 차단 + 회귀 테스트 (M-1도 함께 해소)
2. H-2 `ADMIN_ROLES`와 `is_staff()` 분리, 제출물 열람을 capability 기반으로 전환
3. H-3 협업 세션 참여에 멤버십 검증 추가, `can_edit` 기본값 `False`
4. H-4 비밀번호 정책 검증기 도입 + 로그인 시도 제한
5. H-6 step-up을 실제 동작하게 만들고, 프론트가 세션 토큰을 덮어쓰지 않도록 수정

**2단계 — 운영 안정성**

6. H-5 컴파일/실행 분리 (채점 처리량에 직접 영향)
7. M-4 표절 검사 정규화 캐싱 + 비동기 잡 전환
8. M-5 스냅샷·협업 코드 크기 제한
9. M-6 WebSocket 세션·권한·연결 정리
10. M-2 CSV sanitize
11. M-3 `super_admin` UI 접근 복구 (capability 기반 노출로 전환)

**3단계 — 하드닝 및 정리**

12. M-7 프론트엔드 에러 봉투 활용 + 401 공통 처리
13. M-8 보안 헤더 추가, 토큰 저장 방식 재검토
14. L-1 ~ L-9 순차 처리

---

## 부록. 검증 재현 방법

```bash
# 백엔드 (컨테이너 — OS 무관, 프로젝트가 제공하는 하네스)
./backend/scripts/test.sh
SERVICE=format ./backend/scripts/test.sh

# 백엔드 (호스트에 uv가 있는 경우)
cd backend && uv sync && uv run pytest -q
uv run black --check app tests
uv run python -m app.cli check-openapi --baseline openapi.json

# 프론트엔드
cd frontend && npm ci && npx tsc --noEmit && npx eslint .
```

H-1 ~ H-6, M-1, M-2, M-4의 PoC 스크립트는 `tests/conftest.py`와 동일하게 인메모리 SQLite + `TestClient`를 사용하고
`app.dependency_overrides[get_session]`로 세션을 주입하는 방식입니다. 각 항목의 재현 출력은 본문에 그대로 인용했습니다.
