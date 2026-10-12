"use client";

import { Fragment, useMemo, useState } from "react";
import { ScanEye, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

type Stage = "hook" | "pressure" | "ask" | "cashout";

interface Span {
  start: number;
  end: number;
  intent: string;
  stage: Stage;
  label: string;
  why: string;
}

export interface XrayData {
  text: string;
  spans: Span[];
  stages: Record<Stage, string[]>;
  reassuring: string[];
}

const STAGES: { key: Stage; name: string; question: string; tone: string; mark: string }[] = [
  { key: "hook", name: "Hook", question: "Why you'd engage", tone: "text-primary border-primary/50 bg-primary/10", mark: "bg-primary/20 decoration-primary" },
  { key: "pressure", name: "Pressure", question: "Why you'd hurry", tone: "text-risk-medium border-risk-medium/50 bg-risk-medium/10", mark: "bg-risk-medium/25 decoration-risk-medium" },
  { key: "ask", name: "The ask", question: "What they want", tone: "text-destructive border-destructive/50 bg-destructive/10", mark: "bg-destructive/25 decoration-destructive" },
  { key: "cashout", name: "Cash-out", question: "How money leaves", tone: "text-risk-high border-risk-high/50 bg-risk-high/10", mark: "bg-risk-high/25 decoration-risk-high" },
];
const BY_KEY = Object.fromEntries(STAGES.map((s) => [s.key, s])) as Record<Stage, (typeof STAGES)[number]>;

/** The message itself, with each trap phrase marked and explained, plus
 * the four-stage anatomy the scam follows. */
export function ScamXray({ xray, compact = false }: { xray: XrayData | null | undefined; compact?: boolean }) {
  const [active, setActive] = useState<number | null>(null);
  const pieces = useMemo(() => {
    if (!xray) return [];
    const out: Array<{ text: string; span?: Span; index?: number }> = [];
    let cursor = 0;
    xray.spans.forEach((s, i) => {
      if (s.start > cursor) out.push({ text: xray.text.slice(cursor, s.start) });
      out.push({ text: xray.text.slice(s.start, s.end), span: s, index: i });
      cursor = s.end;
    });
    if (cursor < xray.text.length) out.push({ text: xray.text.slice(cursor) });
    return out;
  }, [xray]);

  if (!xray || !xray.text.trim()) return null;
  const hasSpans = xray.spans.length > 0;
  const current = active !== null ? xray.spans[active] : null;

  return (
    <section aria-label="Scam X-Ray" className={cn("rounded-2xl border border-border bg-card/60 backdrop-blur", compact ? "p-4" : "p-5 sm:p-6")}>
      <div className="flex items-center gap-2">
        <ScanEye className="h-4 w-4 text-primary" />
        <h3 className="font-display text-base font-semibold">Scam X-Ray</h3>
        <span className="text-xs text-muted-foreground">
          {hasSpans ? "Tap a highlighted phrase to see why it's a red flag." : "No trap phrases found in this message."}
        </span>
      </div>

      {hasSpans && (
        <ol className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label="How this scam works">
          {STAGES.map((st, i) => {
            const labels = xray.stages[st.key] ?? [];
            const lit = labels.length > 0;
            return (
              <li
                key={st.key}
                className={cn(
                  "relative rounded-xl border p-3 transition-colors",
                  lit ? st.tone : "border-dashed border-border text-muted-foreground opacity-60",
                )}
              >
                <p className="text-xs font-semibold">
                  {i + 1}. {st.name}
                </p>
                <p className="text-[0.7rem] opacity-80">{st.question}</p>
                {!compact && lit && <p className="mt-1.5 text-xs leading-snug text-foreground">{labels.join(", ")}</p>}
              </li>
            );
          })}
        </ol>
      )}

      <p className={cn("mt-4 whitespace-pre-wrap rounded-xl border border-border bg-background/60 leading-relaxed", compact ? "p-3 text-sm" : "p-4 text-[0.95rem]")}>
        {pieces.map((p, i) =>
          p.span ? (
            <mark
              key={i}
              tabIndex={0}
              role="button"
              aria-label={`${p.span.label}: ${p.text}`}
              aria-pressed={active === p.index}
              onClick={() => setActive(active === p.index ? null : (p.index ?? null))}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setActive(active === p.index ? null : (p.index ?? null)))}
              className={cn(
                "cursor-pointer rounded px-0.5 text-foreground underline decoration-2 underline-offset-4 transition-shadow",
                BY_KEY[p.span.stage].mark,
                active === p.index && "ring-2 ring-offset-1 ring-offset-background ring-current",
              )}
            >
              {p.text}
            </mark>
          ) : (
            <Fragment key={i}>{p.text}</Fragment>
          ),
        )}
      </p>

      {current && (
        <div className={cn("mt-3 rounded-xl border p-3 text-sm", BY_KEY[current.stage].tone)} role="status">
          <p className="font-semibold">
            {BY_KEY[current.stage].name}: {current.label}
          </p>
          <p className="mt-0.5 text-foreground">{current.why}</p>
        </div>
      )}

      {!hasSpans && xray.reassuring.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm">
          {xray.reassuring.map((r) => (
            <li key={r} className="flex items-start gap-2 text-risk-low">
              <ShieldCheck className="mt-0.5 h-4 w-4" /> <span className="text-foreground">{r}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
