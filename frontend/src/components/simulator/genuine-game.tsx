"use client";

import { useEffect, useMemo, useState } from "react";
import { Lightbulb, Loader2, RotateCcw, Sparkles, Wand2 } from "lucide-react";
import { scamToGenuine, type GenuineCue, type ScamToGenuine } from "@/lib/api/tools";
import { cn } from "@/lib/utils";

const SAMPLES = [
  "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone.",
  "This is CBI Mumbai. You are under digital arrest. Do not tell anyone. Transfer Rs 50,000 to the verification account.",
  "Dear customer, your electricity will be disconnected tonight at 9:30 pm. Call officer 9123456780 immediately to update your bill.",
];

const pct = (v: number) => Math.round(v * 100);

function Meter({ score }: { score: number }) {
  const p = pct(score);
  const tone = score >= 0.5 ? "bg-destructive" : score >= 0.25 ? "bg-caution" : "bg-safe";
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">{score >= 0.5 ? "Looks like a scam" : score >= 0.25 ? "Still suspicious" : "Looks genuine"}</span>
        <span className="font-mono text-3xl font-semibold tabular-nums">{p}%</span>
      </div>
      <div className="mt-2 h-3 overflow-hidden rounded-[999px] bg-muted">
        <div className={cn("h-full rounded-[999px] transition-all duration-500", tone)} style={{ width: `${Math.max(2, p)}%` }} />
      </div>
      <p className="mt-1 text-[11px] text-muted-foreground">Live risk score from ScamGuard&apos;s real engine</p>
    </div>
  );
}

/** Highlight each remaining cue in the message as a clickable trap. */
function Marked({ text, cues, onFix, busy }: { text: string; cues: GenuineCue[]; onFix: (c: GenuineCue) => void; busy: boolean }) {
  const parts = useMemo(() => {
    const found = cues.map((c) => ({ c, i: text.indexOf(c.phrase) })).filter((x) => x.i >= 0).sort((a, b) => a.i - b.i);
    const out: Array<string | GenuineCue> = [];
    let at = 0;
    for (const { c, i } of found) {
      if (i < at) continue;
      out.push(text.slice(at, i), c);
      at = i + c.phrase.length;
    }
    out.push(text.slice(at));
    return out;
  }, [text, cues]);
  return (
    <p className="text-base leading-loose">
      {parts.map((p, k) =>
        typeof p === "string" ? <span key={k}>{p}</span> : (
          <button key={k} type="button" disabled={busy} onClick={() => onFix(p)} title={`${p.label}: click to fix`}
            className="mx-0.5 rounded bg-destructive/15 px-1 font-medium text-destructive underline decoration-destructive/60 decoration-2 underline-offset-4 transition-colors hover:bg-destructive/25 disabled:opacity-60">
            {p.phrase}
          </button>
        ),
      )}
    </p>
  );
}

/** "Scam to genuine": fix the traps one by one and watch the real risk score
 * fall, or let ScamGuard show the shortest path (a counterfactual explanation). */
export function GenuineGame() {
  const [start, setStart] = useState(SAMPLES[0]!);
  const [text, setText] = useState(start);
  const [data, setData] = useState<ScamToGenuine | null>(null);
  const [first, setFirst] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fixed, setFixed] = useState<GenuineCue[]>([]);
  const [solution, setSolution] = useState<number>(-1);

  const load = async (t: string, reset = false) => {
    setBusy(true);
    setError(null);
    try {
      const d = await scamToGenuine(t);
      setData(d);
      setText(t);
      if (reset) setFirst(d.score);
    } catch {
      setError("The server didn't answer. It may be waking up: try again in a few seconds.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    setFixed([]);
    setSolution(-1);
    void load(start, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start]);

  const fix = (c: GenuineCue) => {
    setFixed((f) => [...f, c]);
    const next = text.replace(c.phrase, c.replacement ? ` ${c.replacement} ` : " ").split(/\s+/).join(" ").replace(/^[\s:;,.-]+/, "").trim();
    void load(next);
  };

  // Play the model's own path step by step.
  useEffect(() => {
    if (solution < 0 || !data) return;
    if (solution >= data.steps.length) return;
    const t = setTimeout(() => setSolution((s) => s + 1), 1100);
    return () => clearTimeout(t);
  }, [solution, data]);

  const showingSolution = solution >= 0 && data && data.steps.length > 0;
  const step = showingSolution ? data!.steps[Math.min(solution, data!.steps.length) - 1] : null;
  const shownText = step ? step.text : text;
  const shownScore = step ? step.score : data?.score ?? first ?? 1;
  const won = !showingSolution && data && data.score < 0.25 && fixed.length > 0;

  return (
    <div className="mt-6 space-y-6">
      <div className="flex flex-wrap gap-2">
        {SAMPLES.map((s, i) => (
          <button key={i} type="button" onClick={() => setStart(s)}
            className={cn("rounded-md border px-3 py-1.5 text-xs", s === start ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:text-foreground")}>
            Scam {i + 1}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="rounded-2xl border border-border bg-card p-5">
          <p className="mb-3 flex items-center gap-2 text-xs text-muted-foreground"><Lightbulb className="h-3.5 w-3.5 text-primary" />
            {showingSolution ? "ScamGuard is fixing the biggest trap first…" : "Click each red trap to replace it with what a real bank would write."}
          </p>
          {!data && busy ? <div className="h-24 animate-pulse rounded bg-muted" /> : showingSolution ? (
            <p className="text-base leading-loose">{shownText}</p>
          ) : (
            <Marked text={text} cues={data?.cues ?? []} onFix={fix} busy={busy} />
          )}
          {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
          {won && <p className="mt-4 flex items-center gap-2 rounded-lg bg-safe/10 p-3 text-sm font-medium text-safe"><Sparkles className="h-4 w-4" /> Done: it now reads like a genuine message. That is exactly what to look for next time.</p>}
          <div className="mt-5 flex flex-wrap gap-3">
            <button type="button" disabled={busy || !data?.steps.length} onClick={() => { setText(start); setSolution(0); }}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
              <Wand2 className="h-4 w-4" /> Show me how
            </button>
            <button type="button" disabled={busy} onClick={() => { setFixed([]); setSolution(-1); void load(start, true); }}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm disabled:opacity-50">
              <RotateCcw className="h-4 w-4" /> Start again
            </button>
            {busy && <Loader2 className="h-4 w-4 animate-spin self-center text-muted-foreground" />}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5"><Meter score={shownScore} /></div>
          <div className="rounded-2xl border border-border bg-card p-5">
            <p className="text-sm font-semibold">What changed</p>
            <ol className="mt-3 space-y-2 text-sm">
              {(showingSolution ? data!.steps.slice(0, solution) : fixed).map((c, i) => (
                <li key={i} className="rounded-lg bg-muted/60 p-2.5">
                  <span className="block text-xs text-muted-foreground first-letter:uppercase">{c.label}</span>
                  <p><s className="text-destructive">{c.phrase}</s>{" → "}<span className="text-safe">{c.replacement || "removed"}</span>
                    {"score" in c && <span className="ml-2 font-mono text-xs text-muted-foreground">{pct((c as { score: number }).score)}%</span>}
                  </p>
                </li>
              ))}
              {!(showingSolution ? solution : fixed.length) && <li className="text-muted-foreground">Nothing yet.</li>}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
