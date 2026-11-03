import Link from "next/link";
import { Suspense } from "react";
import { PenSquareIcon, SearchIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { listPosts, PAGE_SIZE } from "@/lib/posts";

export default function Home({ searchParams }: PageProps<"/">) {
  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">자유 게시판</h1>
          <p className="text-sm text-muted-foreground">자유롭게 글을 남기고 의견을 나눠 보세요.</p>
        </div>
        <Button asChild>
          <Link href="/posts/new">
            <PenSquareIcon data-icon="inline-start" />
            글쓰기
          </Link>
        </Button>
      </div>
      <Suspense fallback={<ListSkeleton />}>
        <PostList searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function PostList({ searchParams }: { searchParams: PageProps<"/">["searchParams"] }) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q : "";
  const requestedPage = Number(typeof params.page === "string" ? params.page : 1) || 1;
  const { posts, total, page, totalPages } = await listPosts({ query, page: requestedPage });

  const hrefFor = (p: number) => {
    const sp = new URLSearchParams();
    if (query) sp.set("q", query);
    if (p > 1) sp.set("page", String(p));
    const qs = sp.toString();
    return qs ? `/?${qs}` : "/";
  };

  return (
    <>
      <form action="/" className="flex gap-2" role="search">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            name="q"
            defaultValue={query}
            placeholder="제목, 내용, 작성자로 검색"
            className="pl-8"
            aria-label="검색어"
          />
        </div>
        <Button type="submit" variant="secondary">
          검색
        </Button>
        {query && (
          <Button variant="ghost" asChild>
            <Link href="/">초기화</Link>
          </Button>
        )}
      </form>

      <p className="text-sm text-muted-foreground">
        {query ? (
          <>
            &ldquo;{query}&rdquo; 검색 결과 <strong className="text-foreground">{total}</strong>건
          </>
        ) : (
          <>
            전체 글 <strong className="text-foreground">{total}</strong>건
          </>
        )}
      </p>

      {posts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {query ? "검색 결과가 없습니다." : "아직 게시글이 없습니다. 첫 글을 작성해 보세요!"}
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 태블릿 이상: 표 */}
          <Card className="hidden py-0 md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16 text-center">번호</TableHead>
                  <TableHead>제목</TableHead>
                  <TableHead className="w-32">작성자</TableHead>
                  <TableHead className="w-32">작성일</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {posts.map((post, i) => (
                  <TableRow key={post.id}>
                    <TableCell className="text-center text-muted-foreground">
                      {total - (page - 1) * PAGE_SIZE - i}
                    </TableCell>
                    <TableCell className="max-w-0">
                      <Link
                        href={`/posts/${post.id}`}
                        className="block truncate font-medium hover:underline"
                      >
                        {post.title}
                        {post.updatedAt !== post.createdAt && (
                          <Badge variant="secondary" className="ml-2 align-middle">
                            수정됨
                          </Badge>
                        )}
                      </Link>
                    </TableCell>
                    <TableCell className="truncate">{post.author}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(post.createdAt)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          {/* 모바일: 카드 목록 */}
          <ul className="grid gap-3 md:hidden">
            {posts.map((post) => (
              <li key={post.id}>
                <Link href={`/posts/${post.id}`}>
                  <Card className="gap-1 py-4 transition-colors hover:bg-muted/50">
                    <CardContent className="grid gap-1">
                      <span className="truncate font-medium">{post.title}</span>
                      <span className="text-sm text-muted-foreground">
                        {post.author} · {formatDate(post.createdAt)}
                      </span>
                    </CardContent>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}

      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href={hrefFor(Math.max(1, page - 1))}
                text="이전"
                aria-label="이전 페이지"
                aria-disabled={page === 1}
                className={page === 1 ? "pointer-events-none opacity-50" : undefined}
              />
            </PaginationItem>
            {pageNumbers(page, totalPages).map((p, i) =>
              p === null ? (
                <PaginationItem key={`gap-${i}`}>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : (
                <PaginationItem key={p}>
                  <PaginationLink href={hrefFor(p)} isActive={p === page}>
                    {p}
                  </PaginationLink>
                </PaginationItem>
              ),
            )}
            <PaginationItem>
              <PaginationNext
                href={hrefFor(Math.min(totalPages, page + 1))}
                text="다음"
                aria-label="다음 페이지"
                aria-disabled={page === totalPages}
                className={page === totalPages ? "pointer-events-none opacity-50" : undefined}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </>
  );
}

// 1 … 4 5 6 … 10 형태로 보여 줄 페이지 번호 (null은 생략 부호)
function pageNumbers(current: number, total: number): (number | null)[] {
  const pages = new Set([1, total, current - 1, current, current + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
  const result: (number | null)[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) result.push(null);
    result.push(p);
  });
  return result;
}

function ListSkeleton() {
  return (
    <div className="grid gap-3" aria-busy="true" aria-label="불러오는 중">
      <div className="h-9 animate-pulse rounded-lg bg-muted" />
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  );
}
