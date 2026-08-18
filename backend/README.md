# neoESPA 백엔드 서비스 (FastAPI)

> 본 프로젝트는 neoESPA 학습 관리 시스템의 백엔드 관련 기능을 제공하는 코드입니다. 현재는 FastAPI와 SQLModel(SQLAlchemy + Pydantic)을 기반으로 작성되었습니다. 코드 관련 세부사항은 [REVIEW-GUIDE.md](./REVIEW-GUIDE.md)를 참고하시기 바랍니다.

## 개선 목표

- 테스트를 기반으로 언제든 다른 플랫폼/프레임워크로 변경 가능하도록 관리
- 수강생의 소중한 데이터가 외부에 노출되지 않도록 보안 및 안정성 강화
- 유지보수 및 확장 용이성 확보

## 주요 기술 스택

- [FastAPI](https://fastapi.tiangolo.com/) (>= Python 3.14)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [uv](https://github.com/astral-sh/uv)
- 데이터베이스: SQLite.
  - `DATABASE_URL` 환경변수로 SQLAlchemy가 지원하는 다른 엔진을 지정할 수 있으나, 현재 마이그레이션은 SQLite에서만 검증함
- 보안: OAuth2 (JWT), bcrypt 비밀번호 해싱
- 테스트: pytest

## 설치 및 실행

실행 경로는 두 가지입니다. **Docker 경로는 호스트에 Python·uv·컴파일러가 없어도 되고 운영체제 차이를 타지 않으므로 이쪽을 권장합니다.** 아래 "테스트 수행"도 Docker 기준입니다.

### Docker로 실행 (권장)

`docker compose` 명령은 **저장소 루트**(`backend/`의 상위)에서 실행합니다.

```bash
cd ..                              # backend/ 에 있다면 저장소 루트로 이동

docker compose up --build -d backend   # 백엔드만 (프론트까지 띄우려면 서비스명 생략)
docker compose logs -f backend         # 로그 확인
docker compose down                    # 종료
```

- API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)
- 소스는 컨테이너에 바인드 마운트되어 `--reload`로 즉시 반영됩니다. 파이썬 의존성은 컨테이너가 기동할 때마다 `uv sync --frozen`으로 맞춰지므로, `--build`는 `Dockerfile`이나 시스템 패키지를 바꿨을 때만 필요합니다.
- DB는 저장소 루트의 `database/database.sqlite`를 공유하며, 스키마 마이그레이션은 앱 기동 시 자동 적용됩니다.

컨테이너 안에서 스크립트나 CLI를 실행할 때는 `docker compose exec`를 사용합니다.

```bash
# 샘플 데이터 생성 (관리자·학생 계정, 예시 과제/공지)
docker compose exec backend uv run python create_sample_data.py

# 관리 CLI
docker compose exec backend uv run python -m app.cli --help
```

- 관리자 계정: ID: `admin` / PW: `admin`
- 테스트 학생: ID: `testuser` / PW: `qwer1234`

프로덕션 구성은 저장소 루트의 `docker-compose.prod.yml`을 사용합니다. 이 구성은 API 이미지와 함께 nsjail 샌드박스가 포함된 채점 워커(`deploy/Dockerfile.judge`)를 별도로 띄우며, 워커는 기동 전에 샌드박스 자체 점검을 통과해야 채점을 시작합니다.

협업 WebSocket 브로드캐스트는 현재 API 프로세스 메모리 안에서 관리되므로 API는 `--workers 1`로 실행해야 합니다. 다중 워커나 여러 API 레플리카로 확장하기 전에는 Redis pub/sub 같은 외부 브로커로 연결 관리 계층을 교체해야 합니다.

### 호스트에서 직접 실행 (uv)

```bash
# 가상 환경 생성 및 의존성 설치
uv sync
```

#### 데이터베이스 스키마 초기화

데이터베이스 테이블을 생성하고 초기 마이그레이션을 수행합니다.

```bash
uv run -m app.core.migrations
```

#### 샘플 데이터 설정

개발 및 테스트를 위한 관리자 계정, 샘플 과제, 공지사항 등을 생성합니다. (계정 정보는 위 Docker 절과 동일합니다.)

```bash
uv run python create_sample_data.py
```

#### 서버 실행

로컬 개발 서버를 실행합니다. ASGI 애플리케이션은 `app/main.py`의 `app` 객체입니다.

```bash
uv run uvicorn app.main:app --reload
```

저장소 최상위의 공용 SQLite 파일을 사용하려면 `DATABASE_URL`을 지정합니다.

```bash
DATABASE_URL="sqlite:///$PWD/../database/database.sqlite" \
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 [http://localhost:8000/docs](http://localhost:8000/docs)에서 인터랙티브 API 문서를 확인할 수 있습니다.

## 주요 관리 도구 (CLI)

관리자 계정 생성 등 주요 운영 작업을 위한 전용 CLI 도구를 제공합니다. 전체 명령 목록은 `uv run python -m app.cli --help`로 확인할 수 있습니다. Docker로 실행 중이라면 모든 예시 앞에 `docker compose exec backend`를 붙이면 됩니다.

```bash
# 관리자 계정 생성
uv run python -m app.cli create-admin \
  --id ops-admin \
  --sid 10050001 \
  --name "Operations Admin" \
  --phone "010-5555-0001" \
  --email "ops-admin@example.com" \
  --password "secure-password"
```

주요 명령:

| 명령                                                | 용도                                                                                                              |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `create-admin`                                      | 로컬 관리자 계정 생성                                                                                             |
| `issue-bootstrap-token`                             | 최초 슈퍼 관리자용 일회성 토큰 발급                                                                               |
| `run-judge-worker`                                  | 채점·검증 작업 큐 처리 워커 실행                                                                                  |
| `check-openapi`                                     | 현재 API가 저장된 스펙을 깨는지 검사                                                                              |
| `export-openapi`                                    | 정규화된 OpenAPI 스펙 파일 갱신                                                                                   |
| `verify-course-bundle` / `restore-course-bundle`    | 코스 번들 무결성 검증 및 복원                                                                                     |
| `create-course-snapshot`                            | 코스 스냅샷 생성                                                                                                  |
| `export-analytics-jsonl`                            | 분석용 JSONL 내보내기                                                                                             |
| `reconcile-artifacts` / `backfill-legacy-artifacts` | 아티팩트 정합성 조정 및 백필                                                                                      |
| `record-capacity-baseline`                          | 용량 기준선 기록                                                                                                  |
| `run-sandbox-self-test`                             | 샌드박스 자체 점검 (nsjail이 설치된 Linux에서만 동작. 판정 근거는 [샌드박스 실검증](#샌드박스nsjail-실검증) 참고) |

`check-openapi`와 `export-openapi`의 실행 순서에는 주의가 필요합니다. 자세한 내용은 [API.md](./API.md)의 "스펙 검증"을 참조하시기 바랍니다.

## 개발 및 테스트 가이드

### 테스트 수행 (Docker 기반)

테스트는 **운영체제와 무관하게 동일한 결과**가 나오도록 Linux 컨테이너 안에서 실행하는 것을 기준으로 합니다. 호스트에 Python·uv·C/C++ 컴파일러가 없어도 되며, 채점기(`CodeRunnerService`)가 실제로 코드를 컴파일·실행하는 테스트 케이스까지 그대로 검증됩니다.

래퍼 스크립트는 **어느 디렉터리에서 실행해도** 됩니다. (스크립트가 저장소 루트를 스스로 찾습니다.)

```bash
# Linux / macOS / Git Bash
./backend/scripts/test.sh

# Windows PowerShell
.\backend\scripts\test.ps1
```

`docker compose` 명령을 직접 쓸 때는 **저장소 루트**에서 실행합니다.

```bash
docker compose -f docker-compose.test.yml run --rm --build tests
```

`--build`는 현재 작업 트리를 이미지에 다시 굽기 위한 것으로, 래퍼 스크립트에는 이미 포함되어 있습니다. 붙이지 않으면 마지막으로 빌드된 소스가 검증됩니다.

pytest 인자는 그대로 전달됩니다.

```bash
# 특정 카테고리 테스트 실행 (예: 과제 도메인)
./backend/scripts/test.sh tests/homework

# 이름으로 필터링 + 실패 지점에서 중단
./backend/scripts/test.sh -k lint -x
```

제공되는 compose 서비스는 다음과 같습니다.

| 서비스          | 용도                                                                  | 실행                                                                       |
| --------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `tests`         | 이미지에 구워진 소스로 전체 테스트 실행 (기본 검증 대상)              | `./backend/scripts/test.sh`                                                |
| `tests-live`    | 재빌드 없이 호스트의 `app/`·`tests/`를 읽기 전용 마운트하여 반복 실행 | `SERVICE=tests-live ./backend/scripts/test.sh`                             |
| `coverage`      | 커버리지 측정 후 `backend/.reports/`에 HTML·XML 리포트 생성           | `SERVICE=coverage ./backend/scripts/test.sh`                               |
| `format`        | `black --check --diff`로 포매팅 위반 검사                             | `SERVICE=format ./backend/scripts/test.sh`                                 |
| `sandbox-tests` | 실제 nsjail로 샌드박스 격리 검증 ([아래 절](#샌드박스nsjail-실검증))  | `docker compose -f docker-compose.test.yml run --rm --build sandbox-tests` |

PowerShell에는 `SERVICE=...` 접두사 문법이 없으므로 `-Service` 파라미터를 씁니다.

```powershell
.\backend\scripts\test.ps1 -Service coverage
.\backend\scripts\test.ps1 -Service format
```

컨테이너는 저장소 레이아웃을 그대로 재현하므로(`/` = 저장소 루트, `/app` = `backend/`, `/supportFiles`, `/database`) `settings.BASE_DIR` 및 supportFiles 탐색 경로가 개발 머신과 동일하게 동작합니다. `supportFiles`는 named build context로 이미지에 포함되므로 실행 시 호스트 경로 마운트가 필요 없고, `.env`도 읽지 않으며 네트워크도 차단(`network_mode: none`)됩니다. 로케일·타임존은 `C.UTF-8`/`UTC`로 고정됩니다.

compose 없이 이미지만 직접 빌드·실행할 수도 있습니다. (CI에서 유용)

```bash
docker build --target test \
  --build-context supportfiles=./supportFiles \
  -t neoespa-backend-test ./backend
docker run --rm --network none neoespa-backend-test
```

### 샌드박스(nsjail) 실검증

샌드박스 테스트는 두 층으로 나뉩니다.

| 파일                                    | 방식                             | 실행 환경                                               |
| --------------------------------------- | -------------------------------- | ------------------------------------------------------- |
| `tests/sandbox/test_nsjail_contract.py` | mock (`subprocess.run` 패치)     | 모든 OS — 명령 구성·fail-closed 스펙만 검증             |
| `tests/sandbox/test_nsjail_real.py`     | **mock 없음** — 실제 nsjail 실행 | `sandbox-tests` 서비스 전용, 그 외 환경에서는 자동 skip |

mock 테스트는 "정책 파일에 어떤 문자열이 있는가"까지만 보증하고, 그 정책이 실제로 격리를 강제하는지는 증명하지 못합니다. `sandbox-tests`는 운영 judge 이미지(`deploy/Dockerfile.judge`)와 **동일한 nsjail 바이너리**로 감옥을 띄워 다음을 실제로 확인합니다.

- 파이썬·C 제출의 컴파일·실행·stdin 전달이 감옥 안에서 정상 동작
- 네트워크 차단: 테스트 프로세스가 직접 연 리스너에조차 접속 불가
- 루트 파일시스템 읽기 전용, 작업 디렉터리만 쓰기 가능
- fork bomb 억제, CPU 타임아웃, 출력량 제한, 메모리 제한
- hostile self-test 6종을 실행해 기록한 attestation이 `settings.SANDBOX_READY`(fail-closed 스위치)를 실제로 열고, 정책이 1바이트라도 바뀌면 즉시 닫히는지

```bash
docker compose -f docker-compose.test.yml run --rm --build sandbox-tests
```

nsjail을 소스에서 빌드하므로 첫 실행은 수 분이 걸립니다. 커널 네임스페이스·cgroup 제어가 필요해 운영(`docker-compose.prod.yml`)과 동일하게 `privileged` + `cgroup: host`로 실행되며, 다른 서비스와 달리 컨테이너 네트워크를 차단하지 않습니다(네트워크가 있어야 "감옥 안에서만 끊긴다"는 사실이 증명됩니다).

> 이 실검증을 도입하면서 `deploy/nsjail.cfg`의 결함 세 가지가 드러나 수정했습니다. 자세한 내용은 커밋 이력을 참고하시고, 정책 변경분은 보안 검토가 필요합니다.

### 호스트에서 pytest 직접 실행 (참고용)

`uv run pytest`로도 실행할 수 있으나, 결과는 호스트 OS에 따라 달라질 수 있습니다. 예를 들어 Windows에서는 `tests/core/test_runner.py::test_runner_enforces_timeout`처럼 POSIX 프로세스 동작에 의존하는 테스트가 실패합니다. 최종 판정 기준은 항상 위의 컨테이너 실행 결과입니다.

```bash
uv run pytest
```

### 테스트 카테고리 및 항목

테스트 코드는 API 및 비즈니스 로직의 카테고리에 따라 다음과 같이 분류되어 있습니다. QA 및 코드 리뷰 시 해당 경로의 테스트를 참조하시기 바랍니다.

- `tests/auth/` (인증/권한): 사용자 로그인, 회원가입, JWT 토큰 발급 및 권한 제어 검증
- `tests/collab/` (협업): 실시간 협업 세션 및 WebSocket 연결 상태 검증
- `tests/contests/` (대회): 대회 생성·게시, 참가, 클래리피케이션 및 스코어보드 검증
- `tests/dashboard/` (대시보드): 통계 데이터 및 현황 요약 API 검증
- `tests/exams/` (시험): 시험 생성, 응시 및 성적 처리 로직 검증
- `tests/grading/` (채점): 자동 채점 엔진, 피드백 생성, 린트 파이프라인 및 채점 큐 동작 검증
- `tests/homework/` (과제): 과제 생성, 데이터 임포트/엑스포트, ZIP 파일 파싱 검증
- `tests/jobs/` (작업 큐): 비동기 작업 상태 전이, 재시도 및 취소 동작 검증
- `tests/materials/` (자료): 학습 자료 업로드 및 조회 API 검증
- `tests/notices/` (공지): 시스템 공지사항 관리 기능 검증
- `tests/notifications/` (알림): 사용자 알림 발송 및 수신 상태 검증
- `tests/observability/` (관측성): 시스템 상태 모니터링 및 로깅 기능 검증
- `tests/plagiarism/` (표절): 제출 코드 간 유사도 검사 및 표절 탐지 서비스 검증
- `tests/problems/` (문제): 문제·revision 수명주기, 테스트케이스 관리 및 게시 검증
- `tests/qa/` (Q&A): 질문 등록 및 답변 기능 검증
- `tests/sandbox/` (샌드박스): 코드 실행 격리 환경 및 자원 제한 검증
- `tests/settings/` (설정): 시스템 전역 설정 및 환경 구성 API 검증
- `tests/submissions/` (제출): 수강생 코드 제출 및 결과 조회 기능 검증
- `tests/users/` (사용자): 사용자 프로필 관리 및 관리자 전용 사용자 제어 검증
- `tests/e2e/` (종합 테스트): 주요 사용자 시나리오 기반의 End-to-End 통합 테스트
- `tests/core/` (인프라): 데이터베이스 설정, 마이그레이션, CLI 도구, OpenAPI 스펙 및 스키마 유효성 검증

### 코드 품질 관리

커버리지 측정은 `pytest-cov`로 수행합니다.

```bash
# 컨테이너 (권장) — backend/.reports/htmlcov, coverage.xml 생성
SERVICE=coverage ./backend/scripts/test.sh

# 호스트
uv run pytest --cov=app --cov-report=term-missing
```

API를 추가·삭제·변경한 경우 [API.md](./API.md)의 "스펙 검증" 절차를 따라 문서와 `openapi.json`을 함께 갱신해야 합니다. `tests/core/test_openapi_contract.py`가 문서와 runtime router의 일치 여부를 검사합니다.

### 구현 주의 사항 (FK 제약 조건)

SQLAlchemy 세션 내에서 외래 키(Foreign Key) 참조가 포함된 데이터를 저장할 때는 반드시 부모 데이터를 먼저 `flush()` 처리해야 합니다.

```python
# 안전한 패턴 예시
session.add(parent_instance)
session.flush() # DB에 ID를 확정하여 자식 노드에서 참조 가능하게 함
session.add(child_instance_with_fk)
session.commit()
```

## 프로젝트 구조

```text
backend/
├── app/
│   ├── api/          # 글로벌 API 설정 및 의존성
│   ├── core/         # DB 설정, 보안, 구성 정보, 마이그레이션 실행기
│   ├── domains/      # 도메인별 비즈니스 로직 및 라우터 (Auth, Homework, etc.)
│   ├── migrations/   # 순차 적용되는 스키마 마이그레이션 정의
│   ├── models/       # SQLModel 데이터 스키마
│   ├── services/     # 재사용 가능한 서비스 레이어 (Grading, Lint, etc.)
│   ├── cli.py        # 운영용 CLI 진입점 (python -m app.cli)
│   └── main.py       # FastAPI 애플리케이션 (app 객체)
├── deploy/           # 배포 관련 설정 (Dockerfile.judge, nsjail.cfg)
├── scripts/          # test.sh / test.ps1 (Docker 기반 테스트 실행 래퍼)
├── tests/            # pytest 기반 테스트 코드
├── API.md            # 카테고리별 API 명세서
├── openapi.json      # 정규화된 OpenAPI 스펙 기준선
├── create_sample_data.py  # 개발용 샘플 데이터 생성 스크립트
└── Dockerfile        # 백엔드 컨테이너 이미지 정의 (runtime / test 타깃)
```

컨테이너 구성 파일은 저장소 루트에 있습니다.

| 파일                      | 용도                                                       |
| ------------------------- | ---------------------------------------------------------- |
| `docker-compose.yml`      | 개발용 백엔드·프론트엔드 (소스 바인드 마운트 + `--reload`) |
| `docker-compose.test.yml` | 테스트·커버리지·포맷 검사·샌드박스 실검증                  |
| `docker-compose.prod.yml` | 운영 배포 (API + nsjail 채점 워커)                         |
