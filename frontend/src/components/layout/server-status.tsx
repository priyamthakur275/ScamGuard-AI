"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api/public";
import { cn } from "@/lib/utils";

type Status = "checking" | "online" | "waking";

const LABEL: Record<Status, string> = {
  checking: "Checking server",
  online: "Server online",
  waking: "Server waking up",
};

/** Small live indicator so a slow first request reads as "waking", not "broken". */
export function ServerStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    function schedule() {
      if (cancelled) return;
      if (document.visibilityState === "hidden") {
        document.addEventListener("visibilitychange", schedule, { once: true });
        return;
      }
      void poll();
    }
    async function poll() {
      const ok = await checkHealth();
      if (cancelled) return;
      setStatus(ok ? "online" : "waking");
      // Gentle polling: 2 min when healthy, 10 s while waking, and paused
      // while the tab is hidden, so open tabs never flood the backend.
      timer = setTimeout(schedule, ok ? 120000 : 10000);
    }
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return (
    <span
      className="hidden items-center gap-1.5 font-mono text-[11px] text-muted-foreground sm:inline-flex"
      title={LABEL[status]}
      aria-live="polite"
    >
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          status === "online" && "bg-emerald-500",
          status === "waking" && "animate-pulse bg-amber-500",
          status === "checking" && "bg-muted-foreground/50",
        )}
        aria-hidden="true"
      />
      {LABEL[status]}
    </span>
  );
}
