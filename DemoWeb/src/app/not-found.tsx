import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="grid place-items-center gap-4 py-24 text-center">
      <h1 className="text-2xl font-bold">페이지를 찾을 수 없습니다</h1>
      <p className="text-muted-foreground">삭제되었거나 존재하지 않는 게시글입니다.</p>
      <Button asChild>
        <Link href="/">목록으로 돌아가기</Link>
      </Button>
    </div>
  );
}
