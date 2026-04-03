# neoESPA 백엔드 서비스 (FastAPI)

> 본 프로젝트는 neoESPA 학습 관리 시스템의 백엔드 관련 기능을 제공하는 코드입니다. 많은 유틸리티가 Python으로 작성되어 있어서 현재는 FastAPI와 SQLModel(SQLAlchemy + Pydantic)을 기반으로 빠르게 작성되었습니다.

## 개선 목표

1. 테스트를 기반으로 언제든 다른 플랫폼/프레임워크로 변경 가능하도록 관리.
2. 수강생의 소중한 데이터가 외부에 노출되지 않도록 보안 및 안정성 강화.
3. 유지보수 및 확장 용이성 확보.

## 주요 기술 스택

- [FastAPI](https://fastapi.tiangolo.com/) (>= Python 3.14)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [uv](https://github.com/astral-sh/uv)
- Database: SQLite (개발용) / 확장 가능 (PostgreSQL 등)
- Security: OAuth2 (JWT), bcrypt 비밀번호 해싱
- Testing: pytest

## 설치

본 프로젝트는 패키지 관리 및 가상 환경 제어를 위해 `uv`를 사용합니다.

### 가상 환경 설정 및 패키지 설치

```bash
# 가상 환경 생성 및 의존성 설치
uv sync
```

### 데이터베이스 스키마 초기화

데이터베이스 테이블을 생성하고 초기 마이그레이션을 수행합니다.

```bash
uv run -m app.core.migrations
```

### 샘플 데이터 설정 (Optional)

개발 및 테스트를 위한 관리자 계정, 샘플 과제, 공지사항 등을 생성합니다.

```bash
uv run create_sample_data.py
```

- 관리자 계정: ID: `admin` / PW: `pllab818`
- 테스트 학생: ID: `testuser` / PW: `qwer1234`

### 서버 실행

로컬 개발 서버를 실행합니다.

```bash
uv run fastapi dev main.py
```

서버가 실행되면 [http://localhost:8000/docs](http://localhost:8000/docs)에서 인터랙티브 API 문서를 확인할 수 있습니다.

## 주요 관리 도구 (CLI)

관리자 계정 생성 등 주요 운영 작업을 위한 전용 CLI 도구를 제공합니다.

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

## 개발 및 테스트 가이드

### 테스트 수행

모든 단위 테스트 및 통합 테스트를 실행합니다.

```bash
# 전체 테스트 실행
uv run pytest

# 특정 카테고리 테스트 실행 (예: 과제 도메인)
uv run pytest tests/homework
```

### 테스트 카테고리 및 항목

테스트 코드는 API 및 비즈니스 로직의 카테고리에 따라 다음과 같이 분류되어 있습니다. QA 및 코드 리뷰 시 해당 경로의 테스트를 참조하시기 바랍니다.

- **`tests/auth/` (인증/권한)**: 사용자 로그인, 회원가입, JWT 토큰 발급 및 권한 제어 검증
- **`tests/collab/` (협업)**: 실시간 협업 세션 및 WebSocket 연결 상태 검증
- **`tests/dashboard/` (대시보드)**: 통계 데이터 및 현황 요약 API 검증
- **`tests/exams/` (시험)**: 시험 생성, 응시 및 성적 처리 로직 검증
- **`tests/grading/` (채점)**: 자동 채점 엔진, 피드백 생성, 린트 파이프라인 및 채점 큐 동작 검증
- **`tests/homework/` (과제)**: 과제 생성, 데이터 임포트/엑스포트, ZIP 파일 파싱 검증
- **`tests/materials/` (자료)**: 학습 자료 업로드 및 조회 API 검증
- **`tests/notices/` (공지)**: 시스템 공지사항 관리 기능 검증
- **`tests/notifications/` (알림)**: 사용자 알림 발송 및 수신 상태 검증
- **`tests/observability/` (관측성)**: 시스템 상태 모니터링 및 로깅 기능 검증
- **`tests/plagiarism/` (표절)**: 제출 코드 간 유사도 검사 및 표절 탐지 서비스 검증
- **`tests/settings/` (설정)**: 시스템 전역 설정 및 환경 구성 API 검증
- **`tests/submissions/` (제출)**: 수강생 코드 제출 및 결과 조회 기능 검증
- **`tests/users/` (사용자)**: 사용자 프로필 관리 및 관리자 전용 사용자 제어 검증
- **`tests/e2e/` (종합 테스트)**: 주요 사용자 시나리오 기반의 End-to-End 통합 테스트
- **`tests/core/` (인프라)**: 데이터베이스 설정, 마이그레이션, CLI 도구 및 스키마 유효성 검증

### 코드 품질 관리

테스트 커버리지 측정 및 TDD 관련 향후 계획은 `TDD_TODO.md` 파일을 참조하시기 바랍니다.

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
│   ├── core/         # DB 설정, 보안, 구성 정보
│   ├── domains/      # 도메인별 비즈니스 로직 및 라우터 (Auth, Homework, etc.)
│   ├── models/       # SQLModel 데이터 스키마
│   └── services/     # 재사용 가능한 서비스 레이어 (Grading, Lint, etc.)
├── tests/            # pytest 기반 테스트 코드
├── API.md            # 카테고리별 API 명세서
└── TDD_TODO.md       # 테스트 고도화 로드맵
```

## 라이센스

MIT
