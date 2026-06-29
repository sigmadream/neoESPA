# 남은 과제

이 문서는 현재 시점의 남은 작업만 정리한 통합 TODO입니다.
기존 `backend/TDD_TODO.md`의 미해결 후속 작업과 최근 테스트 보강 이후 남은 과제를 이 문서로 통합합니다.

## 1. 우선 처리 권장 항목

### 1.1 테스트 자원 정리 품질 개선
- Hypothesis 기반 테스트와 일부 SQLite 경로에서 발생하는 `ResourceWarning: unclosed database` 원인 추적
- 세션, 엔진, 연결 해제 시점 정리
- 경고 없는 전체 테스트 실행을 목표로 fixture 구조 점검

완료 기준
- `cd backend && uv run pytest` 실행 시 `ResourceWarning: unclosed database`가 발생하지 않습니다.

### 1.2 저보호 핵심 서비스 추가 보강
- `backend/app/services/grading_service.py`
  - 현재 전체 커버리지 기준 79%
  - 남은 분기 중심 보강 필요
  - 컴파일/런타임 실패 상세 분기
  - 요약 메시지 조합 분기
  - lint 반영 경계 분기
- `backend/app/core/system_settings.py`
  - 전체 스위트 기준 남은 branch 보강 필요
  - 음수, 빈 string, key error 경계 세분화 가능
- `backend/app/core/config.py`
  - 환경 변수 파싱 및 기본값 경계 보강 필요

완료 기준
- 대상 모듈에 대해 현재 미커버 branch가 줄고, 회귀 위험 분기가 테스트로 고정됩니다.

## 2. 중간 우선순위 항목

### 2.1 Homework 헬퍼 계층 보강
대상 파일
- `backend/app/domains/homework/helpers.py`

남은 과제
- artifact metadata 정규화 실패 분기
- 잘못된 testcase payload fallback
- rule 활성/비활성 분기
- 언어 정책 JSON 손상 및 비정상 타입 경계

### 2.2 API dependency 및 공통 인증 경계 보강
대상 파일
- `backend/app/api/dependencies.py`

남은 과제
- 토큰 누락/손상/만료 경계
- 비활성 사용자 처리 분기
- 권한 부족 분기 세분화

### 2.3 notification/observability 보조 경로 보강
대상 파일
- `backend/app/services/observability_service.py`
- `backend/app/services/notification_service.py`

남은 과제
- observability payload/context 조합 분기
- 읽음 처리 외 알림 누적/정렬/limit 경계
- 공지/채점 외 추가 알림 유형이 생길 때의 계약 테스트 준비

## 3. 낮은 우선순위 항목

### 3.1 문서화된 커버리지 기준선 갱신
- `DONE.md`에는 현재 90% 재측정 결과가 기록되어 있습니다.
- 필요 시 `TODO.md` 유지 대신 별도 커버리지 기준 문서로 분리할 수 있습니다.
- 모듈별 최소 기준선을 실제 CI 규칙으로 올릴지 결정이 필요합니다.

### 3.2 CI 품질 게이트 연동
- 전체 테스트 통과 외에
  - 커버리지 하한
  - 경고 0건
  - Docker 가능 환경의 Testcontainers 스위트 별도 lane
  를 CI에 연결할지 검토가 필요합니다.

## 4. 현재 참고 지표

- 전체 백엔드 테스트 결과
  - `cd backend && uv run pytest`
  - 165 passed, 2 skipped
- 전체 커버리지 결과
  - `cd backend && uv run pytest --cov=app --cov-report=term-missing`
  - 전체 90%

현재 기준 주의사항
- 기능 실패는 없으나 `ResourceWarning: unclosed database`가 남아 있습니다.
- Docker daemon 부재 환경에서는 `tests/core/test_testcontainers_postgres.py`가 skip 됩니다.

## 5. 정리

완료된 항목은 `DONE.md`에 정리했습니다.
이 문서는 앞으로 실제로 남아 있는 작업만 유지합니다.
