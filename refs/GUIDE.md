# neoESPA 관리자 운영 가이드

이 문서는 neoESPA를 운영하는 관리자용 안내서다. 실제 관리자 콘솔에서 할 수 있는 일과, 현재는 API 또는 CLI로만 처리해야 하는 일을 분리해서 정리한다.

## 1. 이 문서가 다루는 범위

- **UI**: 프론트엔드 `/admin` 관리자 콘솔에서 바로 수행 가능한 작업
- **API-only**: 백엔드 API는 있지만 현재 관리자 UI 연결 근거가 없는 작업
- **CLI-only**: 서버에서 명령어로만 수행하는 작업

엔드포인트 상세 계약과 요청/응답 예시는 [API.md](./API.md), 전체 목록은 [openapi-reference.md](./openapi-reference.md)를 참고한다.

## 2. 운영 시작 전 확인

### 접속 주소

- 서비스 UI: `http://localhost:3000`
- 관리자 콘솔: `http://localhost:3000/admin`
- 백엔드 Swagger: `http://localhost:8000/docs`

### 샘플 계정

- 관리자: `admin / pllab2026`
- 학생: `testuser / qwer1234`

### 접근 권한

- `/admin` 페이지 자체는 `admin`, `instructor`, `ta`가 접근할 수 있다.
- 다만 **Users** 탭과 **Settings** 탭은 실제 UI에서 `admin`만 노출된다.

## 3. 관리자 콘솔(UI)

현재 관리자 UI는 `/admin` 단일 콘솔이다. 상단 탭에서 운영 영역을 전환한다.

### 3-1. Overview 탭 — **UI**

운영 현황을 빠르게 보는 화면이다.

할 수 있는 일:

- 과제별 제출률과 실패 현황 확인
- 채점 대기열 상태 확인
- 최근 운영 이벤트 확인

이 탭은 “지금 어떤 과제에서 문제가 생기고 있는가”를 파악하는 첫 화면으로 쓰면 된다.

### 3-2. Homework 탭 — **UI**

일반적인 과제 생성과 수정은 이 탭에서 처리한다.

할 수 있는 일:

- 과제 제목, 설명, 시작 시각, 마감 시각 설정
- 허용 언어 지정
- 린트 활성화 여부와 주차(`lint_week`) 설정
- 테스트케이스 추가/수정
- 과제 수정 및 삭제

운영 팁:

- 학생 제출 언어 제한은 실제 제출 API에 반영된다.
- 시작 전 과제는 학생 목록에서 숨겨지고, 마감 후에는 제출이 막힌다.

### 3-3. Notices 탭 — **UI**

공지 작성과 게시 상태 관리를 담당한다.

할 수 있는 일:

- 공지 생성, 수정, 삭제
- draft / published / scheduled 상태 관리
- pinned 공지 설정

운영 팁:

- 게시된 공지는 학생 공지 목록과 알림 흐름에 연결된다.
- 예약 게시 공지는 게시 시점 전까지 학생에게 숨겨진다.

### 3-4. Materials 탭 — **UI**

강의자료 링크를 등록하고 공개 여부를 관리한다.

할 수 있는 일:

- 자료 제목, 설명, URL 입력
- 공개(`is_published`) 여부 설정

주의:

- 현재 근거상 자료 관리는 **링크 등록형**이다.
- 파일 업로드형 자료 관리 UI 근거는 확인되지 않았다.

### 3-5. Users 탭 — **UI, admin 전용**

사용자 계정 운영 화면이다.

할 수 있는 일:

- 사용자 검색과 목록 조회
- 역할 변경 (`student`, `ta`, `instructor`, `admin`)
- 활성/비활성 전환
- 비밀번호 초기화
- 대량 등록

운영 팁:

- 사용자를 비활성화하면 이후 로그인은 `403`으로 막힌다.
- 대량 등록은 기존 사용자를 건너뛰는 옵션과 기본 비밀번호를 함께 쓸 수 있다.

### 3-6. Settings 탭 — **UI, admin 전용**

전역 채점 설정, 특히 린트 관련 설정을 조정한다.

대표 항목:

- `lint_calc_weight`
- `lint_calc_panalty`
- `lint_err_performance`
- `lint_set_default`

운영 팁:

- 이 설정은 실제 채점 결과의 `quality_score`에 반영된다.
- 설정 변경 후 대표 과제로 한 번 채점해 결과가 의도대로 바뀌는지 확인하는 편이 안전하다.

### 3-7. Plagiarism 탭 — **UI**

표절 검사를 수동으로 실행하고 비교 결과를 확인한다.

할 수 있는 일:

- 과제 선택 후 표절 검사 실행
- flagged pair 목록 조회
- 두 제출 코드 비교

주의:

- 현재 표절 검사는 **수동 실행 중심**으로 이해하는 것이 맞다.
- 과제 관리 화면에 표절 관련 예약 필드가 있더라도 자동 처리 기본 동작 근거는 없다.

## 4. 관리자 운영 업무별 추천 흐름

### 새 과제 배포

1. `/admin` → **Homework** 탭으로 이동한다.
2. 제목, 설명, 시작/마감 시각, 허용 언어를 입력한다.
3. 필요하면 린트와 테스트케이스를 설정한다.
4. 저장 후 학생 과제 목록 노출 시점을 일정으로 제어한다.

### 공지 게시

1. `/admin` → **Notices** 탭으로 이동한다.
2. 제목, 작성자, 내용, 게시 시각을 입력한다.
3. 필요하면 pinned와 published 상태를 설정한다.
4. 게시 후 학생 공지와 알림 반영 여부를 확인한다.

### 강의자료 공개

1. `/admin` → **Materials** 탭으로 이동한다.
2. 제목, 설명, 링크를 입력한다.
3. `is_published`를 켜면 학생 목록에 노출된다.

### 사용자 계정 정리

1. `/admin` → **Users** 탭으로 이동한다.
2. 검색으로 대상 계정을 찾는다.
3. 역할 변경, 비활성화, 비밀번호 초기화 중 필요한 작업을 수행한다.
4. 대량 등록은 CSV형 데이터 묶음을 준비한 뒤 한 번에 처리한다.

### 표절 검사 확인

1. `/admin` → **Plagiarism** 탭으로 이동한다.
2. 과제를 선택해 검사를 실행한다.
3. flagged pair를 열어 좌우 코드를 비교한다.

## 5. 현재 API로만 처리하는 작업(API-only)

아래 기능은 OpenAPI에는 존재하지만, 현재 프론트엔드 관리자 UI 연결 근거를 확인하지 못한 항목들이다. 운영 문서에는 포함하되, 실제 실행은 API 호출 기준으로 이해해야 한다.

### 5-1. 관리자 과제 import — **API-only**

- 경로: `POST /api/admin/homeworks/import`
- 목적: 문제 파일(`problem_file`)과 입출력 ZIP(`input_zip`, `output_zip`)을 함께 올려 과제를 등록

이 방식은 일반 JSON 과제 생성과 다르다. `allowed_languages`를 JSON 문자열로 보내야 하고, ZIP 파일쌍 이름이 서로 맞아야 한다.

대표 실패:

- 무토큰 `401`
- 비관리자 `403`
- 필수 파일 누락 `422`
- 손상 ZIP, 확장자 오류, 날짜 오류 `400`

### 5-2. 감사 로그와 시스템 이벤트 — **API-only**

- `GET /api/admin/audit-logs`
- `GET /api/admin/observability/events`

대시보드보다 더 세밀한 운영 추적이 필요할 때 사용한다.

### 5-3. 수동 채점과 큐 제어 — **API-only**

- `POST /api/admin/submissions/{submission_id}/grade`
- `POST /api/admin/submissions/{submission_id}/queue`
- `POST /api/admin/submissions/{submission_id}/requeue`
- `PATCH /api/admin/submissions/{submission_id}/score`
- `POST /api/admin/grading/process-next`

이 기능은 실패 제출 재처리, 점수 수동 보정, 대기열 관리에 쓴다.

### 5-4. 데이터 내보내기 — **API-only**

- `GET /api/admin/homeworks/{homework_num}/grades/export`
- `GET /api/admin/homeworks/{homework_num}/submissions/archive`

성적 CSV와 최신 제출 ZIP을 받을 때 사용한다.

### 5-5. 시험 생성 — **API-only**

- `POST /api/admin/exams`

현재 저장소 메모와 README 기준으로 시험 전용 프론트엔드 화면은 아직 없다. 시험 관리가 필요하면 API 기준으로 처리해야 한다.

## 6. 서버 명령으로만 처리하는 작업(CLI-only)

### 관리자 계정 생성 — **CLI-only**

백엔드 서버 환경에서 관리자 계정을 직접 만들 수 있다.

```bash
cd backend
uv run neoespa-admin create-admin \
  --id ops-admin \
  --sid 10050001 \
  --name "Operations Admin" \
  --phone "010-5555-0001" \
  --email "ops-admin@example.com" \
  --password "change-me-now"
```

같은 명령은 모듈 실행 형태로도 가능하다.

```bash
cd backend
uv run python -m app.cli create-admin \
  --id ops-admin \
  --sid 10050001 \
  --name "Operations Admin" \
  --phone "010-5555-0001" \
  --email "ops-admin@example.com" \
  --password "change-me-now"
```

옵션:

- `--inactive`: 비활성 상태로 관리자 계정을 생성

## 7. 운영 시 주의할 점

- 채점 실행기는 타임아웃과 임시 디렉터리 격리 수준이며, 운영급 샌드박스는 아니다.
- 린트 품질 점수는 현재 문서 기준으로 Python 제출 흐름에만 실제 반영 근거가 있다.
- 시험 API는 존재하지만 전용 학생 UI는 아직 없다.
- 자료실은 현재 게시판형 파일 업로드보다 링크형 운영 흐름에 가깝다.

## 8. 어떤 문서를 언제 볼지

- 관리자 UI에서 할 수 있는 일을 알고 싶을 때: `refs/GUIDE.md`
- 요청/응답 JSON과 상태 코드를 확인할 때: `refs/API.md`
- 전체 엔드포인트 목록만 빠르게 확인할 때: `refs/openapi-reference.md`
- 샘플 계정, 실행 방법, 로컬 실행 팁이 필요할 때: `README.md`, `backend/README.md`
