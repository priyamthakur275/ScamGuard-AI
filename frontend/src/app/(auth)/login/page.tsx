import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="flex flex-col gap-5">
      <div className="text-center">
        <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">Welcome Back</h1>
        <p className="mt-1 text-xs text-muted-foreground">Sign in to continue to ScamGuard AI</p>
      </div>
      <Suspense fallback={<div className="h-[360px] w-full animate-pulse rounded-xl bg-muted/40" />}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
