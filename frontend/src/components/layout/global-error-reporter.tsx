"use client";

import { useEffect, useRef } from "react";
import { useToast } from "@/hooks/use-toast";

/** Surfaces promise rejections that no code handled, instead of letting them
 * fail silently. Aborted requests are expected and ignored; toasts are
 * throttled so one bad loop cannot flood the screen. */
export function GlobalErrorReporter() {
  const { toast } = useToast();
  const last = useRef(0);

  useEffect(() => {
    const onRejection = (event: PromiseRejectionEvent) => {
      const reason: unknown = event.reason;
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      console.error("[ScamGuard] Unhandled promise rejection:", reason);
      const now = Date.now();
      if (now - last.current < 10_000) return;
      last.current = now;
      toast({
        title: "Something went wrong",
        description: reason instanceof Error && reason.message ? reason.message : "An action did not finish. Please try again.",
        variant: "error",
      });
    };
    window.addEventListener("unhandledrejection", onRejection);
    return () => window.removeEventListener("unhandledrejection", onRejection);
  }, [toast]);

  return null;
}
