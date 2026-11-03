import type { Metadata } from "next";

import { createPostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";

export const metadata: Metadata = { title: "글쓰기" };

export default function NewPostPage() {
  return (
    <PostForm title="새 글 작성" submitLabel="등록" cancelHref="/" action={createPostAction} />
  );
}
