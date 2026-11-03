import { notFound } from "next/navigation";
import { Suspense } from "react";

import { updatePostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";
import { getPost } from "@/lib/posts";

export const metadata = { title: "글 수정" };

export default function EditPostPage({ params }: PageProps<"/posts/[id]/edit">) {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-muted" />}>
      <EditForm params={params} />
    </Suspense>
  );
}

async function EditForm({ params }: { params: PageProps<"/posts/[id]/edit">["params"] }) {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) notFound();

  return (
    <PostForm
      title="글 수정"
      submitLabel="수정 완료"
      cancelHref={`/posts/${post.id}`}
      defaultValues={{ title: post.title, author: post.author, content: post.content }}
      action={updatePostAction.bind(null, post.id)}
    />
  );
}
