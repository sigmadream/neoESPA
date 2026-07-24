# neoESPA Deployment Guide & Migration Management

## 1. Database Schema & Migration Management

neoESPA는 자체 버전 관리 기반 비동기 마이그레이션 체계를 사용합니다 (`backend/app/migrations/v0001~v0004`).

### 신규 마이그레이션 작성 절차
1. `backend/app/migrations/` 디렉터리에 `v0005_feature_name.py` 모듈을 작성합니다.
2. `apply_migration(engine)` 함수 내 스키마 변경 SQL문과 멱등성(Idempotency) 검사를 구현합니다.
3. `backend/app/migrations/__init__.py` 및 `backend/app/core/migrations.py`의 마이그레이션 목록에 해당 모듈을 등록합니다.

---

## 2. Docker & Production Deployment

### 개발 환경 실행
```bash
docker compose up --build
```

### 프로덕션 환경 실행 (PostgreSQL 또는 SQLite)
```bash
JWT_SECRET="<32자 이상 시크릿>" docker compose -f docker-compose.prod.yml up --build -d
```

프론트엔드의 API 프록시 대상(`BACKEND_URL`)은 Next.js 빌드 시점에 고정되므로,
`docker-compose.prod.yml`의 `build.args`로 전달합니다. compose 네트워크 기본값은
`http://backend:8000`이며, 별도 인프라에 배포할 때는 해당 값을 실제 백엔드 주소로 변경합니다.

백엔드는 단일 uvicorn worker로 실행합니다. 채점 큐(`GradingQueueService`)와 스냅샷
rate limiter가 프로세스 내 메모리 상태를 사용하므로, 다중 worker로 확장하려면 먼저
해당 상태를 외부 저장소(예: Redis)로 이전해야 합니다.

---

## 3. Database Backup and Recovery

### SQLite 백업 및 복구
- **백업**: `cp database/database.sqlite database/database_backup_$(date +%Y%m%d).sqlite`
- **복구**: `cp database/database_backup_20260724.sqlite database/database.sqlite`

---

## 4. Environment Variables Reference

| Variable | Default | Description |
| --- | --- | --- |
| `APP_ENV` | `development` | 애플리케이션 환경 (`development`, `test`, `production`) |
| `JWT_SECRET` | Required in prod | JWT 암호화 비밀키 (최소 32자 이상) |
| `CORS_ORIGINS` | `http://localhost:3000` | 허용할 프론트엔드 출처 쉼표 구분 목록 |
| `DATABASE_URL` | `sqlite:////database/database.sqlite` | 데이터베이스 연결 문자열 |
| `BACKEND_URL` | `http://backend:8000` | 프론트엔드 빌드 인자. Next.js rewrite가 프록시할 백엔드 주소 |
