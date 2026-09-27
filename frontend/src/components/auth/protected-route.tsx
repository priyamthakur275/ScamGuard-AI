"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { FullPageSpinner } from "@/components/ui/spinner";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  // While the real session check is in flight, or once it has come back
  // negative and a redirect has just been kicked off, render nothing
  // rather than the protected page -- a scan/history/settings page must
  // never render (and try to call the API) for a visitor who was never
  // actually authenticated.
  if (isLoading || !isAuthenticated) {
    return <FullPageSpinner />;
  }

  return <>{children}</>;
}
