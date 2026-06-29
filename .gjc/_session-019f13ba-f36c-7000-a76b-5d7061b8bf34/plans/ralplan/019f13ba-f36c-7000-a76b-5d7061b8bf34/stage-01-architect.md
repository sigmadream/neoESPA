## Summary
현재 backend/TDD_TODO.md는 2026-04-03 회고 이후 생긴 실제 회귀 위험보다 범용 테스트 기법 도입을 더 앞세우고 있어 우선순위가 어긋나 있습니다. 특히 스냅샷 압축 계약, require_staff 중심 권한 경계, 제출 라우터의 실패 경로, 그리고 스냅샷 기능을 반영하지 못한 마이그레이션 검증이 빠져 있어 로드맵 수정이 필요합니다.

## Analysis
- 회고 20260403.md는 AssignmentBase 도입, require_staff 권한 단일화, 스냅샷 압축 및 중복 방지, Alembic 기반 마이그레이션을 핵심 변화로 적고 있습니다.
- 현재 보호되고 있는 테스트는 스냅샷 기본 플로우 backend/tests/submissions/test_code_snapshots.py, ZIP 파서 기본과 일부 에러 backend/tests/homework/test_homework_zip_parser.py, 성적 CSV 및 최신 제출 ZIP 내보내기 backend/tests/homework/test_export_api.py, 마이그레이션 최소 경로 backend/tests/core/test_migrations.py 입니다.
- 반면 실제 구현 backend/app/domains/submissions/router.py 에는 제출 생성, 제출 조회, 피드백, 스냅샷 저장 조회 관리자 조회까지 넓은 분기와 예외 처리가 있지만 현재 대상 테스트들 중 상당수는 이 경로를 직접 보호하지 않습니다.
- backend/app/core/compression.py 는 legacy plain text fallback까지 포함한 압축 계층을 구현하지만 직접 테스트가 없습니다.
- backend/app/api/dependencies.py 는 require_staff, require_roles, get_optional_current_user 의 보안 경계를 정의하지만 현재 대상 테스트는 관리자 1종 positive와 비관리자 1종 negative만 간접 확인합니다.
- backend/app/models/schemas.py 에는 AssignmentBase 기반 Homework와 Exam, CodeSnapshot, Submission, SubmissionResult 등 회고 대상 모델이 있으나 이 구조적 계약을 검증하는 테스트는 보이지 않습니다.
- backend/tests/core/test_migrations.py 는 핵심 테이블과 user timestamp backfill만 검증하며 회고의 스냅샷 기능에 대응하는 code_snapshots 테이블 보호가 빠져 있습니다.

## Root Cause
로드맵이 현재 코드의 실제 고장 면을 기준으로 정렬되지 않고 범용 테스트 인프라 도입 항목을 상위에 둔 것이 근본 원인입니다. 그 결과 회고에서 중요하다고 밝힌 변경점과 현재 구현의 실패 경로가 명시적 테스트 백로그로 번역되지 않았습니다.

## Findings
- HIGH — backend/TDD_TODO.md, backend/app/domains/submissions/router.py, backend/tests/submissions/test_code_snapshots.py: 로드맵이 스냅샷과 제출 라우터의 현재 미검증 분기보다 커버리지 도구와 팩토리 도입을 우선합니다. 영향은 실제 회귀가 발생해도 상위 계획이 이를 직접 막지 못한다는 점입니다. 수정은 스냅샷 압축 계약, 제출 생성 실패 경로, 권한 경계를 P0로 승격하는 것입니다.
- HIGH — backend/app/core/compression.py, backend/app/domains/submissions/router.py, backend/tests/submissions/test_code_snapshots.py: 회고의 저장소 최적화 핵심인 압축과 legacy fallback 계약이 테스트되지 않습니다. 특히 duplicate snapshot 테스트는 행 수만 확인하고 저장값이 계속 압축 상태인지, legacy plain text 조회가 안전한지 확인하지 않습니다. 수정은 압축 round-trip, invalid base64 fallback, duplicate path의 저장값 불변을 명시적으로 검증하는 것입니다.
- MEDIUM — backend/app/api/dependencies.py, backend/tests/submissions/test_code_snapshots.py: require_staff 가 허용하는 instructor 와 ta 경계와 get_optional_current_user 의 inactive 와 invalid token 분기가 미보호입니다. 영향은 권한 리팩토링 회귀를 조기에 못 잡는 것입니다. 수정은 의존성 단위 테스트 또는 엔드포인트 매트릭스 테스트를 추가하는 것입니다.
- MEDIUM — backend/tests/core/test_migrations.py, backend/app/models/schemas.py, 20260403.md: 마이그레이션 테스트가 회고의 스냅샷과 Alembic 변경 범위를 충분히 반영하지 않습니다. 영향은 신규 테이블 누락이나 재실행 회귀를 놓칠 수 있다는 점입니다. 수정은 code_snapshots 존재, 재실행 idempotency, legacy 데이터 호환을 명시하는 것입니다.
- LOW — backend/TDD_TODO.md, backend/app/domains/submissions/router.py: 비동기 테스트 최적화를 별도 상위 항목으로 둔 현재 순서는 다소 앞서갑니다. 대상 라우터는 현재 대부분 동기 def 엔드포인트이며 즉시 위험은 다른 곳이 더 큽니다. 수정은 async 항목을 후순위 탐색성 작업으로 내리는 것입니다.

## Recommendations
1. backend/TDD_TODO.md 최상단을 현재 기능 회귀 방어 중심으로 재편하십시오: 스냅샷 압축과 중복과 권한, 제출 생성과 조회와 피드백 실패 경로, 마이그레이션 스냅샷 테이블 보호.
2. 회고 항목을 테스트 작업으로 직결하십시오: AssignmentBase 와 Homework 와 Exam 공통 필드 계약, require_staff 역할 매트릭스, legacy plain text fallback, Alembic backfill 및 재실행 안전성.
3. backend/tests/homework/test_export_api.py 와 backend/tests/homework/test_homework_zip_parser.py 에는 권한 negative, 빈 결과, 중복 이름, 빈 ZIP 등 운영형 edge case를 추가하십시오.
4. pytest-cov, factory_boy, Hypothesis, Testcontainers, async 도구는 기능 회귀 팩을 보강한 뒤 enablement 섹션으로 이동하십시오.

## Architectural Status
WATCH

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
- 기능별 회귀 우선: 즉시 위험을 낮추지만 문서 구조를 더 구체적으로 써야 합니다.
- 범용 인프라 우선: 장기 생산성은 좋아질 수 있으나 현재 회고 기반 회귀를 직접 막지 못합니다.
- Testcontainers 와 async 선행: 환경 유사성은 높아지지만 현재 대상 코드의 가장 큰 미검증 분기를 뒤로 미룹니다.
