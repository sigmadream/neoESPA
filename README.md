## neoESPA 프로젝트 실행 가이드

neoESPA 프로젝트를 빠르게 실행하는 방법입니다.

## 1. 도커(Docker) 기반 실행 방법

Docker 및 Docker Compose가 설치된 환경에서 아래 명령어로 백엔드와 프론트엔드를 함께 기동합니다.

```bash
docker compose up --build -d
```

초기 샘플 데이터(관리자, 학생 계정 및 과제 데이터)를 생성하려면 아래 명령어를 실행합니다.

```bash
docker compose exec backend uv run python create_sample_data.py
```

서비스 접속 주소:
- 프론트엔드: http://localhost:3000
- 백엔드 API 문서(Swagger): http://localhost:8000/docs

기본 샘플 계정:
- 관리자 계정: admin / pllab818
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
cd neoespa_v2
```

### 백엔드 기동

```bash
cd backend
uv sync
DATABASE_URL="sqlite:///$PWD/../database/database.sqlite" uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

