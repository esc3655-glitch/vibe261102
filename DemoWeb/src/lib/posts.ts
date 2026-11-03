import "server-only";

import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

export type Post = {
  id: string;
  title: string;
  content: string;
  author: string;
  createdAt: string;
  updatedAt: string;
};

export type PostInput = Pick<Post, "title" | "content" | "author">;

const DATA_DIR = path.join(process.cwd(), "data");
const DATA_FILE = path.join(DATA_DIR, "posts.json");

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
      "외부 DB 없이 바로 실행할 수 있도록 프로젝트의 data/posts.json 파일에 저장합니다.\n파일을 지우면 다음 실행 때 샘플 글로 다시 채워집니다.",
  },
  {
    title: "다크 모드도 지원합니다",
    author: "디자이너",
    content: "오른쪽 위의 테마 버튼으로 라이트, 다크, 시스템 설정을 고를 수 있습니다.",
  },
];

// 동시에 들어온 쓰기 요청이 파일을 덮어쓰지 않도록 순서대로 처리한다.
let writeQueue: Promise<unknown> = Promise.resolve();

async function readAll(): Promise<Post[]> {
  try {
    const raw = await fs.readFile(DATA_FILE, "utf8");
    return JSON.parse(raw) as Post[];
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    return seed();
  }
}

// 파일이 없을 때 샘플 글로 만든다. 'wx'로 만들어 동시에 들어온 요청 중 하나만 쓰게 한다.
async function seed(): Promise<Post[]> {
  const now = Date.now();
  const seeded = SEED.map((input, i) => {
    const at = new Date(now - (SEED.length - i) * 60_000).toISOString();
    return { ...input, id: randomUUID(), createdAt: at, updatedAt: at };
  });
  await fs.mkdir(DATA_DIR, { recursive: true });
  try {
    await fs.writeFile(DATA_FILE, JSON.stringify(seeded, null, 2), { encoding: "utf8", flag: "wx" });
    return seeded;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
    return JSON.parse(await fs.readFile(DATA_FILE, "utf8")) as Post[];
  }
}

async function writeAll(posts: Post[]) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  const tmp = `${DATA_FILE}.${randomUUID()}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(posts, null, 2), "utf8");
  await fs.rename(tmp, DATA_FILE);
}

function mutate<T>(fn: (posts: Post[]) => { posts: Post[]; result: T }): Promise<T> {
  const run = writeQueue.then(async () => {
    const { posts, result } = fn(await readAll());
    await writeAll(posts);
    return result;
  });
  writeQueue = run.catch(() => undefined);
  return run;
}

export const PAGE_SIZE = 10;

export async function listPosts({ query = "", page = 1 }: { query?: string; page?: number }) {
  const q = query.trim().toLowerCase();
  const all = (await readAll())
    .filter(
      (p) =>
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.content.toLowerCase().includes(q) ||
        p.author.toLowerCase().includes(q),
    )
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));

  const totalPages = Math.max(1, Math.ceil(all.length / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);
  return {
    posts: all.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE),
    total: all.length,
    page: current,
    totalPages,
  };
}

export async function getPost(id: string) {
  return (await readAll()).find((p) => p.id === id) ?? null;
}

export function createPost(input: PostInput) {
  return mutate((posts) => {
    const now = new Date().toISOString();
    const post: Post = { ...input, id: randomUUID(), createdAt: now, updatedAt: now };
    return { posts: [...posts, post], result: post };
  });
}

export function updatePost(id: string, input: PostInput) {
  return mutate((posts) => {
    let updated: Post | null = null;
    const next = posts.map((p) => {
      if (p.id !== id) return p;
      updated = { ...p, ...input, updatedAt: new Date().toISOString() };
      return updated;
    });
    return { posts: next, result: updated as Post | null };
  });
}

export function deletePost(id: string) {
  return mutate((posts) => {
    const next = posts.filter((p) => p.id !== id);
    return { posts: next, result: next.length !== posts.length };
  });
}
