"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { PublicShell } from "@/components/layout/public-shell";
import { ComparePanel } from "@/components/cross-domain/compare-panel";
import { getCrossDomainResults, type CdResults } from "@/lib/api/public";
import { cn } from "@/lib/utils";

const AdaptationChart = dynamic(() => import("@/components/cross-domain/adaptation-chart"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded bg-muted" aria-label="Loading chart" />,
});

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const f3 = (v: number) => v.toFixed(3);

function Step({ n, title, value, note, tone }: { n: number; title: string; value: string; note: string; tone?: "bad" | "good" }) {
  return (
    <div className="flex-1 rounded-xl border border-border p-4">
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">{n}</span>
        <p className="text-sm font-medium">{title}</p>
      </div>
      <p className={cn("mt-3 text-2xl font-bold tabular-nums", tone === "bad" ? "text-destructive" : tone === "good" ? "text-primary" : "")}>{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}

export default function CrossDomainPage() {
  const [study, setStudy] = useState<CdResults | null>(null);
  const [studyError, setStudyError] = useState<string | null>(null);

  useEffect(() => {
    getCrossDomainResults()
      .then(setStudy)
      .catch(() => setStudyError("Could not load the results. Refresh in a few seconds."));
  }, []);

  const lrA = study?.within_vs_cross.find((r) => r.Model === "Logistic Regression" && r["Test domain"] === "Source A");
  const lrB = study?.within_vs_cross.find((r) => r.Model === "Logistic Regression" && r["Test domain"] === "Target B");
  const lr10 = study?.adaptation_summary.find((r) => r.model === "logistic_regression" && r.feature === "word" && r.target_fraction === 0.1);
  const rowsA = Number(study?.dataset_statistics[0]?.["Rows after cleaning"] ?? 0);
  const rowsB = Number(study?.dataset_statistics[1]?.["Rows after cleaning"] ?? 0);
  const pool = rowsB - Math.round(rowsB * 0.3);
  const added10 = Math.floor(pool * 0.1);
  const dc = study?.domain_characteristics ?? [];
  const uk = dc.find((d) => d.Domain.startsWith("A"));
  const india = dc.find((d) => d.Domain === "B (India)");
  const indiaSpam = dc.find((d) => d.Domain === "B spam");

  return (
    <PublicShell>
      <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Cross-Domain SMS Spam Detection</h1>
      <p className="mt-2 text-sm text-muted-foreground">Source: UCI SMS Spam Collection (UK) · Target: Indian SMS</p>

      {studyError && <p className="mt-4 text-sm text-destructive">{studyError}</p>}
      {study && lrA && lrB && lr10 && (
        <section className="mt-6" aria-label="Summary">
          <div className="flex flex-col gap-3 md:flex-row">
            <Step n={1} title="Trained on UK SMS" value={f3(lrA["F1-score"])} note={`Spam F1, UK test set · ${rowsA.toLocaleString("en-IN")} messages`} />
            <Step n={2} title="Tested on Indian SMS" value={f3(lrB["F1-score"])} tone="bad" note={`Spam F1 · recall ${pct(lrB.Recall)} · ${rowsB.toLocaleString("en-IN")} messages`} />
            <Step n={3} title="Indian samples added" value={`+${added10}`} note={`10% of the ${pool.toLocaleString("en-IN")}-message labelled pool`} />
            <Step n={4} title="After adaptation" value={f3(lr10.B_f1_mean)} tone="good" note={`Spam F1, Indian test set · mean of ${study.seeds.length} seeds`} />
          </div>
        </section>
      )}

      <ComparePanel />

      {uk && india && indiaSpam && (
        <section className="mt-6 rounded-xl border border-border p-5">
          <h2 className="text-xl font-semibold">UK vs Indian SMS</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">Words the UK model never saw</p>
              <p className="mt-1 text-xl font-bold tabular-nums">{pct(uk["Mean share of words unseen in A-train"])} → {pct(india["Mean share of words unseen in A-train"])}</p>
              <p className="mt-1 text-xs text-muted-foreground">UK test messages vs Indian messages</p>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">Messages with a link</p>
              <p className="mt-1 text-xl font-bold tabular-nums">{pct(uk["Has URL"])} → {pct(indiaSpam["Has URL"])}</p>
              <p className="mt-1 text-xs text-muted-foreground">UK test messages vs Indian spam</p>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">Median length</p>
              <p className="mt-1 text-xl font-bold tabular-nums">{uk["Median length (chars)"]} → {india["Median length (chars)"]} chars</p>
              <p className="mt-1 text-xs text-muted-foreground">UK test messages vs Indian messages</p>
            </div>
          </div>
        </section>
      )}

      <h2 className="mt-10 text-xl font-semibold">Results</h2>
      {study && <p className="mt-1 text-sm text-muted-foreground">Mean over seeds {study.seeds.join(", ")}</p>}
      {!study && !studyError && <p className="mt-3 text-sm text-muted-foreground">Loading…</p>}

      {study && (
        <>
          <section className="mt-4 border border-border p-5">
            <h3 className="text-base font-semibold">Trained on UCI only: within-domain vs cross-domain</h3>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr><th className="py-1 pr-3">Model</th><th className="pr-3">Tested on</th><th className="pr-3">Accuracy</th><th className="pr-3">Precision</th><th className="pr-3">Recall</th><th>F1</th></tr>
                </thead>
                <tbody>
                  {study.within_vs_cross.map((r) => (
                    <tr key={`${r.Model}${r["Test domain"]}`} className="border-t border-border tabular-nums">
                      <td className="py-1 pr-3">{r.Model}</td>
                      <td className="pr-3">{r["Test domain"] === "Source A" ? "UCI test (same domain)" : "Indian SMS (new domain)"}</td>
                      <td className="pr-3">{pct(r.Accuracy)}</td><td className="pr-3">{pct(r.Precision)}</td><td className="pr-3">{pct(r.Recall)}</td>
                      <td className="font-semibold">{pct(r["F1-score"])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 border border-border p-5">
            <h3 className="text-base font-semibold">Adding labelled Indian messages: spam F1 on the Indian final test set</h3>
            <div className="mt-3 h-72"><AdaptationChart rows={study.adaptation_summary} /></div>
          </section>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section className="border border-border p-5">
              <h3 className="text-base font-semibold">Confusion matrices (seed 42, word TF-IDF)</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {study.confusion_seed42.map((c) => (
                  <div key={c["Evaluation setting"]}>
                    <p className="text-xs text-muted-foreground">{c["Evaluation setting"]}</p>
                    <table className="mt-1 w-full text-center text-sm tabular-nums">
                      <tbody>
                        <tr><td className="border border-border p-1 text-xs text-muted-foreground" /><td className="border border-border p-1 text-xs text-muted-foreground">pred ham</td><td className="border border-border p-1 text-xs text-muted-foreground">pred spam</td></tr>
                        <tr><td className="border border-border p-1 text-xs text-muted-foreground">true ham</td><td className="border border-border p-1">{c.TN}</td><td className="border border-border p-1">{c.FP}</td></tr>
                        <tr><td className="border border-border p-1 text-xs text-muted-foreground">true spam</td><td className="border border-border p-1">{c.FN}</td><td className="border border-border p-1">{c.TP}</td></tr>
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            </section>
            <section className="border border-border p-5">
              <h3 className="text-base font-semibold">Robustness: near-duplicates kept apart</h3>
              <p className="mt-1 text-xs text-muted-foreground">F1 when every near-duplicate group of Indian messages stays on one side of the split.</p>
              <table className="mt-3 w-full text-sm tabular-nums">
                <thead className="text-left text-xs text-muted-foreground">
                  <tr><th className="py-1 pr-3">Model</th><th className="pr-3">Indian data added</th><th className="pr-3">Random split</th><th>Group-aware split</th></tr>
                </thead>
                <tbody>
                  {study.group_aware.map((r) => (
                    <tr key={`${r.Model}${r["Target data added"]}`} className="border-t border-border">
                      <td className="py-1 pr-3">{r.Model}</td><td className="pr-3">{r["Target data added"]}</td>
                      <td className="pr-3">{r["F1, random split"]}</td><td>{r["F1, group-aware split"]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        </>
      )}

    </PublicShell>
  );
}
