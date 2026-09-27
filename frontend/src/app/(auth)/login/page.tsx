import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-left">
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">Access request</p>
        <h1 className="mt-1 font-sans text-2xl font-semibold tracking-tight">Sign in to ScamGuard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Enter your credentials to continue to your account.</p>
      </div>
      <Suspense fallback={<div className="h-[400px] w-full animate-pulse rounded-xl bg-muted/50" />}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
