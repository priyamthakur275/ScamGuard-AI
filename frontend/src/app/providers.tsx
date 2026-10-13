"use client";

import { useEffect, type ReactNode } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { ThemeProvider } from "@/lib/theme/theme-context";
import { ToastProvider } from "@/hooks/use-toast";
import { MotionConfig } from "framer-motion";
import { Toaster } from "@/components/ui/toaster";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { CopilotProvider } from "@/components/copilot/copilot-provider";
import { ScamGuardChat } from "@/components/copilot/scamguard-chat";
import { GlobalErrorReporter } from "@/components/layout/global-error-reporter";
import { ErrorBoundary } from "@/components/error-boundary";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    // Remove legacy, unscoped sensitive history left by older versions.
    try { localStorage.removeItem("scamguard_local_history"); } catch {}
  }, []);

  return (
    <MotionConfig reducedMotion="user"><ThemeProvider><LanguageProvider>
      <ToastProvider>
        <AuthProvider>
          <CopilotProvider>
            {children}
            <ErrorBoundary area="Copilot" silentFallback>
              <ScamGuardChat />
            </ErrorBoundary>
          </CopilotProvider>
          <Toaster />
          <GlobalErrorReporter />
        </AuthProvider>
      </ToastProvider>
    </LanguageProvider></ThemeProvider></MotionConfig>
  );
}
