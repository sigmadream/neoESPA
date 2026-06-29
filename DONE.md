# 완료된 항목

이 문서는 현재까지 완료된 테스트 보강 및 TDD 고도화 작업을 정리한 기록입니다.

## 1. 1차 우선순위 이슈 완료

- CodeSnapshot 압축/복원 계약 회귀 테스트 완료
  - 압축/복원 왕복
  - 평문 fallback
  - 손상 입력 fallback
  - 응답 평문, DB 압축 저장 계약 검증
- CodeSnapshot 중복 저장 최적화 회귀 테스트 완료
  - 동일 코드 재저장 시 단일 레코드 유지
  - 기존 snapshot id 유지
  - 최신 조회 응답 평문 유지
- 관리자 권한 역할 행렬 회귀 테스트 완료
  - admin, instructor, ta 허용
  - student, 비활성 사용자 차단
  - 관리자 스냅샷 조회 권한 검증
- 마이그레이션 최신 스키마 회귀 테스트 완료
  - code_snapshots 포함 최신 스키마 생성
  - 재실행 idempotency
  - Docker/Local SQLite 경로 smoke 검증
- 채점 상태 전이 경계 회귀 테스트 완료
  - pending → graded, failed, retryable 전이 검증
  - 재채점 실패 시 수동 점수 보존
  - 대표 실패 요약 메시지 계약 검증
- 제출 라우터 실패 경로 회귀 테스트 완료
  - 존재하지 않는 과제, 허용되지 않은 언어, 빈 코드
  - 공개 전, 마감 후, 재시도 한도 초과 차단
  - 본인/타인/관리자 권한 분기 검증

## 2. 후속 TDD 준비 항목 완료

- 스냅샷 API Rate Limiting 구현 및 회귀 테스트 완료
- 스냅샷 Retention / Archive 정책 구현 및 회귀 테스트 완료
- 압축 레이어 공통화 완료
  - Submission 저장 압축
  - 채점, 표절, 내보내기, 협업 이력 평문 복원
  - 레거시 평문 fallback 유지

## 3. 장기 고도화 과제 완료

- 커버리지 측정 도입
  - pytest-cov 적용
- 테스트 데이터 팩토리 도입
  - create_user
  - create_homework
  - create_submission
  - create_submission_result
- 속성 기반 테스트 확장
  - ZIP pairing 순서 불변식
  - 압축/복원 왕복 불변식
  - 채점 점수 총합 경계 불변식
- 비동기 및 실시간 경로 테스트 보강
  - AsyncClient 기반 협업 세션 검증
  - WebSocket 실시간 이벤트 검증
- Testcontainers 기반 환경 일치성 검증 추가
  - Postgres smoke 테스트 구성
  - Docker 부재 환경 skip 동작 검증

## 4. 추가 보강 완료 항목

### 사용자 및 설정 관리
- 사용자 관리자 API 예외 경로 보강 완료
  - 잘못된 role filter
  - 자기 자신의 role 변경 차단
  - 자기 자신의 비활성화 차단
  - 없는 사용자에 대한 role/status/reset-password 404
  - bulk 생성 중복 id, 중복 sid, 빈 기본 비밀번호, 잘못된 user_group, 기존 사용자 충돌
  - reset password 후 기존 비밀번호 실패, 새 비밀번호 성공
- 설정 API 검증 분기 보강 완료
  - 빈 settings payload 400
  - 지원하지 않는 key 400
  - 잘못된 boolean 및 음수 numeric 값 400
  - updated_at 갱신 검증

### 과제 및 채점 운영 경로
- 과제 import/delete 실패 정리 경로 보강 완료
  - import 중 HTTPException cleanup
  - import 중 일반 예외 cleanup
  - 없는 homework update/delete 404
  - delete 시 artifact metadata rule 삭제
  - delete 시 artifact 디렉터리 제거
- 채점 관리자 운영 분기 보강 완료
  - grade_submission 일반 예외 시 grading_failed 이벤트 기록
  - process-next 성공 시 audit 기록
  - process-next retryable 시 queue_processing_failed 이벤트 기록
  - grading queue singleton 상태 reset 보강
- Lint 파이프라인 순수 분기 보강 완료
  - syntax error issue
  - disallowed name 탐지
  - unknown rule fallback
  - 잘못된 regex fallback
  - setting fallback 검증

### 시스템 설정 및 알림
- system_settings 헬퍼 테스트 보강 완료
  - parse_boolean_setting 허용/거부값
  - normalize_setting_value number, boolean, string 정규화
  - 빈 string, 알 수 없는 key 예외
  - LINT_SETTING_KEYS, DEFAULT_LINT_SETTINGS 기본 계약 검증
- notification 경로 테스트 보강 완료
  - 빈 notification_ids 읽음 처리
  - 현재 사용자 알림만 읽음 반영
  - 비활성 학생 공지 알림 제외
  - manual_total_score 우선 채점 완료 알림 검증

## 5. 현재 기준 검증 결과

- 전체 백엔드 테스트
  - 명령: `cd backend && uv run pytest`
  - 결과: 165 passed, 2 skipped
- 전체 커버리지 재측정
  - 명령: `cd backend && uv run pytest --cov=app --cov-report=term-missing`
  - 결과: 전체 90%
- 대표 커버리지 결과
  - `app/domains/users/router.py` 98%
  - `app/domains/settings/router.py` 100%
  - `app/domains/grading/router.py` 95%
  - `app/domains/homework/router.py` 91%
  - `app/services/notification_service.py` 100%

## 6. 문서 통합 메모

- 기존 `backend/TDD_TODO.md`의 완료 항목은 이 문서와 루트 `TODO.md`로 통합했습니다.
- 백엔드 전용 TDD 문서는 삭제했습니다.
