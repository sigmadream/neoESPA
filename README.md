## neoESPA 프로젝트 실행 가이드

> neoESPA 프로젝트를 빠르게 실행하는 방법입니다.

## 1. 도커(Docker) 기반 실행 방법

Docker 및 Docker Compose가 설치된 환경에서 아래 명령어로 백엔드와 프론트엔드를 함께 기동합니다.

```bash
docker compose up --build -d
```

운영 환경 구성은 `docker-compose.prod.yml`을 사용하며, `JWT_SECRET` 등의 값을 환경변수로 주입해야 합니다.

```bash
JWT_SECRET="<32바이트 이상의 비밀키>" docker compose -f docker-compose.prod.yml up --build -d
```

초기 샘플 데이터(관리자, 학생 계정 및 과제 데이터)를 생성하려면 아래 명령어를 실행합니다.

```bash
docker compose exec backend uv run python create_sample_data.py
```

서비스 접속 주소:
- 프론트엔드: http://localhost:3000
- 백엔드 API 문서(Swagger): http://localhost:8000/docs

기본 샘플 계정:
- 관리자 계정: admin / pllab2026
- 학생 계정: testuser / qwer1234

도커 컨테이너 중지:

```bash
docker compose down
```

## 2. 소스 코드(Clone) 기반 실행 방법

Python 3.14 이상, uv, Node.js 22 이상 환경에서 직접 구동하는 방법입니다.

### 저장소 클론 및 이동

```bash
git clone <repository-url>
cd neoespa
```

### 환경 변수 설정

`env_example`을 복사해 `.env`를 만들고 값을 채웁니다. 최소한 `JWT_SECRET`은 32바이트 이상의 값으로 교체해야 합니다.

```bash
cp env_example .env
```

### 백엔드 기동

```bash
cd backend
uv sync
DATABASE_URL="sqlite:///$PWD/../database/database.sqlite" uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

데이터베이스 스키마는 애플리케이션 기동 시 자동으로 적용됩니다. 수동으로 적용하려면 아래 명령을 사용합니다.

```bash
uv run -m app.core.migrations
```

샘플 데이터 생성(선택 사항):

```bash
cd backend
uv run python create_sample_data.py
```

### 프론트엔드 기동

별도의 터미널에서 프론트엔드 의존성을 설치하고 개발 서버를 실행합니다.

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

서비스 접속 주소:
- 프론트엔드: http://localhost:3000
- 백엔드 API 문서: http://localhost:8000/docs

## 3. 테스트 실행

백엔드 테스트는 운영체제와 무관하게 동일한 Linux 컨테이너 안에서 실행합니다. 호스트에 Python·uv·컴파일러가 없어도 됩니다.

```bash
# Linux / macOS / Git Bash
./backend/scripts/test.sh

# Windows PowerShell
.\backend\scripts\test.ps1

# 래퍼 없이 직접 실행
docker compose -f docker-compose.test.yml run --rm --build tests

# 샌드박스 격리 실검증 (실제 nsjail 실행, 첫 빌드는 수 분 소요)
docker compose -f docker-compose.test.yml run --rm --build sandbox-tests
```

세부 옵션(특정 테스트만 실행, 커버리지, 포맷 검사)은 [backend/README.md](./backend/README.md#테스트-수행-docker-기반)를 참고하시기 바랍니다.

## 추가 문서

- [backend/README.md](./backend/README.md) — 백엔드 설치, CLI 도구, 테스트 카테고리
- [backend/API.md](./backend/API.md) — 카테고리별 API 명세 및 계약 검증 절차
