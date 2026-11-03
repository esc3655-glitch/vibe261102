import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ArrowLeftIcon, PencilIcon } from "lucide-react";

import { DeletePostButton } from "@/components/delete-post-button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDateTime } from "@/lib/format";
import { getPost } from "@/lib/posts";

export async function generateMetadata({ params }: PageProps<"/posts/[id]">) {
  const post = await getPost((await params).id);
  return { title: post?.title ?? "게시글을 찾을 수 없음" };
}

export default function PostPage({ params }: PageProps<"/posts/[id]">) {
  return (
    <div className="grid gap-4">
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/">
            <ArrowLeftIcon data-icon="inline-start" />
            목록으로
          </Link>
        </Button>
      </div>
      <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-muted" />}>
        <PostDetail params={params} />
      </Suspense>
    </div>
  );
}

async function PostDetail({ params }: { params: PageProps<"/posts/[id]">["params"] }) {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) notFound();

  const edited = post.updatedAt !== post.createdAt;

  return (
    <Card>
      <CardHeader className="gap-2">
        <CardTitle className="text-2xl leading-snug break-words">{post.title}</CardTitle>
        <CardDescription className="flex flex-wrap gap-x-3 gap-y-1">
          <span className="font-medium text-foreground">{post.author}</span>
          <span>작성 {formatDateTime(post.createdAt)}</span>
          {edited && <span>수정 {formatDateTime(post.updatedAt)}</span>}
        </CardDescription>
      </CardHeader>
      <Separator />
      <CardContent>
        <div className="min-h-32 leading-relaxed break-words whitespace-pre-wrap">{post.content}</div>
      </CardContent>
      <Separator />
      <CardFooter className="justify-end gap-2">
        <Button variant="outline" asChild>
          <Link href={`/posts/${post.id}/edit`}>
            <PencilIcon data-icon="inline-start" />
            수정
          </Link>
        </Button>
        <DeletePostButton id={post.id} title={post.title} />
      </CardFooter>
    </Card>
  );
}
