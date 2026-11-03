# DemoWeb 게시판

Next.js(App Router) + TypeScript + shadcn/ui로 만든 간단한 웹 게시판입니다.

## 기능

- 게시글 목록: 최신순 정렬, 페이지당 10개 페이지네이션, 제목·내용·작성자 검색(`?q=`)
- 게시글 상세 보기, 작성, 수정, 삭제(확인 다이얼로그)
- 서버 측 입력 검증(제목 100자, 작성자 30자, 내용 5000자 이하)
- 작업 결과 알림(토스트), 404 페이지
- 반응형: 태블릿 이상은 표, 모바일은 카드 목록
- 다크 모드: 헤더의 테마 버튼으로 라이트 / 다크 / 시스템 선택(`next-themes`)

## 실행

```bash
npm install
npm run dev -- --port 5175
```

브라우저에서 http://localhost:5175 를 엽니다. 저장소 루트의 `.claude/launch.json`에도 `demoweb`(포트 5175) 항목이 있습니다.

프로덕션 빌드:

```bash
npm run build
npm start
```

## 데이터 저장 방식

**Neon**(서버리스 PostgreSQL)에 저장하며, `@neondatabase/serverless` 드라이버(HTTP)로 접속합니다.

1. `.env.example`을 `.env.local`로 복사하고 `DATABASE_URL`에 Neon 연결 문자열을 넣습니다. `.env.local`은 git에 올라가지 않습니다.
2. 처음 요청이 들어오면 `posts` 테이블이 없을 때 만들고, 비어 있으면 샘플 글 3개를 넣습니다.

- 읽기/쓰기 로직은 `src/lib/posts.ts` 한 곳에 모여 있습니다(`server-only`).
- 작성·수정·삭제는 **Server Actions**(`src/app/actions.ts`)로 처리하고, 끝나면 `revalidatePath`로 화면을 갱신합니다.
- 검색은 제목·내용·작성자에 대한 `ILIKE`, 페이지네이션은 `LIMIT/OFFSET`으로 DB에서 처리합니다.

테이블 구조:

| 컬럼 | 타입 |
|---|---|
| `id` | `uuid` PK (기본값 `gen_random_uuid()`) |
| `title`, `content`, `author` | `text` |
| `created_at`, `updated_at` | `timestamptz` |

예전 JSON 파일(`data/posts.json`)의 글을 옮기려면 `npm run db:import`를 실행합니다. 같은 id는 건너뜁니다.

## 구조

```
src/
  app/
    page.tsx                 목록 + 검색 + 페이지네이션
    posts/new/page.tsx       글쓰기
    posts/[id]/page.tsx      상세 보기 + 삭제
    posts/[id]/edit/page.tsx 수정
    actions.ts               Server Actions(작성/수정/삭제, 검증)
    not-found.tsx
  components/
    post-form.tsx            작성/수정 공용 폼
    delete-post-button.tsx   삭제 확인 AlertDialog
    theme-toggle.tsx         테마 전환
    toast-from-query.tsx     ?toast= 값을 알림으로 표시
    ui/                      shadcn/ui 컴포넌트
  lib/
    posts.ts                 Neon(PostgreSQL) 저장소
    format.ts                날짜 형식
```

## 사용한 shadcn/ui 컴포넌트

Button, Card, Input, Textarea, Label, Table, AlertDialog, Dialog, Pagination, DropdownMenu, Badge, Separator, Sonner
