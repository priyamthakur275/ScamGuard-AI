"use client";

import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

/** Secondary analysis panels, folded away so the verdict, the trap phrases
 * and what to do next stay on one screen. Nothing is removed; one click
 * opens the rest. */
export function MoreDetails({ children, label = "Deeper analysis", hint }: { children: ReactNode; label?: string; hint?: string }) {
  return (
    <details className="elder-hide group rounded-lg border border-border bg-background/40 print:block [&[open]>summary_svg]:rotate-180">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
        <span>
          <span className="block text-sm font-semibold text-foreground">{label}</span>
          {hint && <span className="mt-0.5 block text-xs text-muted-foreground">{hint}</span>}
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform" aria-hidden="true" />
      </summary>
      <div className="flex flex-col gap-6 border-t border-border p-5">{children}</div>
    </details>
  );
}
