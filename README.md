# neoESPA ReNew

> 현재는 "로컬에서 바로 띄워 보고, 과제 제출 흐름까지 확인할 수 있는 상태"이다. 남은 몇가지 기능은 아래와 같고, 2026년 6월까지 계속해서 진행할 예정입니다.

- [ ] 시험 전용 UI
- [ ] 게시판형 자료실
- [ ] 게시판형 Q&A 
- [ ] 멀티 코스 구조

## 빠르게 시작하기

- 프론트엔드: `http://localhost:3000`
- 백엔드 API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

```bash
docker compose up --build
# docker compose up --build -d
docker compose exec backend uv run python create_sample_data.py
```

### 샘플 계정

- 관리자: `admin / pllab818`
- 학생: `testuser / qwer1234`

### 로그 확인

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### 시스템 중지

```bash
docker compose down
```

## 테스트

### 백엔드

```bash
cd backend
uv run pytest
```

### 프론트엔드

```bash
cd frontend
npm run lint
npm run build
```

### E2E

```bash
cd frontend
npm run test:e2e
```

## 수동 실행

Docker 없이도 실행할 수 있다. 다만 루트 `.env`의 `DATABASE_URL`은 Docker 컨테이너 기준 경로라서, 로컬에서 직접 실행할 때는 덮어쓰는 편이 안전하다.

### 백엔드

```bash
cd backend
uv sync
DATABASE_URL="sqlite:///$PWD/../database/database.sqlite" \
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 샘플 데이터

```bash
cd backend
uv run python create_sample_data.py
```

### 프론트엔드

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```
