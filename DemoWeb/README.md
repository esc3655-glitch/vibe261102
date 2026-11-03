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

외부 DB 없이 바로 실행할 수 있도록 **로컬 JSON 파일**(`data/posts.json`)에 저장합니다.

- 읽기/쓰기 로직은 `src/lib/posts.ts` 한 곳에 모여 있습니다(`server-only`).
- 작성·수정·삭제는 **Server Actions**(`src/app/actions.ts`)로 처리하고, 끝나면 `revalidatePath`로 화면을 갱신합니다.
- 쓰기 요청은 프로세스 안에서 순서대로 처리하고, 임시 파일에 쓴 뒤 이름을 바꿔(atomic rename) 파일이 깨지지 않게 합니다.
- 파일이 없으면 첫 요청 때 샘플 글 3개로 만들어집니다. `data/`는 `.gitignore`에 들어 있습니다.

한 대의 서버에서 돌리는 데모용 방식입니다. 여러 인스턴스나 서버리스 환경에 배포하려면 `src/lib/posts.ts`만 SQLite·Postgres 등으로 바꾸면 됩니다.

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
    posts.ts                 JSON 파일 저장소
    format.ts                날짜 형식
```

## 사용한 shadcn/ui 컴포넌트

Button, Card, Input, Textarea, Label, Table, AlertDialog, Dialog, Pagination, DropdownMenu, Badge, Separator, Sonner
