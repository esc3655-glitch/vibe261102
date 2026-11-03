import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { ThemeProvider } from "next-themes";
import { Suspense } from "react";
import { MessagesSquareIcon } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { ToastFromQuery } from "@/components/toast-from-query";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "DemoWeb 게시판",
    template: "%s | DemoWeb 게시판",
  },
  description: "Next.js와 shadcn/ui로 만든 데모 게시판",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
            <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-4">
              <Link href="/" className="flex items-center gap-2 font-semibold">
                <MessagesSquareIcon className="size-5" />
                DemoWeb 게시판
              </Link>
              <ThemeToggle />
            </div>
          </header>
          <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
          <footer className="border-t py-6 text-center text-sm text-muted-foreground">
            © 2026 DemoWeb · Next.js + shadcn/ui 데모
          </footer>
          <Toaster richColors position="top-center" />
          <Suspense>
            <ToastFromQuery />
          </Suspense>
        </ThemeProvider>
      </body>
    </html>
  );
}
