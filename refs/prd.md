# neoESPA PRD

- 문서 상태: Working Draft
- 기준일: 2026-03-25
- 문서 목적: 현재 저장소 기준 제품 범위를 정리하고, 이후 개발 우선순위를 `완료`, `계획`, `발전 단계`로 구분한다.
- 연계 문서: 상세 구현 순서와 작업 분해는 `refs/plan.md`에서 관리한다.

## 1. 문서 범위

이 문서는 현재 코드베이스, 테스트, 프론트엔드 화면, 운영 문서를 기준으로 `neoESPA`의 제품 상태를 다시 정리한 기준 문서다.

이 문서가 답하려는 질문은 세 가지다.

1. 지금 실제로 사용할 수 있는 기능은 어디까지인가.
2. 현재 운영상 가장 먼저 닫아야 하는 공백은 무엇인가.
3. 그 다음 단계의 확장과 하드닝은 어떤 방향으로 가야 하는가.

문서 작성 기준은 다음과 같다.

- **완료**: 현재 저장소에서 UI, API, 테스트, 운영 문서 근거가 함께 확인되는 범위
- **계획**: 현재 제품의 핵심 공백으로, 이미 문서와 코드 구조상 다음 단계로 명시된 범위
- **발전 단계**: 단기 운영 갭을 넘어서 구조 확장 또는 운영급 하드닝이 필요한 범위

## 2. 제품 개요

`neoESPA`는 프로그래밍 수업 운영을 위한 통합 플랫폼이다. 학생은 공지, 자료, 과제, 제출 결과, 알림, 협업 기능을 한 곳에서 사용하고, 운영자는 `/admin` 콘솔과 관리자 API를 통해 과제·공지·사용자·채점 설정·표절 검사를 관리한다.

현재 제품은 “로컬에서 바로 띄워 보고, 과제 제출 흐름까지 확인할 수 있는 상태”를 기준선으로 삼고 있다. 반면 시험 전용 UI, 게시판형 자료실/Q&A, 멀티 코스 구조는 아직 남은 작업으로 문서와 코드에 함께 표시돼 있다.

## 3. 현재 제품 기준선

### 3.1 사용자 유형

- **학생**: 회원가입, 로그인, 과제 조회/제출, 결과 확인, 공지/자료 열람, 알림 확인, 협업 참여
- **TA/조교**: 관리자 콘솔 접근, 공지/과제 운영 보조, 표절 탐지 확인
- **관리자/교수**: 과제/공지/자료/사용자/설정/표절 운영, 채점 및 export, 관리자 계정 생성

### 3.2 현재 확인 가능한 진입점

- 학생 화면: `/login`, `/register`, `/dashboard`, `/profile`, `/homework`, `/homework/[num]`, `/homework/result`, `/notice`, `/materials`, `/notifications`, `/collab`
- 관리자 화면: `/admin`
- 백엔드 문서: `/docs`, `/openapi.json`
- 관리자 CLI: `uv run neoespa-admin create-admin ...`

## 4. 완료

이 섹션은 현재 프로젝트에서 이미 동작하고 있다고 보는 기준선이다.

### 4.1 계정과 인증

완료 범위:

- 회원가입, 로그인, JWT 기반 인증
- 공개 가입 후 기본 역할 부여
- 비밀번호 변경
- 자기 정보 조회와 수정
- 관리자에 의한 역할 변경, 활성/비활성 전환, 비밀번호 초기화, 대량 등록

현재 제품은 단일 계정 체계로 학생과 운영자 기능을 나누고 있다. 학생과 운영자는 같은 인증 흐름을 쓰고, 권한은 RBAC로 분리된다.

근거:

- 프론트엔드: `frontend/src/app/register/page.tsx`, `frontend/src/app/login/page.tsx`, `frontend/src/app/profile/page.tsx`
- 백엔드: `backend/app/domains/auth/router.py`, `backend/app/domains/users/router.py`
- 테스트: `backend/tests/test_auth_api.py`, `backend/tests/test_user_admin_api.py`

### 4.2 학생 과제 흐름

완료 범위:

- 과제 목록 조회
- 과제 상세 조회
- 허용 언어와 일정 확인
- 코드 제출
- 제출 이력 조회
- 제출 결과 화면 확인
- 학생 대시보드에서 제출 현황과 최근 점수 확인

현재 제품의 가장 강한 기준선은 과제 제출 흐름이다. 루트 README도 이 범위를 “현재 바로 확인 가능한 상태”로 규정하고 있다.

근거:

- 프론트엔드: `frontend/src/app/homework/page.tsx`, `frontend/src/app/homework/[num]/page.tsx`, `frontend/src/app/homework/result/page.tsx`, `frontend/src/app/dashboard/page.tsx`
- 백엔드: `backend/app/domains/homework/router.py`, `backend/app/domains/submissions/router.py`, `backend/app/domains/dashboard/router.py`
- 테스트: `backend/tests/test_homework_api.py`, `backend/tests/test_submission_api.py`, `backend/tests/test_end_to_end_api.py`, `backend/tests/test_dashboard_api.py`

### 4.3 공지, 강의자료, 알림

완료 범위:

- 공지 목록/상세 조회
- 예약 게시 및 pinned 공지 처리
- 강의자료 조회
- 운영자의 자료 등록 및 공개 여부 관리
- 알림 목록 조회와 읽음 처리

주의할 점은 현재 강의자료는 **게시판형 자료실**이 아니라 **링크형 자료 등록/조회** 흐름이라는 점이다. 이 범위는 완료지만, 게시판형 자료실 요구까지 충족된 것은 아니다.

근거:

- 프론트엔드: `frontend/src/app/notice/page.tsx`, `frontend/src/app/notice/[num]/page.tsx`, `frontend/src/app/materials/page.tsx`, `frontend/src/app/notifications/page.tsx`
- 백엔드: `backend/app/domains/notices/router.py`, `backend/app/domains/materials/router.py`, `backend/app/domains/notifications/router.py`
- 테스트: `backend/tests/test_notice_api.py`, `backend/tests/test_notice_admin_api.py`, `backend/tests/test_material_api.py`, `backend/tests/test_notification_api.py`

### 4.4 관리자 운영 콘솔

완료 범위:

- `/admin` 단일 콘솔
- Overview 탭 운영 현황 확인
- Homework 탭 과제 CRUD, 테스트케이스, 허용 언어, 린트 주차 관리
- Notices 탭 공지 CRUD, draft/published/scheduled/pinned 관리
- Materials 탭 링크형 자료 등록
- Users 탭 사용자 검색, 역할 변경, 활성/비활성, 비밀번호 초기화, 대량 등록
- Settings 탭 전역 린트 관련 설정 수정
- Plagiarism 탭 표절 탐지 실행과 pair 비교

현재 관리자 UI는 “모든 관리자 API를 다 품은 콘솔”은 아니지만, 수업 운영 핵심 기능은 하나의 화면에서 처리할 수 있는 상태다.

근거:

- 프론트엔드: `frontend/src/app/admin/page.tsx`, `frontend/src/components/admin/*.tsx`
- 백엔드: `backend/app/domains/homework/router.py`, `backend/app/domains/notices/router.py`, `backend/app/domains/materials/router.py`, `backend/app/domains/users/router.py`, `backend/app/domains/settings/router.py`, `backend/app/domains/plagiarism/router.py`, `backend/app/domains/observability/router.py`
- 테스트: `backend/tests/test_homework_admin_api.py`, `backend/tests/test_notice_admin_api.py`, `backend/tests/test_material_api.py`, `backend/tests/test_user_admin_api.py`, `backend/tests/test_settings_api.py`, `backend/tests/test_plagiarism_api.py`, `backend/tests/test_dashboard_api.py`

### 4.5 자동 채점, 재채점, export, 운영 관측

완료 범위:

- 제출 직후 자동 채점 시도
- 채점 큐와 재채점
- 점수 조정
- 성적 CSV export
- 최신 제출 ZIP archive export
- 감사 로그와 시스템 이벤트 조회

이 영역은 UI보다 백엔드 API와 테스트 근거가 더 강하다. 즉, 제품 기능으로는 존재하지만 일부는 관리자 UI보다 API 중심으로 노출된다.

근거:

- 백엔드: `backend/app/domains/grading/router.py`, `backend/app/domains/observability/router.py`
- 테스트: `backend/tests/test_grading_api.py`, `backend/tests/test_grading_admin_api.py`, `backend/tests/test_export_api.py`

### 4.6 협업과 시험 API

완료 범위:

- 협업 세션 생성, 참여, 코드 동기화, 채팅, 히스토리 조회
- WebSocket 기반 실시간 협업
- 시험 목록, 시험 생성, 시험 제출 API

다만 시험은 **API 기준 완료**로 보는 것이 맞고, 학생이 사용하는 별도 시험 전용 화면까지 완료로 보기는 어렵다.

근거:

- 프론트엔드: `frontend/src/app/collab/page.tsx`
- 백엔드: `backend/app/domains/collab/router.py`, `backend/app/domains/exams/router.py`
- 테스트: `backend/tests/test_collab_api.py`, `backend/tests/test_exam_api.py`

## 5. 계획

이 섹션은 현재 저장소와 문서에서 가장 먼저 메워야 할 제품 공백이다. 루트 README, `refs/plan.md`, 현재 UI 범위를 같이 보면 다음 항목들이 가까운 계획으로 가장 자연스럽다.

### 5.1 시험 전용 UI

현재 시험 API는 존재하지만, 프론트엔드에는 시험 전용 학생 화면이 없다. 이 때문에 “시험 기능이 있다”와 “학생이 시험을 실제로 응시한다” 사이에 사용자 경험 공백이 남아 있다.

계획 범위:

- 시험 목록 화면
- 시험 상세/응시 화면
- 시험 제출 후 결과 확인 화면

근거:

- `README.md`
- `refs/plan.md`
- `backend/app/domains/exams/router.py`
- `backend/tests/test_exam_api.py`

### 5.2 게시판형 자료실과 Q&A

현재 자료는 링크형 관리까지만 닫혀 있다. 반면 레거시 요구와 계획 문서는 자료실/Q&A/댓글/첨부가 있는 게시판형 운영을 목표로 잡고 있다.

계획 범위:

- 자료실 게시판
- 질문과 답변 게시판
- 댓글
- 첨부 파일
- 목록/상세/작성/수정 흐름

이 항목은 현재 프로젝트에서 가장 분명한 미구현 영역 중 하나다.

근거:

- `README.md`
- `refs/plan.md`
- 현재 프론트엔드 route 목록
- 현재 materials 구현 범위

### 5.3 코스 허브 화면

지금의 학생 대시보드는 과제 진행 현황에 강점이 있지만, 공지/자료/Q&A/과제 제출을 한 화면에서 묶는 “과목 홈 허브”는 아니다. 제품 경험을 더 일관되게 만들려면 이 허브가 필요하다.

계획 범위:

- 공지, 자료, 질문, 과제 제출을 한 화면에서 요약
- 학생 관점의 통합 진입점 정리

근거:

- `refs/prd.md`의 기존 요구사항
- `refs/plan.md`
- `frontend/src/app/dashboard/page.tsx`

### 5.4 상세 채점 결과와 전용 린트 뷰어

현재 결과 화면은 총점, functional score, lint score, 상태, 제출 이력까지는 제공한다. 그러나 테스트케이스별 결과, 패널티 근거, 규칙 설명, 전용 린트 뷰까지 닫혀 있다고 보기는 어렵다.

계획 범위:

- 테스트케이스별 결과 노출 강화
- 패널티 근거 표시
- 규칙 설명과 주차 가이드
- 전용 린트 결과 화면

이 항목은 “완전한 미구현”보다는 “부분 구현 후 보강 필요”에 가깝다.

근거:

- `frontend/src/app/homework/result/page.tsx`
- `refs/plan.md`

### 5.5 린트 운영 parity UI

현재 Settings 탭은 일부 전역 `lint_` 설정을 수정할 수 있다. 그러나 레거시 수준의 Score/Option/Message/Rule 전체 편집 기능까지 재현한 상태는 아니다.

계획 범위:

- 점수 설정 UI
- 옵션 설정 UI
- 메시지 번역 관리 UI
- 주차별 규칙 템플릿 UI

근거:

- `frontend/src/components/admin/AdminSettingsManager.tsx`
- `backend/tests/test_settings_api.py`
- `refs/plan.md`

### 5.6 표절 판정 후속 워크플로

현재 제품은 표절 탐지 실행과 pair 비교까지는 제공한다. 하지만 최종 판정, 메모, 점수 반영, 감사 로그 연결을 하나의 운영 흐름으로 닫았다고 보기는 어렵다.

계획 범위:

- 표절 pair 최종 판정
- 판정 메모 저장
- 점수 반영 흐름 연결
- 감사 로그와 판정 내역 연결

근거:

- `frontend/src/components/admin/AdminPlagiarismManager.tsx`
- `backend/tests/test_plagiarism_api.py`
- `refs/plan.md`

### 5.7 멤버십 상태와 승인 흐름

현재는 공개 가입과 기본 프로필 편집은 가능하지만, 레거시 운영에서 쓰던 준회원/정회원 같은 상태 흐름을 현재 권한 체계 안에서 다시 설계한 상태는 아니다.

계획 범위:

- 멤버십 상태 모델
- 승인/전환 흐름
- 화면에서 상태 확인 및 운영 처리

근거:

- `frontend/src/app/profile/page.tsx`
- `refs/plan.md`

## 6. 발전 단계

이 섹션은 지금 당장 학생/운영자 핵심 흐름을 닫는 일보다 뒤에 두되, 제품의 다음 성장 단계를 위해 방향을 명확히 해 둘 필요가 있는 영역이다.

### 6.1 offering 기반 멀티 코스 구조

현재 제품은 단일 강좌 운영 기준이 강하다. 장기적으로는 학기, 분반, 과목 offering 단위로 자산과 권한을 분리해야 한다.

발전 방향:

- `courses`, `terms`, `course_offerings`, `course_enrollments` 도입
- 과제, 공지, 자료, 시험, 게시판의 offering 스코프 분리
- offering 기반 권한 모델 재정리

근거:

- `README.md`
- `refs/plan.md`

### 6.2 외부 연동

멀티 코스 구조가 잡히면 그 위에 LMS 명부 동기화, 성적 export 연동, SSO, 외부 identity 연결을 올릴 수 있다. 이 영역은 현재 기준선보다 제품 외연 확장에 가깝다.

발전 방향:

- LMS roster sync
- grade export 연계
- SSO
- 외부 identity/provider 연동

근거:

- `refs/plan.md`
- 기존 PRD/운영 문서

### 6.3 운영급 실행기와 저장소 하드닝

현재 채점 실행기는 개발 및 수업 운영 기준선으로는 충분하지만, 운영급 샌드박스와 외부 저장소 구조까지 닫혀 있지는 않다. 이 영역은 기능 추가보다 플랫폼 하드닝에 가깝다.

발전 방향:

- 더 강한 격리와 자원 제한을 가진 채점 실행기
- 실행 메타데이터 기록
- 외부 객체 스토리지 기반 산출물 관리
- 백업/복구 자동화와 운영 경보 강화

근거:

- `refs/memo.md`
- `refs/GUIDE.md`
- `refs/plan.md`

## 7. 제품 요구사항 정리

아래는 현재 단계별로 다시 정리한 요구사항 요약이다.

| ID | 요구사항 | 단계 | 비고 |
| --- | --- | --- | --- |
| PRD-01 | 단일 계정 기반 인증과 권한 분리 | 완료 | 현재 회원가입/로그인/JWT/RBAC 제공 |
| PRD-02 | 자기 정보 수정과 비밀번호 변경 | 완료 | 멤버십 상태 흐름은 계획 |
| PRD-03 | 과제 목록/상세/제출/결과/이력 | 완료 | 현재 제품의 핵심 기준선 |
| PRD-04 | 상세 채점 결과와 린트 피드백 강화 | 계획 | 결과 화면은 있으나 상세성 보강 필요 |
| PRD-05 | 관리자 운영 콘솔 | 완료 | `/admin` 기준 핵심 운영 가능 |
| PRD-06 | 린트 운영 parity UI | 계획 | 현재는 일부 settings 수준 |
| PRD-07 | 코스 허브 화면 | 계획 | 현재 대시보드는 허브와 다름 |
| PRD-08 | 게시판형 자료실/Q&A/댓글/첨부 | 계획 | 현재 미구현 |
| PRD-09 | 제출 채널 통합 경험 | 계획 | 과제 제출은 있으나 레거시 게시판 흐름 통합 필요 |
| PRD-10 | 표절 판정 후속 운영 | 계획 | 탐지/비교는 완료, 판정 워크플로는 미완성 |
| PRD-11 | 시험 전용 UI | 계획 | API는 있으나 전용 학생 UI 없음 |
| PRD-12 | 협업 기능 유지 및 보강 | 완료 | 기본 협업 기능은 현재 제공 |
| PRD-13 | offering 기반 멀티 코스 구조 | 발전 단계 | 구조 확장 영역 |
| PRD-14 | LMS/SSO/외부 identity 연동 | 발전 단계 | Phase 2 성격 |
| PRD-15 | 운영급 샌드박스/스토리지 | 발전 단계 | 플랫폼 하드닝 |
| PRD-16 | 운영 자동화와 복구 고도화 | 발전 단계 | 감사/백업 기본선 위 확장 |

## 8. 수용 기준

### 8.1 완료 기준 유지

- 학생이 회원가입 후 로그인해 과제 제출 흐름을 끝까지 사용할 수 있어야 한다.
- 운영자가 `/admin`에서 공지, 과제, 사용자, 설정, 표절 탐지의 핵심 작업을 수행할 수 있어야 한다.
- 관리자 API와 테스트가 현재 운영 기준선을 지속적으로 보장해야 한다.

### 8.2 계획 단계 완료 조건

- 시험 UI, 게시판형 자료실/Q&A, 코스 허브, 상세 채점 결과, 린트 parity UI, 표절 후속 흐름이 실제 화면 기준으로 닫혀야 한다.
- 학생과 운영자가 별도 우회 경로 없이 핵심 학습/운영 흐름을 한 제품 안에서 끝낼 수 있어야 한다.

### 8.3 발전 단계 완료 조건

- 멀티 코스 구조가 현재 단일 강좌 흐름을 깨지 않고 확장돼야 한다.
- 외부 연동이 offering 단위로 안전하게 작동해야 한다.
- 실행기, 저장소, 복구 자동화가 운영급 기준으로 강화돼야 한다.

## 9. 문서 사용 원칙

- 현재 기능 범위를 설명할 때는 이 문서를 기준으로 본다.
- API 계약은 `refs/API.md`, 관리자 운영 흐름은 `refs/GUIDE.md`, 작업 순서는 `refs/plan.md`를 본다.
- 이후 작업은 가능하면 `PRD-*` ID 기준으로 계획과 구현을 연결한다.
