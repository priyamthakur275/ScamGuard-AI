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
    async function poll() {
      const ok = await checkHealth();
      if (cancelled) return;
      setStatus(ok ? "online" : "waking");
      // Re-check quickly while waking, then once a minute.
      timer = setTimeout(poll, ok ? 60000 : 5000);
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
