# neoESPA 온라인 저지 백엔드 개선 계획

## 1. 문서 목적과 범위

이 문서는 neoESPA를 백준 Online Judge(BOJ) 및 DMOJ에 가까운 운영형 온라인 저지로 발전시키기 위한 백엔드 개선 계획입니다. 사용자 혹평의 핵심인 “문제 등록과 관리자 업무가 웹에서 끝나지 않고 터미널 작업을 요구한다”는 문제를 우선 해결합니다.

이번 단계의 범위는 백엔드 모델, API, 비동기 작업, 권한, 감사, 저장소 및 검증 체계입니다. 프론트엔드 화면과 UX 계획은 백엔드 계약이 확정된 뒤 별도 문서로 작성합니다.

완료 조건은 다음과 같습니다.

- 최초 최고 관리자 부트스트랩과 인프라 배포를 제외한 일상 운영 업무를 Admin API로 수행할 수 있습니다.
- 문제 작성, 테스트 데이터 업로드, 검증, 시험 채점, 게시, 수정, 재채점의 전 과정을 API로 수행할 수 있습니다.
- 장시간 작업은 HTTP 요청이나 단일 프로세스 메모리에 묶이지 않고, 진행률·실패 이유·재시도를 조회할 수 있습니다.
- 관리자 권한이 업무 단위로 분리되고 모든 민감 작업에 감사 기록이 남습니다.
- 기존 과제·시험·제출 API의 동작을 유지하면서 점진적으로 온라인 저지 도메인으로 확장합니다.
- 학습자 코드는 호스트 `subprocess`에서 직접 실행하지 않으며, 격리 실행기가 준비되지 않은 운영 환경에서는 자동 채점을 활성화하지 않습니다.

## 2. 비교 기준과 조사 근거

### 2.1 비교 서비스에서 가져올 원칙

DMOJ는 관리자 웹에서 사용자 관리와 문제 지문 작성을 제공하고, 문제별·언어별 자원 제한, 런타임 데이터 생성기, 사용자 정의 출력 검증기, 다수 채점 서버, 실시간 제출 상태, 세밀한 운영 권한을 지원합니다. 대회는 ICPC·IOI 등의 채점 형식, system testing, 숨김 스코어보드, 가상 참가, 접근 제한을 지원합니다.

BOJ는 공개된 관리자 내부 구현을 확인하기 어렵지만, 사용자 관점에서 문제 상태와 재채점 상태를 명확히 노출합니다. 대회 운영 규칙은 문제 수정 공지와 재채점의 운영 통제를 요구하므로, 문제 데이터 변경을 단순 덮어쓰기가 아니라 버전·공지·감사 이벤트로 다뤄야 합니다.

참고 자료:

- [DMOJ online-judge 기능 및 Admin 개요](https://github.com/DMOJ/online-judge)
- [DMOJ judge-server와 문제 데이터 형식](https://github.com/DMOJ/judge-server)
- [DMOJ 대회 모델: 공개 범위, 접근 제한, system testing 관련 설정](https://github.com/DMOJ/online-judge/blob/master/judge/models/contest.py)
- [DMOJ CLI 문제 등록이 실제 운영에서 사용되지 않아 노후화된 사례](https://github.com/DMOJ/online-judge/issues/2255)
- [BOJ 대회 운영 규칙: 문제 수정 공지와 재채점 통제](https://help.acmicpc.net/rule/contest)
- [BOJ 재채점 상태가 노출되는 예시 문제](https://www.acmicpc.net/problem/18807)

### 2.2 현재 neoESPA의 강점

현재 백엔드는 이미 다음 기능을 제공합니다. 따라서 전면 재작성보다 기존 기능을 보존하고 도메인 경계를 확장하는 편이 적절합니다.

- 관리자 과제 목록·상세·생성·ZIP 임포트·수정·삭제 API가 있습니다 (`backend/app/domains/homework/router.py:228`, `backend/app/domains/homework/router.py:243`, `backend/app/domains/homework/router.py:257`, `backend/app/domains/homework/router.py:299`, `backend/app/domains/homework/router.py:497`, `backend/app/domains/homework/router.py:540`).
- 문제 파일과 입출력 ZIP을 웹 요청으로 받아 테스트케이스를 파싱하고 저장합니다 (`backend/app/domains/homework/router.py:299`, `backend/app/domains/homework/router.py:322`, `backend/app/domains/homework/router.py:405`).
- ZIP 크기, 압축 해제 크기, 파일 수, 경로 순회, UTF-8 여부를 검증합니다 (`backend/app/domains/homework/zip_parser.py:12`, `backend/app/domains/homework/zip_parser.py:45`, `backend/app/domains/homework/zip_parser.py:55`, `backend/app/domains/homework/zip_parser.py:100`, `backend/app/domains/homework/zip_parser.py:150`).
- 사용자 일괄 등록, 역할 변경, 활성화/비활성화, 비밀번호 초기화 API가 있습니다 (`backend/app/domains/users/router.py:67`, `backend/app/domains/users/router.py:106`, `backend/app/domains/users/router.py:145`, `backend/app/domains/users/router.py:228`, `backend/app/domains/users/router.py:263`).
- 개별 제출 채점·큐 등록·재등록·점수 조정·성적/소스 내보내기를 지원합니다 (`backend/app/domains/grading/router.py:18`, `backend/app/domains/grading/router.py:92`, `backend/app/domains/grading/router.py:108`, `backend/app/domains/grading/router.py:131`, `backend/app/domains/grading/router.py:217`, `backend/app/domains/grading/router.py:242`).
- Admin 대시보드, 시스템 이벤트, 감사 로그 조회 API가 있습니다 (`backend/app/domains/observability/router.py:15`, `backend/app/domains/observability/router.py:23`, `backend/app/domains/observability/router.py:32`).
- 공지, 시스템 설정, 표절 검사 등 웹 운영 기반이 이미 있습니다 (`backend/app/domains/notices/router.py:46`, `backend/app/domains/settings/router.py:16`, `backend/app/domains/plagiarism/router.py:14`).

### 2.3 현재 구조의 핵심 격차

| 영역 | 현재 상태 | BOJ/DMOJ 수준에서 필요한 상태 | 우선순위 |
| --- | --- | --- | --- |
| 문제 도메인 | `Homework`가 지문·일정·채점 옵션을 함께 보유 (`backend/app/models/schemas.py:112`, `backend/app/models/schemas.py:124`) | 재사용 가능한 `Problem`과 과제/대회 배치를 분리 | P0 |
| 문제 수명주기 | 생성 즉시 사용 가능하며 초안·검증·게시·보관 상태가 없음 | draft → validating → ready → published → archived 상태 전이 | P0 |
| 테스트 데이터 | 테스트케이스 전체를 JSON 규칙에 보관 (`backend/app/services/grading_service.py:319`) | 파일 메타데이터·버전·해시·그룹·점수 정책을 정규화하고 본문은 과목별 content-addressed artifact store에 저장 | P0 |
| 채점 정책 | 단순 출력 비교와 일부 공백/순서 옵션 중심 (`backend/app/services/grading_service.py:397`) | standard/special/interactive checker, 그룹 채점, 언어별 제한, 출력 제한 | P1 |
| 재채점 | 제출 한 건의 `requeue`만 제공 (`backend/app/domains/grading/router.py:108`) | 문제/버전/대회/사용자/결과 범위의 일괄 재채점 작업 | P0 |
| 작업 큐 | 프로세스 내부 `deque`이며 재시작 시 DB 상태를 순회 (`backend/app/services/grading_queue.py:12`, `backend/app/services/grading_queue.py:58`) | DB 기반 영속 작업, lease, heartbeat, retry, cancellation, progress | P0 |
| 큐 처리 | Admin이 `/admin/grading/process-next`를 호출해야 다음 작업 처리 (`backend/app/domains/grading/router.py:178`) | 독립 worker가 자동 처리하고 Admin은 관찰·재시도만 수행 | P0 |
| 권한 | `admin/instructor/ta` 역할 문자열을 라우트별로 사용 (`backend/app/api/dependencies.py:48`, `backend/app/api/dependencies.py:60`) | 문제 작성·검수·게시·재채점·사용자 관리 등 capability 기반 권한 | P1 |
| 설정 | 웹 수정 가능한 설정이 lint 관련 7개에 한정 (`backend/app/core/system_settings.py:6`) | 언어, 제한 상한, 제출 정책, 채점 정책 등 안전한 운영 설정 | P1 |
| 감사 | 감사 기반은 있으나 조회 필터와 변경 전후값, 연관 작업 ID가 부족 | actor/action/target/time/result/job 기준 검색과 before/after 기록 | P1 |
| 관리자 생성 | CLI의 `create-admin`만 제공 (`backend/app/cli.py:10`) | 최초 1회 bootstrap token 이후 웹에서 관리자 초대·권한 부여 | P1 |
| 인프라 상태 | 채점 노드 registry/heartbeat/capability 모델이 없음 | 노드 상태·지원 언어·최근 작업·장애 격리 API | P1 |
| 보안 | 환경변수는 배포 시 직접 설정해야 함 (`backend/app/core/config.py:19`) | 비밀은 계속 배포 환경에서 관리하되, 비밀이 아닌 운영 설정만 웹으로 분리 | 필수 원칙 |

## 3. 목표 백엔드 구조

### 3.1 도메인 분리

`Homework`를 곧바로 제거하지 않고 다음 구조로 점진 전환합니다.

- `Problem`: 제목, slug/code, 지문, 입력/출력 설명, 제한, 공개 상태, 소유자, 태그 등 재사용 가능한 문제 정의
- `ProblemRevision`: 문제 지문과 채점 구성을 묶은 불변 버전. 게시된 버전은 직접 수정하지 않고 새 revision을 만듭니다.
- `ProblemAsset`: 이미지, 첨부 파일, checker/generator/reference solution 소스의 메타데이터와 저장 위치
- `TestCaseGroup`: 그룹 점수, 선행 그룹, 전부 통과 조건 등 채점 정책
- `TestCase`: 입력/정답 파일 참조, 점수, 공개 샘플 여부, 순서, 해시
- `AssignmentProblem`: 기존 `Homework` 또는 향후 `Contest`에 특정 `ProblemRevision`을 연결
- `JudgeJob`: 채점·시험 채점·검증·재채점을 같은 작업 모델로 표현
- `JudgeNode`: worker heartbeat, 지원 언어, 동시 처리량, 상태, 최근 오류

기존 `Homework.num`과 제출 외래키는 1차 단계에서 유지합니다. 마이그레이션 중에는 `AssignmentProblem`을 추가해 기존 API 응답을 adapter로 제공하고, 데이터 전환이 끝난 뒤 명칭 변경을 검토합니다.

### 3.2 과목별 로컬 저장소와 portable course bundle

운영 환경은 과목마다 독립된 베어 메탈 서버와 SQLite DB를 사용하고, 방학에 과목별 데이터를 취합해 교육과정 분석에 활용하는 것을 전제로 합니다. 외부 객체 저장소 제품을 도입하지 않고, SQLite와 로컬 content-addressed artifact store를 하나의 이동 가능한 course bundle로 관리합니다.

권장 디렉터리 구조:

```text
/data/neoespa/{term}/{course_id}/
├── database/
│   └── course.sqlite3
├── objects/
│   └── sha256/{hash_prefix}/{sha256}
├── manifests/
│   ├── course.json
│   ├── objects.jsonl
│   └── checksums.sha256
├── exports/
│   ├── submissions.parquet
│   ├── grading_runs.parquet
│   ├── testcase_results.parquet
│   └── learning_events.parquet
└── VERSION
```

저장 원칙:

- SQLite에는 상태, 관계, 상대 경로, SHA-256, 크기, MIME type, schema version을 저장합니다. 서버 절대 경로는 저장하지 않습니다.
- 테스트 입력·정답, 첨부 파일, checker/generator, 기준 답안, 제출 파일, 대용량 로그는 `objects/sha256/{앞 2자리}/{전체 SHA-256}` 경로에 저장합니다.
- 동일한 내용은 하나의 artifact로 저장하고 여러 문제 revision이나 제출이 참조할 수 있게 하여 과목 내·취합 시 중복을 제거합니다.
- 원본 파일명은 표시용 metadata로만 보관하고 저장 경로로 사용하지 않습니다.
- API 서비스가 경로를 직접 조합하지 않도록 저장·조회·참조 계산·checksum 검증을 `LocalArtifactStore` 서비스로 모읍니다.
- 업로드는 bundle 내부 `staging/` 임시 영역 → 크기·형식·SHA-256 검증 → content-addressed 경로로 원자적 승격 순서로 처리합니다.
- 게시된 문제 revision과 제출 원본은 immutable하게 유지합니다. 수정과 재채점은 기존 파일·결과를 덮어쓰지 않고 새 revision 또는 `GradingRun`을 추가합니다.
- SQLite row와 artifact의 정합성을 주기적으로 검사해 missing object, checksum mismatch, unreferenced object를 보고하는 reconciliation job을 운영합니다.

portable course bundle 원칙:

- course bundle은 `course.sqlite3`, `objects/`, `manifests/`, `VERSION`을 함께 포함해야 완전한 원본 보관 단위가 됩니다.
- 실행 중인 SQLite 파일을 단순 복사하지 않고 SQLite Backup API 또는 checkpoint 후 일관된 snapshot을 생성합니다.
- `course.json`에는 학기, 과목 ID, export 시각, 애플리케이션 버전, DB schema version, artifact format version을 기록합니다.
- `objects.jsonl`과 `checksums.sha256`로 bundle의 파일 목록과 무결성을 검증합니다.
- 장기 보관용 bundle은 `tar.zst` 등으로 패키징할 수 있지만, 분석 전에는 checksum과 schema version을 먼저 검증합니다.
- 운영 원본 bundle은 변경하지 않고 보존하며, 분석 데이터는 가명화 후 별도 Parquet dataset으로 생성합니다.
- bundle 자체 암호화는 적용하지 않습니다. 대신 서버 계정, 파일 권한, Admin API 권한과 접근 감사로 열람 범위를 통제합니다.
- 학기 중에는 별도 백업 장비 없이 운영 서버를 단일 저장 위치로 사용합니다. 학기 종료 시 검증된 bundle을 외장 디스크로 이전합니다.

확정된 데이터 정책:

- 제출 소스, 문제 revision, 테스트 데이터, 채점 이력과 주요 학습 이벤트는 전면 장기 보존합니다.
- 임시 업로드와 언제든 재생성할 수 있는 export만 정리 대상으로 둡니다.
- 학습자 분석 ID는 학교 전체에서 과목·학기를 넘어 동일하게 연결되는 고정 가명 ID를 사용합니다.
- 가명 ID는 별도 관리하는 학교 분석용 secret과 교내 학습자 식별자를 `HMAC-SHA256`으로 처리해 생성합니다. secret과 원본 ID 매핑은 course bundle 및 Parquet export에 포함하지 않습니다.
- 학생 동의를 전제로 데이터를 수집하되, 분석 export에는 목적에 필요한 최소 필드와 가명 ID만 포함합니다.
- course bundle은 암호화하지 않습니다.
- 최소 비용 제약에 따라 학기 중 별도 백업 디스크나 중앙 서버는 사용하지 않습니다. 학기 종료 후 외장 디스크에 장기 보관본을 생성합니다.
- 원본 `course.sqlite3`에는 계정 ID, 학번, 이름, 전화번호, 이메일, 제출 소스와 감사 payload가 포함될 수 있으므로 분석용 Parquet와 동일한 공개 범위로 취급하지 않습니다.
- 원본 bundle과 외장 디스크는 지정된 수업 운영자만 접근하며, Unix 소유자·그룹과 최소 권한(`0700` 디렉터리, `0600` 파일)을 적용합니다.
- 외장 디스크 반출·인계·복사·폐기 시 담당자, 일시, 과목, bundle checksum을 접근대장에 기록합니다. 암호화를 사용하지 않는 결정은 이 물리적·계정 접근 통제를 대체하지 않습니다.
- 학생 동의 상태와 동의한 활용 범위·시점·정책 버전을 DB에 기록하고, 분석 export 생성 전에 포함 가능 여부를 검증합니다.

학기 종료 데이터 취합 흐름:

```text
과목 서버 쓰기 동결
  → SQLite 일관 snapshot 생성
  → artifact 참조·SHA-256 검증
  → manifest와 bundle 생성
  → 분석용 식별자 가명화
  → Parquet export
  → 외장 디스크에 원본 bundle과 checksum 복사
  → 외장 디스크 복사본 재검증
  → 분석 환경에서 DuckDB로 과목·학기별 Parquet 통합 분석
```

외장 디스크의 원본 course bundle은 운영 DB를 대체하는 학기 종료 보관본입니다. 원본 bundle은 재현·감사·재분석을 위해 변경하지 않고 보존하며, Parquet와 DuckDB는 여러 과목 및 학기를 효율적으로 분석하기 위한 파생 계층으로 사용합니다. Parquet/DuckDB는 백엔드 운영 의존성이 아니라 별도 `analytics/` uv 프로젝트에서만 사용하는 오프라인 분석 도구입니다. 해당 도구 도입 전까지는 표준 라이브러리 기반 JSONL/CSV와 읽기 전용 SQLite export를 최소 호환 형식으로 제공합니다.

학기 중 단일 저장본 운영에 대한 완화책:

- 운영 서버 시작과 주기적 maintenance 시 SQLite `PRAGMA integrity_check`와 artifact checksum 표본 검사를 수행합니다.
- SQLite는 WAL mode와 정상 종료 checkpoint 절차를 사용하되, DB와 `-wal` 파일을 불완전하게 분리 복사하지 않습니다.
- 앱 오류로 인한 논리 손상에 대비해 같은 운영 디스크 안에 일관된 SQLite snapshot을 순환 보관할 수 있습니다. 이는 디스크 장애 백업은 아니지만 최근 DB 상태 복구에는 사용합니다.
- 디스크 사용량과 SMART 상태를 관측하고, 위험 임계치 도달 시 Admin 경고를 발생시킵니다.
- 외장 디스크 이전 전후에 전체 `checksums.sha256`을 검증하고, 실제 SQLite 열기와 주요 row count 대조가 성공해야 학기 종료 보관 완료로 판정합니다.
- 별도 물리 백업이 없으므로 학기 중 운영 서버 디스크 고장은 데이터 전체 손실로 이어질 수 있음을 명시적인 잔여 위험으로 수용합니다.

### 3.3 웹과 터미널의 책임 경계

웹 Admin으로 이동할 작업:

- 일반 관리자·출제자·검수자 초대 및 권한 부여
- 문제 초안 생성, 지문/제한/언어/태그 수정
- 테스트 데이터·이미지·checker·generator·정답 코드 업로드
- 패키지 사전 검증과 예제/정답 코드 시험 채점
- 문제 게시, 비공개, 보관, revision 비교 및 롤백
- 제출 검색, 중단, 개별/일괄 재채점, 작업 취소·재시도
- 로컬 채점 worker·큐·오류·감사 이벤트 조회
- 비밀이 아닌 운영 정책 변경

터미널/배포 환경에 남길 작업:

- 최초 최고 관리자 부트스트랩 또는 일회용 bootstrap token 발급
- DB migration, 백업/복구, TLS, 방화벽, Docker/프로세스 배포
- `JWT_SECRET`, 분석용 가명화 HMAC secret, OAuth secret 등 비밀 주입
- 컴파일러와 sandbox 런타임 설치 및 커널/cgroup 설정

이 경계는 터미널을 없애는 것이 아니라, 보안상 배포자 책임인 작업과 일상 운영자 책임을 구분하기 위한 것입니다.

## 4. 단계별 구현 계획

## Phase 0. 기존 동작 고정 및 API 기준선 수립

목표는 리팩터링 전에 현재 기능을 회귀 테스트로 고정하고, 프론트엔드가 의존할 Admin 계약을 OpenAPI로 명시하는 것입니다.

작업:

1. 현재 문제 등록, ZIP 임포트, 수정, 삭제, 개별 채점, 큐 재등록, 사용자 관리, 설정, 감사 로그의 통합 테스트를 보강합니다.
2. 게시 중인 과제를 수정/삭제했을 때의 현재 동작과 제출 결과 보존 여부를 테스트로 명시합니다.
3. `backend/API.md`와 실제 FastAPI OpenAPI의 불일치를 자동 검사합니다.
4. Admin 오류 응답을 `{code, message, field_errors, request_id}` 형태로 통일할 계약을 정의합니다.
5. 현재 migration runner가 down migration을 지원하지 않으므로 rollback은 "migration 직전 SQLite Backup API snapshot과 artifact manifest로 전체 복원"으로 정의합니다. restore rehearsal과 기존 DB fixture 변환 테스트를 추가합니다.
6. 현재 `SubprocessCodeRunner`가 학습자 코드를 호스트에서 직접 실행하는 위험을 보안 기준선으로 기록합니다 (`backend/app/services/code_runner.py:64`, `backend/app/services/code_runner.py:208`). 격리 실행기 적용 전 운영 자동 채점은 feature flag로 비활성화하고 수동 검증 환경에서만 허용합니다.
7. 운영 서버의 실제 CPU, RAM, 디스크, 예상 수강 인원, 최대 동시 제출, 학기당 제출량을 capacity baseline으로 기록해 이후 queue·bundle 성능 기준의 입력값으로 사용합니다.

주요 대상:

- `backend/tests/e2e/test_end_to_end_api.py`
- `backend/tests/homework/`
- `backend/tests/grading/`
- `backend/tests/users/`
- `backend/API.md`
- `backend/app/main.py`

완료 기준:

- 기존 핵심 Admin API의 성공·권한 거부·검증 실패·트랜잭션 실패 경로가 테스트됩니다.
- 현재 OpenAPI 문서를 파일로 생성해 CI에서 breaking change를 감지합니다.
- 이후 migration을 적용하기 전후로 기존 과제와 제출 수, 결과 점수가 일치합니다.
- migration 직전 snapshot에서 DB와 artifact를 복구하는 rehearsal이 성공합니다.
- 격리되지 않은 runner가 production 설정에서 실행되지 않는 자동 테스트가 통과합니다.

## Phase 1. 문제 도메인과 revision 수명주기 도입

목표는 “과제 생성”과 “문제 출제”를 분리하고, 웹에서 안전하게 초안부터 게시까지 관리하는 것입니다.

작업:

1. `Problem`, `ProblemRevision`, `ProblemAsset`, `AssignmentProblem` 모델과 migration을 추가합니다.
2. 상태를 `draft`, `validating`, `ready`, `published`, `archived`로 제한하고 허용된 전이만 서비스 계층에서 처리합니다.
3. 문제 code/slug의 중복, 제목/지문 필수값, 시간·메모리·출력 제한 상한, 허용 언어를 검증합니다.
4. 게시된 revision은 수정하지 못하게 하고, 수정 시 새 revision 초안을 복제합니다.
5. 기존 `Homework` 데이터를 문제와 배치 관계로 변환하는 idempotent migration/backfill을 작성합니다.
6. 기존 `/api/admin/homeworks`는 호환 adapter로 유지하고 새 `/api/admin/problems`를 정식 계약으로 제공합니다.

제안 API:

- `GET/POST /api/admin/problems`
- `GET/PATCH /api/admin/problems/{problem_id}`
- `POST /api/admin/problems/{problem_id}/revisions`
- `GET /api/admin/problems/{problem_id}/revisions`
- `GET /api/admin/problems/{problem_id}/revisions/{revision_id}`
- `POST /api/admin/problems/{problem_id}/revisions/{revision_id}/validate`
- `POST /api/admin/problems/{problem_id}/revisions/{revision_id}/publish`
- `POST /api/admin/problems/{problem_id}/archive`
- `POST /api/admin/homeworks/{homework_num}/problems`

주요 대상:

- `backend/app/models/schemas.py`
- 신규 `backend/app/domains/problems/`
- 신규 `backend/app/services/problem_service.py`
- `backend/app/domains/homework/router.py`
- `backend/app/migrations/`
- `backend/app/api/router.py`

완료 기준:

- Admin이 빈 초안을 만들고 여러 번 저장해도 학생에게 노출되지 않습니다.
- 검증에 실패한 revision은 게시할 수 없습니다.
- 게시 후 지문 또는 테스트 데이터를 바꾸면 기존 revision이 보존됩니다.
- 기존 homework API와 제출 조회가 migration 전과 같은 결과를 반환합니다.

## Phase 2. 문제 패키지·테스트 데이터 관리 API 완성

목표는 서버 디렉터리 편집 없이 브라우저에서 문제에 필요한 모든 자산을 관리하는 것입니다.

작업:

1. 현재 분리된 `problem_file`, `input_zip`, `output_zip` 형식을 유지하되, 단일 문제 패키지 ZIP도 받을 수 있도록 manifest 규격을 정의합니다.
2. 개별 테스트케이스 추가·교체·삭제·순서 변경 API와 ZIP 일괄 업로드 API를 함께 제공합니다.
3. `TestCaseGroup`과 테스트케이스 메타데이터를 정규화하고, 현재 `GradingRule.rule_value` JSON은 migration 후 읽기 호환만 유지합니다 (`backend/app/services/grading_service.py:324`).
4. 업로드 직후 비동기 검증 작업을 생성하여 중복 파일, 빈 파일, pair 불일치, 총 크기, checksum, 점수 합계, 샘플 공개 여부를 검사합니다.
5. Phase 2에서는 reference solution의 파일 존재, 허용 확장자, 크기, checksum 같은 정적 검증만 수행합니다. 컴파일·실행 기반 “시험 채점”은 Phase 3 sandbox 보안 게이트 통과 후에만 활성화합니다.
6. 업로드 자산 다운로드는 권한 검사와 감사 기록을 거쳐 인증된 streaming response로 제공합니다.
7. checker/generator 소스는 일반 실행기와 분리된 제한된 sandbox에서만 실행합니다.
8. 기존 `supportFiles/homeworks/{num}` 파일, `GradingRule`의 artifact metadata JSON, `Submission.storage_path`, `SubmissionFile.storage_path`를 hash 기반 store로 이관하는 idempotent backfill을 작성합니다.
9. backfill은 원본을 즉시 삭제하지 않고 copy → SHA-256 및 크기 대조 → DB 참조 전환 → 전체 reconciliation 성공 후 원본 보류 상태로 전환합니다. 실패 시 snapshot restore 없이도 기존 경로 참조로 되돌릴 수 있어야 합니다.

제안 API:

- `POST /api/admin/problems/{id}/revisions/{rev}/package`
- `GET /api/admin/problems/{id}/revisions/{rev}/assets`
- `POST/PATCH/DELETE /api/admin/problems/{id}/revisions/{rev}/testcases`
- `POST /api/admin/problems/{id}/revisions/{rev}/testcases/import`
- `POST /api/admin/problems/{id}/revisions/{rev}/dry-runs` — Phase 3 `sandbox_ready` 이후 활성화하며 그 전에는 명시적 비활성 오류 반환
- `GET /api/admin/problem-jobs/{job_id}`
- `GET /api/admin/problem-jobs/{job_id}/events`

완료 기준:

- 파일 시스템이나 DB에 직접 접근하지 않고 문제 패키지를 생성·검증·수정할 수 있습니다.
- 업로드 실패 시 부분 파일과 부분 DB row가 남지 않습니다.
- 손상 ZIP, zip bomb, 경로 순회, symlink, 중복 이름, 제한 초과가 거부됩니다.
- hidden testcase의 입력·정답은 학생 API 및 일반 로그에 노출되지 않습니다.
- Phase 3 전에는 어떤 업로드 코드도 실행되지 않으며 `dry-runs`가 명시적으로 차단됩니다.
- 기존 homework와 submission artifact의 backfill 전후 파일 수, 총 크기, SHA-256, 참조 수가 일치합니다.

## Phase 3. 채점 정책과 온라인 저지 판정 확장

목표는 현재 교육용 단순 비교를 표준 온라인 저지의 판정 모델로 확장하는 것입니다.

작업:

1. 가장 먼저 Linux namespace/cgroup/seccomp 기반 격리 실행기 계약을 확정하고, network 차단, read-only root, 임시 workspace, 비특권 UID, process/file/output 제한을 강제합니다. 이 게이트를 통과하기 전에는 공개 운영 자동 채점을 허용하지 않습니다.
2. 판정 코드를 `AC`, `WA`, `TLE`, `MLE`, `OLE`, `RE`, `CE`, `PE`, `IE`, `JG` 등 명시적 enum으로 정의합니다.
3. 문제별 CPU time, wall time, memory, output, source size, process 수 제한을 저장하고 worker가 강제하도록 합니다.
4. standard token/line checker, floating-point checker, unordered checker를 기본 제공하고 special judge는 별도 실행 계약으로 제공합니다.
5. 테스트 그룹별 점수, all-or-nothing, dependency, subtask 점수 계산을 지원합니다.
6. 언어별 time/memory multiplier와 문제별 허용 언어를 revision에 고정합니다.
7. interactive 문제는 별도 프로토콜과 sandbox 검증이 끝날 때까지 기능 플래그 뒤에 둡니다.
8. 결과에는 적용된 problem revision, runner image/runtime version, checker version을 기록합니다.
9. `sandbox_ready` 운영 상태는 hostile fixture 전체 통과 후에만 활성화하고, 활성화 이후 reference solution 시험 채점과 Admin `dry-runs` API를 개방합니다.

주요 대상:

- `backend/app/services/grading_service.py`
- `backend/app/services/code_runner.py`
- `backend/app/models/schemas.py`
- 신규 `backend/app/services/checkers/`
- 신규 `backend/app/services/sandbox/`

완료 기준:

- 동일 revision과 runtime version으로 동일 제출을 재채점하면 같은 판정과 점수를 얻습니다.
- 시간·메모리·출력 제한 초과가 서로 다른 판정으로 기록됩니다.
- checker가 실패하면 사용자 제출의 `WA`가 아니라 운영 오류 `IE`로 분리됩니다.
- 테스트 그룹 및 부분 점수 합산이 단위 테스트와 golden fixture에서 일치합니다.
- sandbox escape, network 접근, fork bomb, 파일 시스템 탐색, 과다 출력 hostile fixture가 호스트와 다른 제출에 영향을 주지 않습니다.
- `sandbox_ready`가 false이면 학생 자동 채점, reference solution 시험 채점, Admin dry-run이 모두 코드를 실행하지 않고 차단됩니다.

## Phase 4. 영속 작업 큐와 일괄 재채점 도입

목표는 Admin의 수동 `process-next` 호출과 프로세스 내부 큐를 제거하고, 재시작과 다중 worker에 안전한 작업 처리를 제공하는 것입니다.

작업:

1. 신규 의존성을 추가하지 않고 과목별 SQLite에 `JudgeJob` 테이블과 단일 queue coordinator를 구현합니다. coordinator가 작업을 원자적으로 claim하고, 실제 sandbox 실행은 제한된 worker process pool에 위임합니다.
2. job 상태를 `queued`, `leased`, `running`, `succeeded`, `failed`, `cancelled`, `dead_letter`로 관리합니다.
3. `lease_owner`, `lease_expires_at`, `heartbeat_at`, `attempt_count`, `max_attempts`, `priority`, `progress`를 저장합니다.
4. API 프로세스와 worker 프로세스를 분리하고, 기존 `GradingQueueService._queue`를 제거합니다.
5. 문제 revision 게시 시 기존 제출에 영향을 주지 않으며, 관리자가 명시적으로 재채점 작업을 생성하도록 합니다.
6. 재채점 scope를 문제, revision, homework/contest, 사용자, 제출 ID, 기존 판정, 제출 시간으로 필터링합니다.
7. 대량 작업은 parent batch와 child job으로 나누고 dry-run 대상 건수 확인, 취소, 실패 건 재시도를 제공합니다.
8. 동일 요청의 중복 실행을 막기 위해 idempotency key와 대상 revision을 기록합니다.
9. claim은 `BEGIN IMMEDIATE` 안에서 조건부 `UPDATE ... WHERE status='queued'`를 수행하고 변경 row 수를 확인하는 계약으로 정의합니다. SQLite 연결에는 WAL, `busy_timeout`, 짧은 write transaction 정책을 적용합니다.
10. worker는 heartbeat를 갱신하고 lease가 만료된 `leased/running` 작업만 coordinator가 재회수합니다. attempt 제한을 넘으면 `dead_letter`로 이동합니다.
11. 학생의 `POST /submissions`는 요청 안에서 `grading_service.grade_submission`을 실행하지 않고 submission과 job을 같은 DB transaction에 기록한 뒤 즉시 반환하는 enqueue-only 흐름으로 전환합니다.
12. checkpoint는 queue가 idle이거나 학기 종료 쓰기 동결 후 수행하며, WAL 파일만 누락된 DB 복사본을 만들지 않습니다.

제안 API:

- `POST /api/admin/rejudge-jobs/preview`
- `POST /api/admin/rejudge-jobs`
- `GET /api/admin/rejudge-jobs`
- `GET /api/admin/rejudge-jobs/{job_id}`
- `POST /api/admin/rejudge-jobs/{job_id}/cancel`
- `POST /api/admin/rejudge-jobs/{job_id}/retry-failed`
- `GET /api/admin/judge-jobs?status=&problem_id=&worker_id=`

완료 기준:

- API 또는 worker 재시작 후에도 queued/running 작업이 유실되지 않습니다.
- 동일 제출을 두 worker가 동시에 채점하지 않습니다.
- 1,000건 이상의 재채점 요청이 HTTP timeout 없이 생성되고 진행률을 조회할 수 있습니다.
- 취소 후 아직 시작하지 않은 child job은 실행되지 않습니다.
- 재채점 전후 판정·점수와 사용한 revision이 감사 가능하게 보존됩니다.
- API 요청 중 호스트에서 학습자 코드가 실행되지 않고, submission row와 judge job이 함께 생성되거나 함께 rollback됩니다.
- 두 coordinator를 실수로 실행한 hostile test에서도 조건부 claim으로 중복 실행이 발생하지 않습니다.

## Phase 5. Admin 권한·계정 부트스트랩·감사 강화

목표는 모든 staff가 동일한 권한을 갖는 현재 구조를 업무별 최소 권한으로 바꾸고, CLI 의존 관리자 생성을 최초 부트스트랩으로 제한하는 것입니다.

작업:

1. 역할 문자열 확인을 capability 기반 정책으로 교체합니다. 예: `problem:create`, `problem:review`, `problem:publish`, `problem:data.read`, `submission:rejudge`, `judge:operate`, `user:manage`, `settings:manage`.
2. 기본 역할을 `super_admin`, `admin`, `problem_setter`, `reviewer`, `judge_operator`, `support`, `viewer`로 제공하되 capability 조합은 DB에서 관리합니다.
3. 문제별 소유자/공동 출제자 범위를 지원해 출제자가 모든 문제 데이터를 볼 수 없도록 합니다.
4. 최초 사용자 0명일 때만 사용할 수 있는 만료형 bootstrap token 흐름을 추가합니다. 이후 관리자는 웹 초대와 역할 부여로 생성합니다.
5. 권한 상승, 문제 데이터 다운로드, 게시, 재채점, 설정 변경은 변경 전후값과 request ID, job ID를 감사 로그에 남깁니다.
6. 감사 로그 API에 actor, action, target, 기간, 성공 여부, request/job ID 필터와 cursor pagination을 추가합니다.
7. 관리자 로그인에는 추후 TOTP/WebAuthn을 붙일 수 있도록 MFA 상태와 step-up 인증 경계를 설계합니다.

주요 대상:

- `backend/app/api/dependencies.py`
- `backend/app/services/user_management.py`
- `backend/app/cli.py`
- `backend/app/domains/users/router.py`
- `backend/app/services/observability_service.py`
- `backend/app/domains/observability/router.py`
- 신규 `backend/app/domains/admin_auth/`

완료 기준:

- 문제 출제자는 자기 문제 초안을 편집하지만 게시·사용자 관리·시스템 설정을 수행하지 못합니다.
- 검수자 승인 없이 출제자가 자기 revision을 게시할 수 없도록 선택 가능한 2인 승인 정책을 제공합니다.
- 사용자 존재 이후 bootstrap API와 token은 동작하지 않습니다.
- 모든 P0/P1 관리자 변경 작업이 감사 로그 테스트에 포함됩니다.

## Phase 6. 로컬 채점 worker·운영 설정·관측성 API

목표는 운영자가 SSH 없이 채점 시스템의 상태를 진단하고 안전한 조치를 수행하는 것입니다.

작업:

1. 단일 베어 메탈 서버의 queue coordinator와 worker pool heartbeat를 구현하고 online, draining, offline, disabled 상태를 관리합니다. 원격 `JudgeNode` registry는 실제 다중 서버 요구가 생길 때까지 보류합니다.
2. 로컬 worker별 지원 언어·버전, 동시 작업 수, 최근 heartbeat, 최근 오류, 현재 job을 조회합니다.
3. Admin이 로컬 worker pool을 drain/enable/disable할 수 있게 하되 임의 shell command 실행 기능은 제공하지 않습니다.
4. 큐 길이, 대기 시간, 판정별 비율, 문제별 오류율, worker 실패율을 집계합니다.
5. 현재 lint 전용 시스템 설정을 제출 제한·지원 언어·기본 자원 상한·보존 정책 등으로 확장합니다.
6. 비밀과 재시작이 필요한 인프라 설정은 API에서 읽거나 쓰지 않습니다. UI에는 “배포 설정에서 관리” 상태만 제공합니다.
7. readiness/liveness와 worker health를 분리하고, request/job correlation ID를 모든 이벤트에 연결합니다.

제안 API:

- `GET /api/admin/judge-workers`
- `POST /api/admin/judge-workers/drain`
- `POST /api/admin/judge-workers/enable`
- `GET /api/admin/grading/metrics`
- `GET /api/admin/grading/incidents`

완료 기준:

- heartbeat가 임계 시간을 넘긴 worker는 자동으로 새 job 할당 대상에서 제외됩니다.
- draining worker pool은 현재 작업을 끝내되 새 작업을 받지 않습니다.
- 운영자가 API로 queue backlog와 실패 원인을 문제/worker/runtime 기준으로 찾을 수 있습니다.
- 모든 위험 설정은 범위 검증, 변경 감사, 롤백 가능한 이전값을 가집니다.

## Phase 7. 대회 운영 백엔드 기반

프론트엔드 계획 전 반드시 구현할 P0는 아니지만, BOJ/DMOJ형 서비스 목표를 위해 문제 도메인 확정 시 스키마 확장 가능성을 확보해야 합니다.

작업:

1. `Contest`, `ContestProblem`, `ContestParticipation`, `Clarification`, `ContestAnnouncement` 경계를 설계합니다.
2. 시작/종료, freeze, 공개 범위, 접근 코드/조직, virtual participation, 채점 방식(ICPC/IOI)을 정책으로 분리합니다.
3. 대회 중 문제 revision 고정, 수정 공지, 재채점 금지/승인 정책을 추가합니다.
4. scoreboard 계산을 제출 row 직접 조회가 아닌 revisioned result event로 재현할 수 있게 합니다.

완료 기준:

- 대회 시작 후 연결된 problem revision이 자동 변경되지 않습니다.
- 문제 수정과 재채점에는 공지/사유/승인 기록이 남습니다.
- scoreboard freeze와 system testing 전후 결과를 재현할 수 있습니다.

## 5. 우선순위와 권장 릴리스 순서

### Release A: 웹 문제 운영 MVP

Phase 0 → Phase 1 → Phase 2를 완료합니다.

사용자에게 보이는 결과:

- 웹에서 문제 초안, 파일, 테스트케이스를 만들고 검증 후 게시할 수 있습니다.
- 서버 디렉터리 편집과 seed 수정이 필요하지 않습니다.
- 게시된 문제를 실수로 덮어쓰지 않고 revision으로 관리합니다.
- 단, 공개 운영에서 학생 코드를 자동 채점하려면 Phase 3의 sandbox 보안 게이트를 먼저 완료해야 합니다. Release A만 완료된 상태에서는 문제 작성·검증 Admin 기능까지만 공개합니다.

### Release B: 신뢰 가능한 채점 운영

Phase 3 → Phase 4를 완료합니다.

사용자에게 보이는 결과:

- 표준 온라인 저지 판정과 자원 제한을 제공합니다.
- Admin이 웹에서 일괄 재채점을 생성하고 진행률·오류·취소를 관리합니다.
- 운영자가 `process-next`를 반복 호출하지 않아도 worker가 자동 채점합니다.

### Release C: 운영 권한과 관측성

Phase 5 → Phase 6을 완료합니다.

사용자에게 보이는 결과:

- 출제자·검수자·채점 운영자 권한이 분리됩니다.
- SSH 없이 로컬 채점 worker와 큐 상태를 확인하고 안전한 운영 조치를 수행합니다.

### Release D: 대회 기능

Phase 7을 별도 PRD와 테스트 명세로 구체화한 뒤 진행합니다.

## 6. 구현하지 않을 것과 보류 사항

- Admin 웹에서 shell command를 직접 실행하는 “웹 터미널”은 만들지 않습니다. 권한 상승과 명령 주입 위험이 크고, 반복 가능한 도메인 API로 해결해야 합니다.
- `JWT_SECRET`, 분석용 HMAC secret, OAuth secret을 DB 설정 화면으로 옮기지 않습니다.
- 기존 `Homework` 테이블과 API를 한 번에 삭제하거나 이름만 `Problem`으로 바꾸지 않습니다.
- 초기 단계에서 DMOJ의 모든 기능(60개 이상 언어, interactive/signature grading, rating, MOSS)을 복제하지 않습니다.
- 새 큐 패키지는 즉시 도입하지 않습니다. 먼저 현재 의존성 안에서 DB 큐 계약을 완성하고 부하 측정 후 Redis/RabbitMQ/Celery 계열 도입 여부를 별도 결정합니다.
- 과목별 SQLite를 운영 기준으로 유지합니다. 한 과목 서버에서는 단일 queue coordinator만 DB 작업을 claim하고, 병렬 채점은 coordinator가 관리하는 worker process pool로 수행해 다중 writer 경합을 제한합니다.
- 과목 DB들을 하나의 운영 SQLite로 직접 병합하지 않습니다. 각 course bundle을 원본으로 보존하고, 별도 오프라인 분석 환경은 schema-versioned Parquet와 DuckDB를 사용할 수 있습니다.

## 7. 위험과 완화책

| 위험 | 영향 | 완화책 |
| --- | --- | --- |
| 기존 `Homework` 데이터 migration 실패 | 과제/제출 연결 손상 | idempotent backfill, dry-run 보고서, row count/checksum, migration 직전 snapshot restore |
| SQLite와 artifact store 불일치 | 게시 불가 또는 hidden data 유실 | staging 업로드, SHA-256, 원자적 승격, 참조 정합성 검사와 복구 보고서 |
| course bundle이 불완전하게 취합됨 | 학기 분석 누락 또는 재현 불가 | SQLite Backup API, manifest, 전체 checksum, bundle validation gate |
| 과목·학기별 schema 차이 | 오프라인 통합 분석 결과 왜곡 | DB/artifact/export schema version 기록, version별 migration 후 Parquet 생성 |
| 분석 데이터에서 학습자 재식별 | 개인정보 노출 | 운영 ID와 학교 전체 고정 가명 ID 분리, 학교 분석용 HMAC secret 별도 관리, 최소 필드 export |
| 학기 중 운영 디스크 장애 | 해당 학기 데이터 전체 손실 가능 | 무결성·SMART·용량 관측, 동일 디스크 SQLite 순환 snapshot, 학기 종료 즉시 외장 디스크 이전; 별도 물리 백업 부재는 수용된 잔여 위험 |
| 외장 디스크 이전 실패 또는 손상 | 학기 종료 보관본 유실 | 복사 전후 전체 SHA-256 검증, SQLite open/row count 검사, 검증 성공 전 운영 서버 원본 삭제 금지 |
| 재채점 폭주 | 정상 제출 채점 지연 | priority queue, batch rate limit, preview, pause/cancel, worker capacity 기반 할당 |
| custom checker가 sandbox 탈출 | 서버 침해 | 일반 API 프로세스에서 실행 금지, seccomp/cgroup/namespace, read-only image, network 차단 |
| 권한 모델 전환 중 과도한 권한 | 문제 데이터 유출/오작동 | deny-by-default capability, role matrix 테스트, audit, 단계적 feature flag |
| 게시 revision 변경으로 결과 불일치 | 신뢰도 하락 | immutable revision, result에 revision/runtime/checker version 기록 |
| 관리자 실수로 대량 변경 | 광범위한 결과 변경 | preview, 영향 건수 표시, 사유 필수, idempotency key, 2인 승인 옵션 |
| API 호환성 파괴 | 기존 프론트엔드 장애 | 기존 endpoint adapter, deprecation header, OpenAPI diff CI, 단계별 제거 |
| 호스트 subprocess에서 학습자 코드 실행 | 서버 권한 탈취·데이터 유출·서비스 중단 | production 자동 채점 비활성화, Phase 3 sandbox 선행 게이트, hostile security fixture |
| SQLite write 경합 | 제출/작업 생성 실패 또는 장기 lock | WAL, busy timeout, 단일 coordinator, 짧은 write transaction, 조건부 claim, capacity test |

## 8. 검증 전략

### 단위 테스트

- 문제 상태 전이와 게시 불변성
- capability 권한 매트릭스
- manifest/ZIP/경로/checksum/점수 합계 검증
- checker별 출력 비교와 판정 매핑
- 테스트 그룹 및 부분 점수 계산
- job lease, retry, timeout, cancellation, idempotency

### 통합 테스트

- 문제 초안 → 자산 업로드 → validate → dry-run → publish 전체 흐름
- 기존 homework → problem revision backfill → 기존 제출 조회/채점 호환
- 문제 revision 변경 → 선택 범위 재채점 → 결과/감사 이력 확인
- API/worker 동시 실행과 worker 강제 종료 후 lease 회수
- staging 승격 실패와 SQLite rollback 간 정합성
- SQLite row ↔ artifact 파일의 missing/checksum mismatch/orphan 검출
- course bundle snapshot 생성 중 제출이 발생해도 일관된 DB와 manifest가 생성되는지 검증
- 서로 다른 schema version의 과목 bundle을 검증·migration·Parquet export하는 통합 테스트

### E2E/API 계약 테스트

- `problem_setter`, `reviewer`, `judge_operator`, `admin`별 허용·거부 시나리오
- 1,000건 이상 재채점 batch의 생성, 진행률, 취소, 실패 재시도
- hidden testcase와 관리자 전용 자산이 일반 사용자 응답에 없는지 검사
- OpenAPI snapshot과 기존 Admin endpoint 호환 검사

### 성능·운영 검증

- 문제 패키지 최대 허용 크기 업로드 시 메모리 사용량 측정
- 동시 worker에서 중복 claim이 0건인지 확인
- queue p95 대기 시간, 채점 p95 처리 시간, worker heartbeat 누락 탐지 시간 측정
- 감사 로그와 job event 보존량에 대한 pagination/index query plan 확인
- 대규모 제출 파일에서 content-addressed 중복 제거율과 reconciliation 수행 시간을 측정
- 학기 전체 bundle 생성·검증·Parquet export에 필요한 시간과 추가 디스크 용량을 측정
- 학기 종료 외장 디스크의 bundle에서 SQLite와 artifact를 실제 복구하는 훈련 수행

### 필수 품질 게이트

각 Phase PR은 다음을 통과해야 합니다.

```bash
cd backend
uv run pytest
uv run python -m compileall app
```

현재 `backend/pyproject.toml`에는 `ruff`와 `mypy`가 없으므로 이를 필수 명령으로 가장하지 않습니다. 추후 명시적으로 개발 의존성을 도입한 뒤에는 `uv run ruff check .`와 `uv run mypy app`을 품질 게이트에 추가합니다. 운영 백엔드에는 새 의존성을 추가하지 않으며, Parquet/DuckDB는 별도 `analytics/` uv 프로젝트의 승인된 오프라인 도구로만 관리합니다.

## 9. 백엔드 확정 시 프론트엔드에 제공할 계약

백엔드 계획이 승인되고 Release A의 API 스키마가 확정되면 프론트엔드 계획은 다음 계약을 기준으로 작성합니다.

- 문제 editor가 필요한 field schema, enum, validation error
- revision 상태와 가능한 다음 action
- multipart upload 방식, 서버 측 staging 처리와 업로드 진행률 계약
- 비동기 job 상태, progress, event, retry/cancel action
- capability 목록과 메뉴/action 노출 규칙
- cursor pagination, 검색, 정렬, 필터 규격
- 위험 작업의 preview/confirm/idempotency 규격
- 감사 로그와 worker/queue observability 응답 규격

프론트엔드 계획 착수 조건은 Phase 1·2의 OpenAPI 초안, 권한 matrix, 오류 응답 규격이 리뷰를 통과하는 것입니다.

## 10. 최종 권고

가장 먼저 할 일은 기존 Admin 화면을 늘리는 것이 아니라 `Homework`에 뒤섞인 문제 정의와 배치 일정을 분리하고, 불변 `ProblemRevision`을 중심으로 문제 운영 수명주기를 만드는 것입니다. 그 위에 문제 패키지 검증과 영속 job을 얹어야 웹 Admin이 터미널 작업을 실제로 대체할 수 있습니다.

권장 첫 구현 묶음은 Phase 0과 Phase 1입니다. 이 단계에서 모델과 API 계약을 확정한 뒤 Phase 2의 업로드/검증 작업을 연결하고, Release A가 안정화된 시점에 프론트엔드 Admin 계획을 수립하는 순서가 가장 작은 위험으로 사용자 불만을 해결합니다.
