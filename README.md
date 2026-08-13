# neoESPA

> 프로그래밍 과목의 과제 제출·자동 채점·피드백을 다루는 학습 관리 시스템입니다.

## 구성 요소

| 구성 요소       | 설명                                                 | 문서                                       |
| --------------- | ---------------------------------------------------- | ------------------------------------------ |
| `backend/`      | FastAPI + SQLModel API 서버, 운영 CLI, 채점 워커     | [backend/README.md](./backend/README.md)   |
| `frontend/`     | Next.js 16 웹 클라이언트 (수강생 화면 + 관리자 콘솔) | [frontend/README.md](./frontend/README.md) |
| `database/`     | SQLite 데이터 파일 (개발·E2E용)                      | —                                          |
| `supportFiles/` | 린트 규칙, 과제 산출물 등 런타임 참조 자료           | —                                          |

## 1. 도커(Docker) 기반 실행 방법

Docker 및 Docker Compose가 설치돼 있으면 아래 명령 하나로 백엔드와 프론트엔드가 함께 뜹니다.
호스트에 Python·uv·Node.js가 없어도 됩니다.

```bash
docker compose up --build -d
```

초기 샘플 데이터(관리자·학생 계정, 예시 과제와 공지)를 생성합니다.

```bash
docker compose exec backend uv run python create_sample_data.py
```

서비스 접속 주소:

- 프론트엔드: http://localhost:3000
- 백엔드 API 문서(Swagger): http://localhost:8000/docs

기본 샘플 계정:

| 구분   | 아이디     | 비밀번호   |
| ------ | ---------- | ---------- |
| 관리자 | `admin`    | `admin`    |
| 학생   | `testuser` | `qwer1234` |

로그·중지:

```bash
docker compose logs -f backend    # 로그 확인
docker compose down               # 중지
```

소스는 컨테이너에 마운트되어 즉시 반영됩니다. `--build`는 `Dockerfile`이나 시스템 패키지를
바꿨을 때만 필요합니다.

### 운영 환경 배포

운영 구성은 API 서버와 함께 nsjail 샌드박스가 포함된 **채점 워커**를 별도로 띄웁니다. 워커는
기동 전에 샌드박스 자체 점검(hostile-fixture)을 통과해야 채점을 시작합니다.

`docker-compose.prod.yml`은 아래 환경변수를 **필수**로 요구하며, 하나라도 없으면 기동이 중단됩니다.

| 변수                    | 설명                                                               |
| ----------------------- | ------------------------------------------------------------------ |
| `JWT_SECRET`            | 32바이트 이상의 토큰 서명 비밀키                                   |
| `COURSE_ID`             | 코스 식별자 (예: `CS101`)                                          |
| `COURSE_TERM`           | 학기 (예: `2026-fall`)                                             |
| `JUDGE_RUNTIME_VERSION` | 채점 이미지의 불변 런타임 버전. 샌드박스 attestation과 대조합니다. |

```bash
JWT_SECRET="<32바이트 이상의 비밀키>" \
COURSE_ID="CS101" \
COURSE_TERM="2026-fall" \
JUDGE_RUNTIME_VERSION="judge-2026-fall-1" \
  docker compose -f docker-compose.prod.yml up --build -d
```

전체 항목과 기본값은 [env_example](./env_example)을 참고하시기 바랍니다.

## 2. 소스 코드(Clone) 기반 실행 방법

Python 3.14 이상, [uv](https://github.com/astral-sh/uv), Node.js 22 이상 환경에서 직접 구동하는 방법입니다.

### 저장소 클론 및 환경 변수 설정

```bash
git clone <repository-url>
cd neoespa
cp env_example .env      # JWT_SECRET은 32바이트 이상 값으로 교체
```

### 백엔드 기동

```bash
cd backend
uv sync
DATABASE_URL="sqlite:///$PWD/../database/database.sqlite" \
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

데이터베이스 스키마는 애플리케이션 기동 시 자동으로 적용됩니다. 샘플 데이터가 필요하면
`uv run python create_sample_data.py`를 실행합니다.

### 프론트엔드 기동

별도의 터미널에서 실행합니다.

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

## 3. 테스트 실행

### 백엔드

운영체제와 무관하게 동일한 Linux 컨테이너 안에서 실행합니다. 호스트에 Python·uv·컴파일러가
없어도 됩니다.

```bash
# Linux / macOS / Git Bash
./backend/scripts/test.sh

# Windows PowerShell
.\backend\scripts\test.ps1

# 래퍼 없이 직접 실행 (저장소 루트에서)
docker compose -f docker-compose.test.yml run --rm --build tests

# 샌드박스 격리 실검증 (실제 nsjail 실행, 첫 빌드는 수 분 소요)
docker compose -f docker-compose.test.yml run --rm --build sandbox-tests
```

특정 테스트만 실행, 커버리지, 포맷 검사 등 세부 옵션은
[backend/README.md](./backend/README.md#테스트-수행-docker-기반)에 있습니다.

### 프론트엔드

타입 검사와 린트는 컨테이너에서 실행할 수 있습니다.

```bash
docker compose run --rm --no-deps -e NODE_ENV=development frontend \
  sh -lc "npm ci --include=dev && npm run typecheck && npm run lint"
```

Playwright E2E는 호스트에서 실행하며, 백엔드(포트 8101)와 프론트엔드(포트 3101)를 스스로
띄우고 `database/e2e.sqlite`를 초기화·시딩합니다. 호스트에 Python·uv·Node.js가 필요합니다.

```bash
cd frontend
npm run test:e2e
```

### API 계약

API를 추가·변경한 경우 기준선과 문서를 함께 갱신해야 합니다. 절차는
[backend/API.md](./backend/API.md)의 "스펙 검증" 절을 따르십시오.

## 추가 문서

- [backend/README.md](./backend/README.md) — 백엔드 설치, 운영 CLI, 테스트 카테고리, 샌드박스 검증
- [frontend/README.md](./frontend/README.md) — 화면 구성, 관리자 콘솔 탭, 디자인 규약, API 클라이언트 규칙
- [backend/API.md](./backend/API.md) — 카테고리별 API 명세 및 스펙 검증 절차
- [backend/REVIEW-GUIDE.md](./backend/REVIEW-GUIDE.md) — 코드 리뷰 단계별 안내
