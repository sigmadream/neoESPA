# 백엔드 코드 리뷰 가이드

도메인 라우터부터 열면 매번 모델과 권한 헬퍼를 찾아 거슬러 올라가야 하므로 왕복이 급격히 늘어납니다.

```text
계약 → 설정 → 데이터 모델 → 권한 → 서비스 → 라우터 → 테스트
```

## 1단계 - 진입점과 설정

| 순서 | 파일                 | 줄  | 확인할 것                                    |
| ---- | -------------------- | --- | -------------------------------------------- |
| 1    | `app/core/config.py` | 170 | 모든 환경변수의 단일 창구. 기본값이 안전한가 |
| 2    | `app/main.py`        | -   | 미들웨어, 예외 핸들러, lifespan              |
| 3    | `app/api/router.py`  | 66  | 도메인 라우터 조립 방식                      |
| 4    | `app/api/runtime.py` | 20  | 전역 싱글턴 서비스 인스턴스                  |

1. `config.py:154` `validate_security()` - production에서 `JWT_SECRET` 미설정 또는 32자 미만이면 기동을 거부합니다. 이 검사가 lifespan에서 실제로 호출되는지 `main.py`에서 확인하십시오.
2. `config.py:137` `SECRET_KEY`는 개발 편의를 위한 하드코딩 fallback을 가집니다. 위 검사가 production을 막아주지만, fallback 값 자체가 저장소에 남아 있는 것이 정책상 허용되는지 판단이 필요합니다.
3. `main.py`의 예외 핸들러 2개가 만드는 오류 envelope는 [API.md](./API.md)의 "오류 응답 규격"에 문서화돼 있습니다. 실제 코드와 문서가 일치하는지 대조하십시오.
4. `runtime.py`의 서비스가 전역 싱글턴입니다. 상태를 들고 있다면 워커 다중화 시 문제가 될 수 있습니다.

## 2단계 - 데이터 모델과 마이그레이션

| 순서 | 파일                    | 줄         |
| ---- | ----------------------- | ---------- |
| 5    | `app/models/schemas.py` | 1,791      |
| 6    | `app/migrations/`       | 627 (26개) |

`schemas.py` 하나에 모든 테이블과 요청/응답 스키마가 들어 있습니다. 전부 읽지 마시고 1단계에서 파악한 핵심 엔티티(User, Homework, Submission, Problem, ProblemRevision, JudgeJob)만 먼저 보십시오.

1. 마이그레이션은 순차 적용 방식입니다. `app/core/migrations.py`(80줄)에서 적용·기록 방식을 먼저 본 뒤 개별 마이그레이션을 보십시오.
2. 마이그레이션은 SQLite에서만 검증합니다. 다른 엔진 호환성 검증 테스트는 이번 정리에서 제거됐습니다 (아래 "판단이 필요한 사항" 참조).

## 3단계 - 권한과 인증

| 순서 | 파일                                           | 줄       |
| ---- | ---------------------------------------------- | -------- |
| 7    | `app/api/dependencies.py`                      | 145      |
| 8    | `app/services/user_management.py`              | -        |
| 9    | `app/domains/auth/`, `app/domains/admin_auth/` | 197 + 92 |

이 단계가 리뷰의 핵심입니다. 145줄짜리 `dependencies.py`가 전체 API의 접근 제어를 결정합니다.

| 의존성                                         | 용도               |
| ---------------------------------------------- | ------------------ |
| `get_current_user` / `get_current_active_user` | 인증               |
| `require_roles(*roles)`                        | 역할 기반          |
| `require_capability(capability)`               | 세분화된 권한      |
| `require_staff`                                | 스태프 전용        |
| `require_step_up(capability)`                  | 위험 작업의 재인증 |

1. 각 게이트가 실패 시 401과 403을 올바르게 구분하는가
2. `require_capability`가 문제 소유권 범위까지 검사하는가, 아니면 라우터가 별도로 해야 하는가 (`app/domains/problems/router.py`의 `_authorize_problem_scope` 참조)
3. `get_optional_current_user`를 쓰는 엔드포인트에서 비로그인 사용자에게 노출되는 데이터 범위

## 4단계 - 핵심 서비스

| 순서 | 파일                                | 줄  | 성격                   |
| ---- | ----------------------------------- | --- | ---------------------- |
| 10   | `app/services/judge_job_service.py` | 687 | 작업 큐, lease, 재시도 |
| 11   | `app/services/grading_service.py`   | 693 | 채점 본체              |
| 12   | `app/services/code_runner.py`       | 360 | 코드 실행 (보안 임계)  |
| 13   | `app/services/lint_pipeline.py`     | 395 | 정적 분석              |
| 14   | `app/services/feedback_service.py`  | 183 | 피드백 생성            |

1. `code_runner.py`는 학생이 제출한 코드를 실행합니다. 샌드박스 경계, 자원 제한, 타임아웃을 가장 꼼꼼히 보셔야 합니다. `config.py`의 `SANDBOX_READY`는 attestation 파일의 `runtime_version`이 `JUDGE_RUNTIME_VERSION`과 일치할 때만 참이 됩니다 - 이 연동이 우회 가능한지 확인하십시오.
2. `judge_job_service.py:114`에 SQLite 전용 분기가 있습니다 (`dialect.name == "sqlite"`). 트랜잭션 처리 차이가 다른 엔진에서 어떻게 동작할지 확인이 필요합니다.
3. 큐의 lease 만료와 재시도가 중복 채점을 만들지 않는지.

## 5단계 - 도메인 라우터

| 도메인        | 줄            | 비고                                  |
| ------------- | ------------- | ------------------------------------- |
| `homework`    | 1,246         | 가장 큼. ZIP 임포트/엑스포트 포함     |
| `problems`    | 1,062         | revision 수명주기, 승인, 테스트케이스 |
| `jobs`        | 555           |                                       |
| `submissions` | 461           |                                       |
| `contests`    | 452           |                                       |
| `collab`      | 442           | WebSocket 포함                        |
| `users`       | 370           |                                       |
| `grading`     | 324           |                                       |
| 나머지 13개   | 각 200줄 미만 | 패턴이 반복됨. 1~2개만 표본 확인      |

1. `homework`의 ZIP 파싱 - 업로드 파일을 다루므로 zip slip, 압축 폭탄, 경로 탈출을 확인하십시오.
2. `problems`의 revision 상태 전이 - draft에서만 테스트 데이터가 바뀌어야 합니다.
3. `collab/router.py:239`의 WebSocket은 OpenAPI에 노출되지 않습니다. 즉 `check-openapi` 계약 검사의 사각지대이므로 눈으로 확인해야 합니다. 인증은 query parameter `token`으로 하고 실패 시 close code 4401을 보냅니다.

## 6단계 - 운영 도구

| 파일                                           | 줄  |
| ---------------------------------------------- | --- |
| `app/cli.py`                                   | 320 |
| `deploy/nsjail.cfg`, `deploy/Dockerfile.judge` | -   |
| `Dockerfile`, `../docker-compose.prod.yml`     | -   |

CLI 14개 명령의 목록과 용도는 [README.md](./README.md)의 표에 있습니다. 운영자가 직접 실행하므로 파괴적 명령(`restore-course-bundle`)의 안전장치를 확인하십시오.

## 7단계 - 테스트

카테고리별 구성은 [README.md](./README.md)에 정리돼 있습니다. 전부 읽기보다 커버리지가 낮은 영역과 아래 두 파일을 보십시오.

- `tests/core/test_openapi_contract.py` - 문서와 runtime router의 일치를 강제합니다
- `tests/sandbox/test_nsjail_contract.py` - mock 기반 스펙 검증 (모든 OS에서 실행)
- `tests/sandbox/test_nsjail_real.py` - 실제 nsjail로 격리를 실행 검증 (`sandbox-tests` 서비스 전용, 그 외 환경에서는 skip)

샌드박스 정책(`deploy/nsjail.cfg`)은 이제 mock 없이 실제로 실행되며, 그 과정에서 드러난 결함을 수정했습니다. 상세는 [README.md](./README.md)의 "샌드박스(nsjail) 실검증"을 참고하십시오.

---

## 이번 변경에서 특히 봐주셨으면 하는 것

### 1. 스펙 검증 절차의 순서

[API.md](./API.md)의 "스펙 검증"에서 `export-openapi`가 검증 시퀀스에서 빠졌습니다. 이전 문서는 `export` 다음에 `check`를 실행하도록 안내했는데, `export`가 git에 추적되는 기준선을 현재 스키마로 덮어쓰므로 `check`가 현재 스키마를 자기 자신과 비교하게 되어 항상 통과했습니다. 기준선 갱신은 이제 별도 단계입니다. 이 절차를 CI에 넣을 때 순서가 다시 뒤집히지 않도록 강제할 방법이 필요한지 확인해야 합니다.

### 2. 하위호환 별칭 route 2개 제거

`app/domains/problems/router.py`에서 `import_testcase_package` 한 함수에 3개의 경로가 쌓여 있었고, 그중 `include_in_schema=False`인 2개(`.../package`, `.../testcases/import`)를 제거했습니다. 저장소 전체에서 호출자가 없음을 확인했습니다. 리뷰 포인트: 저장소 밖의 외부 client가 이 경로를 쓰고 있을 가능성. `include_in_schema=False` route는 `openapi.json`에 없어 `check-openapi`가 제거를 감지하지 못하므로, 자동 검사로는 잡히지 않는 breaking change입니다.

### 3. 반환값을 쓰지 않는 가드 호출

```python
_contest_or_404(session, contest_id)          # contests/router.py:334
_editable_revision_or_409(session, ...)       # problems/router.py:441
```

린터가 미사용 변수로 지적해 변수 바인딩만 제거했습니다. 호출 자체는 404/409를 던지는 필수 검사이므로 지우면 안 됩니다. 리뷰 중 "결과를 안 쓰는데 왜 호출하나"로 보일 수 있어 미리 밝힙니다.

### 4. 미사용 import 22개 및 파일 2개 삭제

`backend/main.py`(`uv init` 스텁)와 `backend/api_spec.json`(구식 수기 명세, 9개 endpoint 중 2개는 이미 없는 경로)을 삭제했습니다. 정리 중 `app/main.py`가 테스트 전용으로 재노출하던 `_to_user_read` 별칭이 제거되어 테스트가 깨졌고, 재노출을 복구하는 대신 테스트가 실제 정의 위치(`app/domains/users/serializers`)를 직접 임포트하도록 수정했습니다.

## 판단이 필요한 사항

| 항목                                  | 현황                                                                                                                                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PostgreSQL 호환성 검증 제거           | `testcontainers` 기반 마이그레이션 호환성 테스트를 삭제했습니다. `DATABASE_URL`로 Postgres 연결은 여전히 가능하지만 검증 수단이 없습니다. 운영에서 Postgres를 쓸 계획이 있다면 복구가 필요합니다 |
| LICENSE 파일 부재                     | README는 MIT라고 명시하는데 `LICENSE` 파일이 없습니다                                                                                                                                            |
| `env_example`의 `APP_VERSION`         | 코드가 읽지 않는 변수입니다. 실제 버전은 `config.py`의 `PROJECT_VERSION`(하드코딩)이 담당합니다                                                                                                  |
| `pyproject.toml`의 `name = "backend"` | 일반적인 이름이나, 변경 시 `uv.lock`과 Docker 빌드에 영향이 있어 손대지 않았습니다                                                                                                               |

## 리뷰 중 실행할 검증 명령

```bash
cd backend

# 전체 테스트 (약 90초)
uv run pytest

# 커버리지
uv run pytest --cov=app --cov-report=term-missing

# API 계약이 깨졌는지 (기준선을 덮어쓰지 않음)
uv run python -m app.cli check-openapi --baseline openapi.json

# 문서와 runtime router 일치 검사
uv run pytest -q tests/core/test_openapi_contract.py

# 미사용 코드 재확인
uvx ruff check --select F401,F811,F841 app/ tests/
```

기준 상태: 265 passed, 커버리지 80%, ruff 위 규칙 위반 0건, `check-openapi` compatible.

## 시간 배분 제안

| 범위    | 소요      | 커버되는 위험                         |
| ------- | --------- | ------------------------------------- |
| 0~3단계 | 약 4시간  | 인증·권한·데이터 모델 - 위험의 대부분 |
| 0~5단계 | 약 9시간  | 위 + 코드 실행 샌드박스 + 업로드 처리 |
| 전체    | 약 11시간 | 운영 도구와 테스트 포함               |

시간이 하루뿐이라면 3단계(권한)와 4단계의 `code_runner.py` 에 집중하시기를 권합니다. 학생 코드를 실행하는 시스템에서 가장 큰 위험이 그곳에 있습니다.
