import { BackendWarmup } from "@/components/layout/backend-warmup";
import { AuthShell } from "@/components/auth/auth-shell";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <BackendWarmup />
      <AuthShell>{children}</AuthShell>
    </>
  );
}
