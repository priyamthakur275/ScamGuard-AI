"use client";

import { useEffect, type ReactNode } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { ThemeProvider } from "@/lib/theme/theme-context";
import { ToastProvider } from "@/hooks/use-toast";
import { MotionConfig } from "framer-motion";
import { Toaster } from "@/components/ui/toaster";
import { LanguageProvider } from "@/lib/i18n/language-context";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    // Remove legacy, unscoped sensitive history left by older versions.
    try { localStorage.removeItem("scamguard_local_history"); } catch {}
  }, []);

  return (
    <MotionConfig reducedMotion="user"><ThemeProvider><LanguageProvider>
      <ToastProvider>
        <AuthProvider>
          {children}
          <Toaster />
        </AuthProvider>
      </ToastProvider>
    </LanguageProvider></ThemeProvider></MotionConfig>
  );
}
