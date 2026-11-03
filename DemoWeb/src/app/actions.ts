"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createPost, deletePost, updatePost, type PostInput } from "@/lib/posts";

export type FormState = {
  errors?: Partial<Record<keyof PostInput, string>>;
  values?: PostInput;
};

const LIMITS = { title: 100, author: 30, content: 5000 } as const;

function parse(formData: FormData): { input: PostInput; errors: FormState["errors"] } {
  const input: PostInput = {
    title: String(formData.get("title") ?? "").trim(),
    author: String(formData.get("author") ?? "").trim(),
    content: String(formData.get("content") ?? "").trim(),
  };
  const errors: NonNullable<FormState["errors"]> = {};
  if (!input.title) errors.title = "제목을 입력해 주세요.";
  else if (input.title.length > LIMITS.title) errors.title = `제목은 ${LIMITS.title}자 이하로 입력해 주세요.`;
  if (!input.author) errors.author = "작성자를 입력해 주세요.";
  else if (input.author.length > LIMITS.author) errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;
  if (!input.content) errors.content = "내용을 입력해 주세요.";
  else if (input.content.length > LIMITS.content) errors.content = `내용은 ${LIMITS.content}자 이하로 입력해 주세요.`;
  return { input, errors: Object.keys(errors).length ? errors : undefined };
}

export async function createPostAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const { input, errors } = parse(formData);
  if (errors) return { errors, values: input };
  const post = await createPost(input);
  revalidatePath("/", "layout");
  redirect(`/posts/${post.id}?toast=created`);
}

export async function updatePostAction(
  id: string,
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  const { input, errors } = parse(formData);
  if (errors) return { errors, values: input };
  const post = await updatePost(id, input);
  if (!post) redirect("/?toast=missing");
  revalidatePath("/", "layout");
  redirect(`/posts/${id}?toast=updated`);
}

export async function deletePostAction(id: string) {
  await deletePost(id);
  revalidatePath("/", "layout");
  redirect("/?toast=deleted");
}
