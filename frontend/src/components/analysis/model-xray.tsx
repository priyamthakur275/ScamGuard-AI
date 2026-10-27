"use client";

import { useEffect, useState } from "react";
import { Binary, Loader2 } from "lucide-react";
import { modelXray, type ModelXrayResult, type XrayFeature } from "@/lib/api/tools";
import { cn } from "@/lib/utils";

const pretty = (f: string) =>
  f.replace(/__url__/g, "[link]").replace(/__num__/g, "[number]").replace(/__phone__/g, "[phone]").replace(/__email__/g, "[email]");
const sign = (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}`;
const pctText = (p: number) => (p > 0.9999 ? ">99.99%" : p < 0.0001 ? "<0.01%" : `${(p * 100).toFixed(2)}%`);

function FeatureBars({ items, max, tone }: { items: XrayFeature[]; max: number; tone: "scam" | "genuine" }) {
  if (!items.length) return <p className="text-xs text-muted-foreground">None in this message.</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((it) => (
        <li key={it.feature} className="grid grid-cols-[minmax(0,1fr)_3.2rem] items-center gap-2 text-xs">
          <div className="min-w-0">
            <span className="block truncate font-mono" title={pretty(it.feature)}>{pretty(it.feature)}</span>
            <div className="mt-0.5 h-1.5 rounded-[999px] bg-muted">
              <div
                className={cn("h-full rounded-[999px]", tone === "scam" ? "bg-destructive/80" : "bg-safe")}
                style={{ width: `${Math.max(4, (Math.abs(it.push) / max) * 100)}%` }}
              />
            </div>
          </div>
          <span className="text-right font-mono tabular-nums text-muted-foreground">{sign(it.push)}</span>
        </li>
      ))}
    </ul>
  );
}

/** "Open the model": the classifier's probability for this message, taken
 * apart into the exact sum that produces it, p = σ(b + Σ wᵢxᵢ). */
export function ModelXray({ text, autoOpen = false }: { text: string; autoOpen?: boolean }) {
  const [data, setData] = useState<ModelXrayResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const clean = ((text || "").split("\n\nDetected language/concepts", 1)[0] ?? "").slice(0, 2000);
  useEffect(() => {
    setData(null);
    if (autoOpen && clean.trim().length >= 3) void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clean, autoOpen]);

  if (clean.trim().length < 3) return null;

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setData(await modelXray(clean));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open the model.");
    } finally {
      setLoading(false);
    }
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-border bg-background/40 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold"><Binary className="h-4 w-4 text-primary" /> Open the model</p>
            <p className="mt-0.5 text-xs text-muted-foreground">See the exact maths behind the model&apos;s score for this message.</p>
          </div>
          <button
            onClick={run}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-60"
          >
            {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />} {loading ? "Opening…" : "Show the maths"}
          </button>
        </div>
        {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
      </div>
    );
  }

  const parts = [
    { label: "Starting point (bias)", v: data.bias, hint: "where every message starts" },
    { label: `Words towards scam (${data.words_up_count})`, v: data.words_up_total, hint: "word and word-pair weights" },
    { label: `Words towards genuine (${data.words_down_count})`, v: data.words_down_total, hint: "" },
    { label: `Spelling patterns (${data.char_count})`, v: data.char_total, hint: "2–5 letter pieces; catch K.Y.C, bl0cked" },
  ];
  const span = Math.max(1, ...parts.map((p) => Math.abs(p.v)));
  const maxFeat = Math.max(0.01, ...data.words_up.map((w) => w.push), ...data.words_down.map((w) => -w.push));

  return (
    <div className="rounded-lg border border-border bg-background/40 p-4">
      <p className="flex items-center gap-2 text-sm font-semibold"><Binary className="h-4 w-4 text-primary" /> Inside the model</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Logistic regression adds up a weight for every word and letter pattern it finds ({data.active_features} of its{" "}
        {data.vocabulary.toLocaleString("en-IN")}), then squashes the total into a probability. These parts add up exactly.
      </p>

      <div className="mt-4 space-y-2">
        {parts.map((p) => (
          <div key={p.label} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_3.6rem] sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)_3.6rem] items-center gap-3 text-xs">
            <span className="truncate" title={p.hint}>{p.label}</span>
            <div className="relative h-3 rounded bg-muted">
              <span className="absolute inset-y-0 left-1/2 w-px bg-border" />
              <span
                className={cn("absolute inset-y-0 rounded", p.v >= 0 ? "left-1/2 bg-destructive/80" : "right-1/2 bg-safe")}
                style={{ width: `${(Math.abs(p.v) / span) * 50}%` }}
              />
            </div>
            <span className="text-right font-mono tabular-nums">{sign(p.v)}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 overflow-x-auto rounded-md bg-muted/60 px-3 py-2.5 font-mono text-xs">
        <span className="break-words sm:whitespace-nowrap">
          p = σ({parts.map((p) => sign(p.v)).join(" ")}) = σ({data.logit.toFixed(2)}) ={" "}
          <b className={data.probability >= 0.5 ? "text-destructive" : "text-safe"}>{pctText(data.probability)}</b>
        </span>
      </div>

      <div className="mt-4 grid gap-5 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium">Pushing towards scam</p>
          <FeatureBars items={data.words_up} max={maxFeat} tone="scam" />
        </div>
        <div>
          <p className="mb-2 text-xs font-medium">Pushing towards genuine</p>
          <FeatureBars items={data.words_down} max={maxFeat} tone="genuine" />
        </div>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">
        Words are shown after cleaning (lower case, light stemming; links and numbers become tokens). This is the classifier on
        its own; the final risk score then applies the intent rules shown above. Model: {data.model}.
      </p>
    </div>
  );
}
