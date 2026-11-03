"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

const MESSAGES: Record<string, string> = {
  created: "게시글을 등록했습니다.",
  updated: "게시글을 수정했습니다.",
  deleted: "게시글을 삭제했습니다.",
  missing: "게시글을 찾을 수 없습니다.",
};

// 서버 액션이 redirect 하면서 붙인 ?toast= 값을 알림으로 보여 주고 URL에서 지운다.
export function ToastFromQuery() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const key = searchParams.get("toast");

  useEffect(() => {
    if (!key) return;
    const message = MESSAGES[key];
    if (message) toast.success(message, { id: key });
    const next = new URLSearchParams(searchParams);
    next.delete("toast");
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [key, pathname, router, searchParams]);

  return null;
}
