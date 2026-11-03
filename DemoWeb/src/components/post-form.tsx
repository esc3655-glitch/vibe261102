"use client";

import Link from "next/link";
import { useActionState } from "react";

import type { FormState } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { PostInput } from "@/lib/posts";

type Props = {
  title: string;
  submitLabel: string;
  cancelHref: string;
  defaultValues?: PostInput;
  action: (state: FormState, formData: FormData) => Promise<FormState>;
};

export function PostForm({ title, submitLabel, cancelHref, defaultValues, action }: Props) {
  const [state, formAction, pending] = useActionState(action, {});
  const values = state.values ?? defaultValues;
  const errors = state.errors ?? {};

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
      </CardHeader>
      {/* 서버에서 검증 오류가 나면 key가 바뀌어 입력값을 그대로 다시 채운다. */}
      <form action={formAction} key={JSON.stringify(state.values ?? null)} noValidate>
        <CardContent className="grid gap-5">
          <Field id="title" label="제목" error={errors.title}>
            <Input
              id="title"
              name="title"
              defaultValue={values?.title}
              placeholder="제목을 입력하세요"
              maxLength={100}
              aria-invalid={!!errors.title}
              required
            />
          </Field>
          <Field id="author" label="작성자" error={errors.author}>
            <Input
              id="author"
              name="author"
              defaultValue={values?.author}
              placeholder="이름 또는 닉네임"
              maxLength={30}
              aria-invalid={!!errors.author}
              className="sm:max-w-xs"
              required
            />
          </Field>
          <Field id="content" label="내용" error={errors.content}>
            <Textarea
              id="content"
              name="content"
              defaultValue={values?.content}
              placeholder="내용을 입력하세요"
              maxLength={5000}
              aria-invalid={!!errors.content}
              className="min-h-64"
              required
            />
          </Field>
        </CardContent>
        <CardFooter className="mt-6 justify-end gap-2">
          <Button variant="outline" asChild>
            <Link href={cancelHref}>취소</Link>
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? "저장 중..." : submitLabel}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
