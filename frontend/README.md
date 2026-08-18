# neoESPA 프론트엔드 (Next.js)

> neoESPA 학습 관리 시스템의 웹 클라이언트입니다. 수강생 화면과 운영진용 관리자 콘솔을 함께 제공합니다.
> 백엔드 API 명세는 [../backend/API.md](../backend/API.md)를 참고하시기 바랍니다.

## 주요 기술 스택

- [Next.js 16](https://nextjs.org/) App Router (`output: "standalone"`, Turbopack)
- React 19 / TypeScript (모든 화면이 클라이언트 컴포넌트)
- [Tailwind CSS v4](https://tailwindcss.com/) — 디자인 토큰은 `src/app/globals.css`에 정의
- [Monaco Editor](https://github.com/suren-atoyan/monaco-react) (코드 편집), [lucide-react](https://lucide.dev/) (아이콘), [next-themes](https://github.com/pacocoursey/next-themes) (다크 모드)
- 테스트: [Playwright](https://playwright.dev/) (E2E)

## 실행

저장소 루트에서 Docker로 백엔드와 함께 띄우는 방법을 권장합니다.

```bash
cd ..
docker compose up --build -d      # 프론트엔드 http://localhost:3000, 백엔드 http://localhost:8000
```

호스트에서 직접 실행하려면 다음과 같이 합니다. (백엔드가 8000 포트에서 실행 중이어야 합니다)

```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

### 환경 변수

| 변수 | 용도 |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | 브라우저에서 호출할 백엔드 주소. 비우면 같은 오리진으로 요청하고 `next.config.ts`의 rewrite가 처리합니다. |
| `BACKEND_URL` | 서버 사이드 rewrite 대상 백엔드 주소 (기본 `http://localhost:8000`). 프로덕션 이미지는 빌드 시점에 굽습니다. |

## 스크립트

| 명령 | 용도 |
|---|---|
| `npm run dev` | 개발 서버 |
| `npm run build` / `npm start` | 프로덕션 빌드 및 실행 |
| `npm run typecheck` | `tsc --noEmit` 타입 검사 |
| `npm run lint` | ESLint 검사 |
| `npm run test:e2e` | Playwright E2E (아래 참고) |

### 검사 실행

컨테이너에서 실행할 때는 dev 의존성이 필요하므로 `NODE_ENV=development`로 설치합니다.
(프로덕션 이미지는 `NODE_ENV=production`이라 그냥 `npm ci`를 하면 dev 의존성이 빠집니다.)

```bash
# 저장소 루트에서
docker compose run --rm --no-deps -e NODE_ENV=development frontend \
  sh -lc "npm ci --include=dev && npm run typecheck && npm run lint"
```

> **알려진 제약**: 소스가 바인드 마운트된 개발 컨테이너에서 `npm run build`를 돌리면
> `/_global-error` 프리렌더 단계에서 실패합니다. 이 프로젝트의 기존 동작이며 소스 문제가 아닙니다.
> 빌드 검증은 `docker compose build frontend`(깨끗한 이미지 빌드)로 하십시오. 이 경로가 실제 배포 경로입니다.

### E2E 테스트

Playwright가 **백엔드(127.0.0.1:8101)와 프론트엔드(127.0.0.1:3101)를 스스로 띄웁니다.** 별도로
서버를 실행할 필요가 없습니다. 시작 시 `database/e2e.sqlite`를 지우고 샘플 데이터를 다시
시딩하므로(`scripts/reset-e2e-db.sh`) 개발용 DB는 건드리지 않습니다.

```bash
npm run test:e2e            # 헤드리스
npm run test:e2e:headed     # 브라우저 표시
```

백엔드를 호스트에서 직접 구동하므로 Python 3.14와 uv가 설치돼 있어야 합니다.

## 화면 구성

### 수강생 화면

| 경로 | 설명 |
|---|---|
| `/` | 홈 · 최근 활동 |
| `/login`, `/register` | 로그인, 회원가입 |
| `/dashboard` | 과제 진행 현황, 최근 제출 요약 |
| `/homework`, `/homework/[num]` | 과제 목록 및 상세·제출 |
| `/submit`, `/submit/result` | 코드 제출 화면과 제출 직후 결과 |
| `/homework/result` | 채점 결과, 피드백, 운영진 점수 조정 내역 |
| `/exam`, `/exam/[id]`, `/exam/[id]/result` | 시험 응시 및 결과 |
| `/contest` | 대회 목록·참가 · 스코어보드 · 대회 공지 · 질문(Clarification) |
| `/materials`, `/notice`, `/notice/[num]`, `/qa` | 강의자료, 공지사항, Q&A |
| `/collab` | 실시간 협업 세션 (WebSocket) |
| `/notifications` | 알림함 |
| `/profile` | 프로필·비밀번호 변경, 학습 분석 데이터 활용 동의 |
| `/admin-invite` | 초대 토큰으로 운영진 계정 생성, 최초 관리자 부트스트랩 (로그인 전 접근) |

### 관리자 콘솔 (`/admin`)

탭 노출은 백엔드 권한(`backend/app/services/authorization_service.py`)과 맞춰 제한합니다.
표의 "열람 가능 역할"은 `src/app/admin/page.tsx`의 `ADMIN_ONLY_TABS`·`INSTRUCTOR_TABS`로 구현돼 있습니다.

| 탭 | 내용 | 열람 가능 역할 |
|---|---|---|
| 현황 종합 | 통계, 채점 큐, 최근 이벤트 | admin · instructor · ta |
| 과제 관리 | 과제 CRUD, 성적 CSV·제출물 ZIP 내보내기, ZIP 기반 과제 가져오기, 문제 연결 | admin · instructor · ta |
| 채점 운영 | 채점 지표·워커 제어·작업/인시던트, 재채점·점수 조정, 아티팩트 정합성 점검 | admin · instructor |
| 일괄 재채점 | 범위 지정 → 미리보기 → 재채점 작업 등록·취소·재시도 | admin · instructor · ta |
| 문제 뱅크 | 문제·리비전·테스트케이스·자산, 검증→검수→게시, 드라이런, 공동 작업자 | admin · instructor · ta |
| 대회 운영 | 대회 생성·게시·문제 연결·공지·질문 답변·운영 승인·시스템 테스트 | admin · instructor |
| 시험 관리 | 시험 등록 및 응시 일정 확인 | admin · instructor |
| 공지사항 / 강의자료 관리 | 공지·자료실 관리 | admin · instructor · ta |
| 사용자 관리 | 계정 조회·역할·상태·비밀번호 초기화·일괄 등록 | admin |
| 역할 권한 | 역할별 수행 권한(capability) 지정 (재인증 필요) | admin |
| 운영진 초대 | 일회성 초대 토큰 발급 (재인증 필요) | admin |
| 시스템 설정 | 린트·채점 관련 전역 설정 및 롤백 | admin |
| 표절 검사 | 유사도 검사 실행·비교·실행 이력 | admin · instructor · ta |
| 운영 로그 | 감사 로그(변경 전/후), 시스템 이벤트 | admin (감사 로그) · instructor · ta (시스템 이벤트) |

## 디자인 규약

`src/app/globals.css`에 정의된 토큰과 유틸리티를 사용합니다. 새 화면도 아래 규약을 따릅니다.

- 색상은 CSS 변수(`--background`, `--card`, `--border`, `--accent` 등)로 정의하고 다크 모드는 `.dark` 클래스에서 재정의합니다.
- 카드는 `card-simple`, 버튼은 `btn-flat`(주요)·`btn-outline`(보조)를 사용합니다.
- 섹션 제목은 `text-xs font-bold uppercase tracking-widest text-slate-400`에 lucide 아이콘을 곁들입니다.
- 상태 색상: 성공 `emerald`, 경고 `amber`, 오류 `rose`, 강조 `text-accent`.
- 입력 요소는 `text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none`을 기본으로 합니다.

## 코드 구조

```text
frontend/
├── src/
│   ├── app/           # App Router 페이지
│   ├── components/    # 공용 컴포넌트
│   │   ├── admin/     # 관리자 콘솔 탭별 매니저 컴포넌트
│   │   └── homework/  # 과제 제출 패널
│   ├── i18n/          # 다국어 사전 (ko·en·ja·zh)와 Context
│   └── lib/
│       ├── api.ts     # 백엔드 API 클라이언트 (타입 + 요청 함수)
│       └── datetime.ts# 서버 시간(UTC) 파싱 헬퍼
├── e2e/               # Playwright 시나리오
├── scripts/           # E2E용 DB 초기화 스크립트
└── next.config.ts     # standalone 빌드 및 /api rewrite
```

### API 클라이언트 사용 규칙

- 모든 백엔드 호출은 `src/lib/api.ts`를 거칩니다. 화면에서 `fetch`를 직접 부르지 않습니다.
- 요청 함수는 `apiRequest<T>(path, { token, ... })` 위에 얇게 작성하고, 응답 타입을 함께 정의합니다.
- 인증이 필요한 파일 내려받기는 `apiDownload`를, 조회 결과가 없을 수 있는 엔드포인트는 `allowNotFound` 옵션을 사용합니다.
- 파일 업로드는 `FormData`를 그대로 `body`에 넘깁니다. (`apiRequest`가 `Content-Type`을 자동으로 비웁니다)
- 토큰은 `useAuth()`의 `token`을 넘깁니다. (`localStorage` 세션은 `AuthProvider`가 관리)

### 화면 작성 규칙

- 데이터 로딩은 `useCallback`으로 감싼 로더를 `useEffect`에서 호출합니다.
- **권한이 서로 다른 데이터를 함께 불러올 때는 `Promise.allSettled`를 사용합니다.** 한쪽이 403이어도
  볼 수 있는 만큼은 보여야 합니다. (예: 운영 로그 탭의 감사 로그 `audit:read` / 시스템 이벤트 `observability:read`)
- 상태 메시지는 `errorMessage`·`successMessage` 두 개로 관리하고, 성공은 emerald, 실패는 rose 배너로 표시합니다.
- 백엔드가 요구하는 작업 순서(예: 대회는 문제 연결 → 게시 → 승인 → 시스템 테스트)는 버튼 비활성화만으로
  감추지 말고 화면에 문장으로 적어 둡니다. 서버가 돌려준 오류 메시지는 그대로 노출합니다.
- 로그인 보호가 필요한 페이지는 `AuthGate`로 감싸고, 역할 제한이 있으면 `roles`를 넘깁니다.

### 재인증(step-up)

백엔드가 재인증을 요구하는 작업(초대 발급, 역할 권한 변경)은 403 응답의
`Recent step-up authentication is required` 메시지를 감지해 `StepUpDialog`를 띄우고,
`useAuth().stepUp(password)`로 세션 토큰을 교체한 뒤 같은 작업을 다시 실행합니다.

### 다국어(i18n)

내비게이션 등 사전 기반 문구는 `useTranslation()`의 `t`를 사용합니다. 키를 추가할 때는
`src/i18n/types.ts`와 `src/i18n/locales/{ko,en,ja,zh}.ts` **네 개 로케일을 모두** 갱신해야
타입 검사를 통과합니다. 관리자 콘솔 문구는 현재 한국어로 직접 작성합니다.
