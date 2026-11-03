// data/posts.json에 있던 글을 Neon의 posts 테이블로 옮긴다. 같은 id가 이미 있으면 건너뛴다.
// 실행: npm run db:import
import { readFile } from "node:fs/promises";
import { neon } from "@neondatabase/serverless";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL이 없습니다. .env.local을 확인해 주세요.");
  process.exit(1);
}

const file = process.argv[2] ?? "data/posts.json";
const posts = JSON.parse(await readFile(file, "utf8"));
const sql = neon(url);

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

const inserted = await sql`
  INSERT INTO posts (id, title, content, author, created_at, updated_at)
  SELECT id, title, content, author, "createdAt", "updatedAt"
  FROM jsonb_to_recordset(${JSON.stringify(posts)}::jsonb)
    AS s(id uuid, title text, content text, author text, "createdAt" timestamptz, "updatedAt" timestamptz)
  ON CONFLICT (id) DO NOTHING
  RETURNING id`;

console.log(`${file}: ${posts.length}개 중 ${inserted.length}개를 가져왔습니다.`);
