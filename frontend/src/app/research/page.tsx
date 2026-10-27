"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { FlaskConical, RotateCcw } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Data: the deployed model's real scores on the 1,874-message test set */
/* (frontend/public/research/test_scores.json, written by               */
/*  backend/ml_training/research/export_web_results.py, which refuses   */
/*  to write unless it reproduces production_v4.json exactly).          */
/* ------------------------------------------------------------------ */

type Row = { t: string; y: 0 | 1; src: string; sub: string; p: number; f: number };
type Cell = "tp" | "fn" | "fp" | "tn";

const SUBTYPE: Record<string, string> = {
  reported_but_genuine: "Reported as scam, actually genuine",
  brand_promotion: "Brand promotion",
  personal_or_work: "Personal or work",
};

const pct = (v: number, d = 1) => `${(v * 100).toFixed(d)}%`;

function confusion(rows: Row[], key: "f" | "p", thr: number) {
  let tp = 0, fp = 0, fn = 0, tn = 0;
  for (const r of rows) {
    const flag = r[key] >= thr;
    if (r.y === 1) flag ? tp++ : fn++;
    else flag ? fp++ : tn++;
  }
  const n = tp + fp + fn + tn;
  return {
    tp, fp, fn, tn,
    accuracy: (tp + tn) / n,
    precision: tp + fp ? tp / (tp + fp) : 0,
    recall: tp / (tp + fn),
    fpr: fp / (fp + tn),
  };
}

/* ------------------------------------------------------------------ */
/* Score histogram: scams vs genuine messages, with the threshold line  */
/* ------------------------------------------------------------------ */
function Histogram({ rows, k, thr }: { rows: Row[]; k: "f" | "p"; thr: number }) {
  const BINS = 20;
  const scam = new Array(BINS).fill(0);
  const gen = new Array(BINS).fill(0);
  for (const r of rows) {
    const b = Math.min(BINS - 1, Math.floor(r[k] * BINS));
    (r.y ? scam : gen)[b]++;
  }
  // square-root scale so the small middle bins stay visible next to the big end bins
  const max = Math.sqrt(Math.max(...scam, ...gen));
  const W = 600, H = 170, bw = W / BINS;
  const h = (v: number) => (Math.sqrt(v) / max) * (H - 12);
  return (
    <svg viewBox={`0 0 ${W} ${H + 22}`} className="w-full" role="img" aria-label="Score distribution of scam and genuine test messages">
      {gen.map((v, i) => (
        <rect key={`g${i}`} x={i * bw + 2} y={H - h(v)} width={bw / 2 - 2} height={h(v)} className="fill-safe/80">
          <title>{`${v} genuine messages scored ${(i / BINS).toFixed(2)}–${((i + 1) / BINS).toFixed(2)}`}</title>
        </rect>
      ))}
      {scam.map((v, i) => (
        <rect key={`s${i}`} x={i * bw + bw / 2} y={H - h(v)} width={bw / 2 - 2} height={h(v)} className="fill-destructive/80">
          <title>{`${v} scam messages scored ${(i / BINS).toFixed(2)}–${((i + 1) / BINS).toFixed(2)}`}</title>
        </rect>
      ))}
      <line x1={0} x2={W} y1={H + 0.5} y2={H + 0.5} className="stroke-border" />
      <line x1={thr * W} x2={thr * W} y1={0} y2={H} className="stroke-foreground" strokeWidth={2} strokeDasharray="5 4" />
      <text x={Math.min(W - 4, Math.max(4, thr * W + 6))} y={12} textAnchor={thr > 0.8 ? "end" : "start"} className="fill-foreground text-[12px] font-semibold">
        threshold {thr.toFixed(2)}
      </text>
      {[0, 0.25, 0.5, 0.75, 1].map((x) => (
        <text key={x} x={x * W} y={H + 17} textAnchor={x === 0 ? "start" : x === 1 ? "end" : "middle"} className="fill-muted-foreground text-[11px]">
          {x.toFixed(2)}
        </text>
      ))}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Findings: the four results from the paper, as before/after bars      */
/* ------------------------------------------------------------------ */
const FINDINGS = [
  {
    title: "Label audit matters most",
    body: "19.5% of messages people reported as scams were genuine. Training on the raw reports makes the model flag a third of real bank and operator messages.",
    a: { label: "Trained on raw reports", value: 34.0 },
    b: { label: "Trained on audited labels", value: 2.6 },
    unit: "false alarms",
    lowerIsBetter: true,
    note: "McNemar test p < 10⁻³⁰ on the same 1,874 messages.",
  },
  {
    title: "Random splits flatter the model",
    body: "Scammers send the same campaign with small edits. A random split put near-copies of 793 test messages into training, so the test looked easier than it is.",
    a: { label: "Random row split", value: 0.8 },
    b: { label: "Campaign-aware split", value: 1.4 },
    unit: "false alarms",
    lowerIsBetter: true,
    note: "We report the harder, honest number: no campaign crosses train and test.",
  },
  {
    title: "Synthetic data covers new scam types",
    body: "Real reports lag behind new tricks. Adding labelled synthetic messages (training only, never tested on) teaches the 2025–26 scam types.",
    a: { label: "Real data only", value: 35.6 },
    b: { label: "Real + synthetic", value: 82.2 },
    unit: "recall on 2025–26 scam types",
    lowerIsBetter: false,
    note: "F1 on real messages stays at 98.1%.",
  },
  {
    title: "Rules explain, they don't add accuracy",
    body: "Hand-written intent rules looked strong on our own test messages, but on unseen real data they slightly lower F1. We keep them because they point at the exact phrases behind a verdict.",
    a: { label: "Classifier alone", value: 98.1 },
    b: { label: "With intent rules", value: 97.7 },
    unit: "F1 on unseen real data",
    lowerIsBetter: false,
    note: "An honest negative result, reported in the paper.",
  },
];

const MODELS = [
  { m: "Naive Bayes", f1: 95.5, fpr: 6.5 },
  { m: "Logistic regression", f1: 98.1, fpr: 2.6, chosen: true },
  { m: "Linear SVM", f1: 98.2, fpr: 3.9 },
  { m: "Random forest", f1: 97.6, fpr: 3.3 },
];

function Bar({ label, value, max, tone }: { label: string; value: number; max: number; tone: "bad" | "good" }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="font-mono font-semibold text-foreground">{value.toFixed(1)}%</span>
      </div>
      <div className="mt-1 h-2.5 overflow-hidden rounded-[999px] bg-muted">
        <div className={cn("h-full rounded-[999px]", tone === "good" ? "bg-safe" : "bg-destructive/80")} style={{ width: `${Math.max(2, (value / max) * 100)}%` }} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

export default function ResearchPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState(false);
  const [thr, setThr] = useState(0.5);
  const [key, setKey] = useState<"f" | "p">("f");
  const [open, setOpen] = useState<Cell | null>("fp");

  useEffect(() => {
    fetch("/research/test_scores.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setRows(d.rows))
      .catch(() => setError(true));
  }, []);

  const m = useMemo(() => (rows ? confusion(rows, key, thr) : null), [rows, key, thr]);

  const cellRows = useMemo(() => {
    if (!rows || !open) return [];
    return rows
      .filter((r) => {
        const flag = r[key] >= thr;
        return open === "tp" ? r.y && flag : open === "fn" ? r.y && !flag : open === "fp" ? !r.y && flag : !r.y && !flag;
      })
      .sort((a, b) => (open === "fp" || open === "tp" ? b[key] - a[key] : a[key] - b[key]));
  }, [rows, open, key, thr]);

  const fpBySubtype = useMemo(() => {
    if (open !== "fp") return null;
    const c: Record<string, number> = {};
    for (const r of cellRows) c[r.sub || r.src] = (c[r.sub || r.src] || 0) + 1;
    return Object.entries(c).sort((a, b) => b[1] - a[1]);
  }, [cellRows, open]);

  const isDefault = thr === 0.5 && key === "f";

  const CELLS: { id: Cell; label: string; hint: string; good: boolean }[] = [
    { id: "tp", label: "Scams caught", hint: "scam, flagged", good: true },
    { id: "fn", label: "Scams missed", hint: "scam, passed", good: false },
    { id: "fp", label: "False alarms", hint: "genuine, flagged", good: false },
    { id: "tn", label: "Genuine passed", hint: "genuine, passed", good: true },
  ];

  return (
    <PublicShell>
      <p className="flex items-center gap-2 text-xs text-primary">
        <FlaskConical className="h-3.5 w-3.5" /> Research Lab
      </p>
      <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">The paper&apos;s results, recomputed live in your browser</h1>
      <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
        These are the deployed model&apos;s real scores on all 1,874 held-out test messages of ScamGuard-IN-2026. Every message comes
        from a scam campaign the model never saw in training. Move the threshold, click any number, and read the actual messages
        behind it.
      </p>

      {error && <p className="mt-8 text-sm text-destructive">Could not load the test results. Refresh the page to try again.</p>}
      {!rows && !error && <div className="mt-8 h-72 animate-pulse rounded-xl bg-muted" aria-label="Loading test results" />}

      {rows && m && (
        <>
          {/* --------------------------------------------- controls + metrics */}
          <section className="mt-8 rounded-2xl border border-border bg-card p-5 md:p-7">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div role="radiogroup" aria-label="Which score" className="inline-flex overflow-hidden rounded-lg border border-border text-sm">
                {([["f", "Deployed system"], ["p", "Classifier alone"]] as const).map(([k, label]) => (
                  <button
                    key={k}
                    role="radio"
                    aria-checked={key === k}
                    onClick={() => setKey(k)}
                    className={cn("px-4 py-2", key === k ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {!isDefault && (
                <button onClick={() => { setThr(0.5); setKey("f"); }} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
                  <RotateCcw className="h-3.5 w-3.5" /> Back to the paper&apos;s setting
                </button>
              )}
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                ["Accuracy", m.accuracy, "right answers out of 1,874"],
                ["Precision", m.precision, "flagged messages that really were scams"],
                ["Recall", m.recall, "scams that were caught"],
                ["False alarms", m.fpr, "genuine messages wrongly flagged"],
              ].map(([label, v, hint]) => (
                <div key={label as string} className="rounded-xl border border-border bg-background p-4">
                  <p className="text-xs text-muted-foreground">{label as string}</p>
                  <p className={cn("mt-1 font-mono text-2xl font-semibold tabular-nums", label === "False alarms" && "text-destructive")}>{pct(v as number)}</p>
                  <p className="mt-1 text-[11px] leading-snug text-muted-foreground">{hint as string}</p>
                </div>
              ))}
            </div>

            <div className="mt-7">
              <label htmlFor="thr" className="flex items-baseline justify-between text-sm">
                <span className="font-medium">Decision threshold</span>
                <span className="font-mono tabular-nums">{thr.toFixed(2)}</span>
              </label>
              <input
                id="thr"
                type="range"
                min={0.05}
                max={0.95}
                step={0.01}
                value={thr}
                onChange={(e) => setThr(Number(e.target.value))}
                className="mt-2 w-full accent-[hsl(var(--primary))]"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                A message is flagged when its score is at or above the threshold. Higher means fewer false alarms but more missed scams.
                {isDefault && " This is the setting the paper reports and the website uses."}
              </p>
            </div>

            <div className="mt-6">
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-safe/80" /> genuine messages</span>
                <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-destructive/80" /> scam messages</span>
                <span>score from 0 (genuine) to 1 (scam); bar height on a square-root scale</span>
              </div>
              <Histogram rows={rows} k={key} thr={thr} />
            </div>
          </section>

          {/* --------------------------------------------- confusion matrix + drill-down */}
          <section className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
            <div className="rounded-2xl border border-border bg-card p-5">
              <h2 className="text-lg font-semibold">Confusion matrix</h2>
              <p className="mt-1 text-xs text-muted-foreground">Click a box to read those messages.</p>
              <div className="mt-4 grid grid-cols-[auto_1fr_1fr] gap-2 text-xs">
                <span />
                <span className="text-center text-muted-foreground">flagged as scam</span>
                <span className="text-center text-muted-foreground">passed as genuine</span>
                {(["scam", "genuine"] as const).map((rowLabel) => (
                  <div key={rowLabel} className="contents">
                    <span className="flex items-center pr-1 text-muted-foreground">really {rowLabel}</span>
                    {CELLS.filter((c) => (rowLabel === "scam" ? c.id === "tp" || c.id === "fn" : c.id === "fp" || c.id === "tn")).map((c) => (
                      <button
                        key={c.id}
                        onClick={() => setOpen(c.id)}
                        aria-pressed={open === c.id}
                        className={cn(
                          "rounded-xl border p-3 text-left transition-colors",
                          c.good ? "border-safe/30 bg-safe/10" : "border-destructive/30 bg-destructive/10",
                          open === c.id && "ring-2 ring-primary",
                        )}
                      >
                        <span className="block font-mono text-2xl font-semibold tabular-nums">{m[c.id].toLocaleString("en-IN")}</span>
                        <span className="block text-[11px] text-muted-foreground">{c.label}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Scoring speed: about 3.8 ms per message on a laptop CPU. Model size 1.6 MB.
              </p>
            </div>

            <div className="min-w-0 rounded-2xl border border-border bg-card p-5">
              {open && (
                <>
                  <h2 className="text-lg font-semibold">
                    {CELLS.find((c) => c.id === open)!.label}: {cellRows.length.toLocaleString("en-IN")} messages
                  </h2>
                  {fpBySubtype && fpBySubtype.length > 0 && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {fpBySubtype.map(([k, v], i) => (
                        <span key={k}>{i > 0 && "; "}<b className="text-foreground">{v}</b> {(SUBTYPE[k] || k).toLowerCase()}</span>
                      ))}
                      . Many of these genuine bank messages ask the user to click a link for KYC or a card, exactly like a scam would.
                    </p>
                  )}
                  {open === "fn" && <p className="mt-1 text-sm text-muted-foreground">Lowest-scoring scams first: these read most like a normal message.</p>}
                  <ul className="mt-4 max-h-[28rem] space-y-2 overflow-y-auto pr-1">
                    {cellRows.slice(0, 60).map((r, i) => (
                      <li key={i} className="rounded-lg border border-border bg-background p-3">
                        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                          <span className="font-mono font-semibold text-foreground">score {r[key].toFixed(2)}</span>
                          {r.sub && <span className="rounded bg-muted px-1.5 py-0.5">{SUBTYPE[r.sub] || r.sub.replace(/_/g, " ")}</span>}
                        </div>
                        <p className="mt-1.5 break-words text-sm leading-relaxed">{r.t}</p>
                      </li>
                    ))}
                  </ul>
                  {cellRows.length > 60 && <p className="mt-2 text-xs text-muted-foreground">Showing 60 of {cellRows.length.toLocaleString("en-IN")}.</p>}
                  <p className="mt-3 text-[11px] text-muted-foreground">Phone numbers, links and names in the corpus were replaced with tokens before release.</p>
                </>
              )}
            </div>
          </section>
        </>
      )}

      {/* --------------------------------------------- findings */}
      <section className="mt-14">
        <h2 className="text-2xl font-semibold tracking-tight">Four things we found</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">From the experiments in the paper, on the same real test set.</p>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {FINDINGS.map((f) => {
            const max = Math.max(f.a.value, f.b.value) * 1.05;
            const aGood = f.lowerIsBetter ? f.a.value < f.b.value : f.a.value > f.b.value;
            return (
              <article key={f.title} className="rounded-2xl border border-border bg-card p-5">
                <h3 className="font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
                <p className="mt-4 text-xs font-medium">{f.unit.charAt(0).toUpperCase() + f.unit.slice(1)}</p>
                <div className="mt-2 space-y-3">
                  <Bar label={f.a.label} value={f.a.value} max={max} tone={aGood ? "good" : "bad"} />
                  <Bar label={f.b.label} value={f.b.value} max={max} tone={aGood ? "bad" : "good"} />
                </div>
                <p className="mt-3 text-xs text-muted-foreground">{f.note}</p>
              </article>
            );
          })}
        </div>
      </section>

      {/* --------------------------------------------- model choice */}
      <section className="mt-14">
        <h2 className="text-2xl font-semibold tracking-tight">Why logistic regression</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Four models on the same word + character features. The SVM edges ahead on F1, but logistic regression has the fewest
          false alarms, and its word weights can be read directly, which is what powers the explanations on every result.
        </p>
        <div className="mt-5 overflow-x-auto rounded-2xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
              <tr><th className="px-4 py-2.5 font-medium">Model</th><th className="px-4 py-2.5 font-medium">F1</th><th className="px-4 py-2.5 font-medium">False alarms</th></tr>
            </thead>
            <tbody>
              {MODELS.map((r) => (
                <tr key={r.m} className={cn("border-t border-border", r.chosen && "bg-primary/10 font-semibold")}>
                  <td className="px-4 py-2.5">{r.m}{r.chosen && <span className="ml-2 rounded bg-primary px-1.5 py-0.5 text-[10px] text-primary-foreground">used</span>}</td>
                  <td className="px-4 py-2.5 font-mono tabular-nums">{r.f1.toFixed(1)}%</td>
                  <td className="px-4 py-2.5 font-mono tabular-nums">{r.fpr.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          Classifier alone, before the intent rules. Try the model yourself on the <Link href="/#quick-check" className="underline">quick check</Link>.
        </p>
      </section>
    </PublicShell>
  );
}
