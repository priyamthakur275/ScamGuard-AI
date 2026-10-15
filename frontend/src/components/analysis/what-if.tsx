"use client";

import { useState } from "react";
import { FlaskConical, Loader2 } from "lucide-react";
import { whatIf, type WhatIfResult } from "@/lib/api/tools";
import type { AnalysisResult } from "@/types";

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** "What makes it a scam?": each suspicious part is put back on its own into
 * the message with every other cue removed, and re-scored by the same engine. */
export function WhatIf({ result }: { result: AnalysisResult }) {
  const [data, setData] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (result.verdict === "legitimate" || !result.text || result.text.length < 3) return null;

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await whatIf(result.text.slice(0, 2000)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not run the check.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-2xl border border-border bg-card p-5" aria-labelledby={`whatif-${result.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id={`whatif-${result.id}`} className="flex items-center gap-2 font-semibold">
            <FlaskConical className="h-4 w-4 text-primary" /> What makes it a scam?
          </h3>
          <p className="text-sm text-muted-foreground">Each suspicious part is tested on its own to show how much risk it adds.</p>
        </div>
        {!data && (
          <button type="button" onClick={run} disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-primary/50 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-60">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />} {loading ? "Testing…" : "Run the test"}
          </button>
        )}
      </div>
      {error && <p role="alert" className="mt-3 text-sm text-destructive">{error}</p>}
      {data && data.parts.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground">No single phrase stands out; the risk comes from the overall wording the model learned from past scams.</p>
      )}
      {data && data.parts.length > 0 && data.baseline !== null && (
        <div className="mt-4 space-y-3">
          <p className="text-sm">
            With every suspicious part removed the message scores <strong>{pct(data.baseline)}</strong>. Adding back one part at a time:
          </p>
          <ul className="space-y-2.5">
            {data.parts.map((p) => (
              <li key={p.label + p.phrase} className="space-y-1">
                <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                  <span><span className="font-medium capitalize">{p.label}</span> <span className="text-muted-foreground">“{p.phrase}”</span></span>
                  <span className="font-mono text-xs">{p.lift > 0.005 ? `+${pct(p.lift)} → ${pct(p.score_alone)}` : "no change"}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
                  <div className="h-full rounded-full bg-destructive/80" style={{ width: `${Math.max(0, Math.min(100, p.lift * 100))}%` }} />
                </div>
              </li>
            ))}
          </ul>
          {data.redundant && (
            <p className="rounded-xl bg-muted/60 p-3 text-sm">
              Several of these are each strong enough on their own, so deleting just one would not make this message safe. That is typical of real scams.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
