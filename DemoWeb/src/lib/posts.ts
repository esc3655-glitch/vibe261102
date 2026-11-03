import "server-only";

import { neon } from "@neondatabase/serverless";

export type Post = {
  id: string;
  title: string;
  content: string;
  author: string;
  createdAt: string;
  updatedAt: string;
};

export type PostInput = Pick<Post, "title" | "content" | "author">;

type PostRow = {
  id: string;
  title: string;
  content: string;
  author: string;
  created_at: Date | string;
  updated_at: Date | string;
};

const SEED: PostInput[] = [
  {
    title: "DemoWeb 게시판에 오신 것을 환영합니다",
    author: "관리자",
    content:
      "Next.js App Router, TypeScript, shadcn/ui로 만든 데모 게시판입니다.\n\n글 목록, 검색, 페이지네이션, 상세 보기, 작성·수정·삭제를 모두 지원합니다.",
  },
  {
    title: "데이터는 어디에 저장되나요?",
    author: "관리자",
    content:
      "Neon(서버리스 PostgreSQL)의 posts 테이블에 저장합니다.\n테이블이 없으면 첫 요청 때 만들어지고 샘플 글로 채워집니다.",
  },
  {
    title: "다크 모드도 지원합니다",
    author: "디자이너",
    content: "오른쪽 위의 테마 버튼으로 라이트, 다크, 시스템 설정을 고를 수 있습니다.",
  },
];

function db() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL이 설정되지 않았습니다. .env.local을 확인해 주세요.");
  return neon(url);
}

// 테이블 생성과 샘플 데이터 입력은 프로세스마다 한 번만 실행한다.
let ready: Promise<void> | null = null;

function ensureSchema() {
  ready ??= (async () => {
    const sql = db();
    await sql`
      CREATE TABLE IF NOT EXISTS posts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        title text NOT NULL,
        content text NOT NULL,
        author text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      )`;
    await sql`CREATE INDEX IF NOT EXISTS posts_created_at_idx ON posts (created_at DESC)`;
    // 테이블이 비어 있을 때만 샘플 글을 넣는다(한 문장이라 동시 요청에도 중복되지 않는다).
    const now = Date.now();
    await sql`
      INSERT INTO posts (title, content, author, created_at, updated_at)
      SELECT s.title, s.content, s.author, s.at, s.at
      FROM jsonb_to_recordset(${JSON.stringify(
        SEED.map((p, i) => ({ ...p, at: new Date(now - (SEED.length - i) * 60_000).toISOString() })),
      )}::jsonb) AS s(title text, content text, author text, at timestamptz)
      WHERE NOT EXISTS (SELECT 1 FROM posts)`;
  })().catch((error) => {
    ready = null;
    throw error;
  });
  return ready;
}

async function query() {
  await ensureSchema();
  return db();
}

const iso = (v: Date | string) => new Date(v).toISOString();

function toPost(row: PostRow): Post {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    author: row.author,
    createdAt: iso(row.created_at),
    updatedAt: iso(row.updated_at),
  };
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const PAGE_SIZE = 10;

export async function listPosts({ query: q = "", page = 1 }: { query?: string; page?: number }) {
  const sql = await query();
  const term = q.trim();
  const pattern = term ? `%${term.replace(/[\\%_]/g, "\\$&")}%` : "%";

  const [{ count }] = (await sql`
    SELECT count(*)::int AS count FROM posts
    WHERE title ILIKE ${pattern} OR content ILIKE ${pattern} OR author ILIKE ${pattern}`) as { count: number }[];

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);
  const rows = (await sql`
    SELECT * FROM posts
    WHERE title ILIKE ${pattern} OR content ILIKE ${pattern} OR author ILIKE ${pattern}
    ORDER BY created_at DESC
    LIMIT ${PAGE_SIZE} OFFSET ${(current - 1) * PAGE_SIZE}`) as PostRow[];

  return { posts: rows.map(toPost), total: count, page: current, totalPages };
}

export async function getPost(id: string) {
  if (!UUID.test(id)) return null;
  const sql = await query();
  const rows = (await sql`SELECT * FROM posts WHERE id = ${id}`) as PostRow[];
  return rows[0] ? toPost(rows[0]) : null;
}

export async function createPost(input: PostInput) {
  const sql = await query();
  const rows = (await sql`
    INSERT INTO posts (title, content, author)
    VALUES (${input.title}, ${input.content}, ${input.author})
    RETURNING *`) as PostRow[];
  return toPost(rows[0]);
}

export async function updatePost(id: string, input: PostInput) {
  if (!UUID.test(id)) return null;
  const sql = await query();
  const rows = (await sql`
    UPDATE posts
    SET title = ${input.title}, content = ${input.content}, author = ${input.author}, updated_at = now()
    WHERE id = ${id}
    RETURNING *`) as PostRow[];
  return rows[0] ? toPost(rows[0]) : null;
}

export async function deletePost(id: string) {
  if (!UUID.test(id)) return false;
  const sql = await query();
  const rows = await sql`DELETE FROM posts WHERE id = ${id} RETURNING id`;
  return (rows as unknown[]).length > 0;
}
