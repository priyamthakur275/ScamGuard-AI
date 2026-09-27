import type { Metadata } from "next";
import { Suspense } from "react";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = { title: "Create account" };

export default function RegisterPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
        <p className="mt-1 text-sm text-muted-foreground">Start detecting scams in seconds</p>
      </div>
      <Suspense fallback={<div className="h-[400px] w-full animate-pulse rounded-xl bg-muted/50" />}>
        <RegisterForm />
      </Suspense>
    </div>
  );
}
