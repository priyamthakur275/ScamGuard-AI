"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { PublicShell } from "@/components/layout/public-shell";
import { ComparePanel } from "@/components/cross-domain/compare-panel";
import { getCrossDomainResults, type CdResults } from "@/lib/api/public";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const AdaptationChart = dynamic(() => import("@/components/cross-domain/adaptation-chart"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

type WorkbenchTab = "compare" | "shift" | "robustness";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const f3 = (v: number) => v.toFixed(3);

export default function CrossDomainPage() {
  const [study, setStudy] = useState<CdResults | null>(null);
  const [studyError, setStudyError] = useState<string | null>(null);
  const [tab, setTab] = useState<WorkbenchTab>("compare");

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
      <div className="border-b border-border pb-6">
        <p className="console-kicker">Research Benchmark</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">Cross-Domain SMS Spam Detection</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Model performance and domain adaptation from UK SMS (UCI) to Indian SMS.
        </p>
      </div>

      {studyError && (
        <p role="alert" className="mt-6 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {studyError}
        </p>
      )}

      {/* Panel 09 Top: 4-Stage Metric Strip */}
      {study && lrA && lrB && lr10 && (
        <section
          aria-label="Key experimental progression"
          className="console-panel mt-6 grid divide-y divide-border md:grid-cols-4 md:divide-x md:divide-y-0"
        >
          <div className="p-5">
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Trained (UK)</p>
            <p className="mt-2 font-mono text-2xl font-bold tabular-nums text-foreground">{f3(lrA["F1-score"])}</p>
            <p className="mt-1 text-xs text-muted-foreground">UK F1 ({rowsA.toLocaleString("en-IN")} msgs)</p>
          </div>
          <div className="p-5">
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Tested (IN)</p>
            <p className="mt-2 font-mono text-2xl font-bold tabular-nums text-destructive">{f3(lrB["F1-score"])}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Zero-shot recall {pct(lrB.Recall)} ({rowsB.toLocaleString("en-IN")} msgs)
            </p>
          </div>
          <div className="p-5">
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">IN Samples</p>
            <p className="mt-2 font-mono text-2xl font-bold tabular-nums text-foreground">+{added10}</p>
            <p className="mt-1 text-xs text-muted-foreground">10% of {pool.toLocaleString("en-IN")} pool</p>
          </div>
          <div className="p-5">
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">After Adaptation</p>
            <p className="mt-2 font-mono text-2xl font-bold tabular-nums text-primary">{f3(lr10.B_f1_mean)}</p>
            <p className="mt-1 text-xs text-muted-foreground">F1 mean ({study.seeds.length} seeds)</p>
          </div>
        </section>
      )}

      {/* Panel 09 Centerpiece: Model Comparison (Spam F1) Curve above the fold */}
      {!study && !studyError && (
        <div className="mt-6 space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      )}

      {study && (
        <section className="console-panel mt-6 p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-semibold text-foreground">Model Comparison (Spam F1)</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                F1 recovery on Indian test messages as labelled target samples increase (word vs character TF-IDF)
              </p>
            </div>
            <span className="font-mono text-[11px] text-muted-foreground">Seeds {study.seeds.join(", ")}</span>
          </div>
          <div className="mt-4 h-[280px] w-full min-w-0">
            <AdaptationChart rows={study.adaptation_summary} />
          </div>
        </section>
      )}

      {/* Interactive Workbench & Evidence Tabs */}
      <section className="mt-8 space-y-4" aria-label="Research workbench">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Research Workbench</h2>
            <p className="text-xs text-muted-foreground">Test baseline vs adapted predictions or inspect benchmark evidence</p>
          </div>
          <div role="tablist" aria-label="Workbench sections" className="inline-flex rounded-lg border border-border bg-muted/40 p-1">
            {(
              [
                ["compare", "Live Comparison"],
                ["shift", "Domain Shift"],
                ["robustness", "Matrices & Split"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                onClick={() => setTab(id)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  tab === id ? "bg-card text-primary shadow-sm ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {tab === "compare" && <ComparePanel />}

        {tab === "shift" && study && (
          <div className="space-y-5">
            {uk && india && indiaSpam && (
              <div className="console-panel grid divide-y divide-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                <div className="p-5">
                  <p className="text-xs text-muted-foreground">Out-of-vocabulary words</p>
                  <p className="mt-1.5 font-mono text-xl font-bold tabular-nums text-foreground">
                    {pct(uk["Mean share of words unseen in A-train"])} → {pct(india["Mean share of words unseen in A-train"])}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">UK test vs Indian SMS</p>
                </div>
                <div className="p-5">
                  <p className="text-xs text-muted-foreground">URL prevalence</p>
                  <p className="mt-1.5 font-mono text-xl font-bold tabular-nums text-foreground">
                    {pct(uk["Has URL"])} → {pct(indiaSpam["Has URL"])}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">UK test vs Indian spam</p>
                </div>
                <div className="p-5">
                  <p className="text-xs text-muted-foreground">Median message length</p>
                  <p className="mt-1.5 font-mono text-xl font-bold tabular-nums text-foreground">
                    {uk["Median length (chars)"]} → {india["Median length (chars)"]} chars
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">UK test vs Indian SMS</p>
                </div>
              </div>
            )}

            <div className="console-panel p-6">
              <h3 className="text-base font-semibold text-foreground">Zero-Shot Within-Domain vs Cross-Domain</h3>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border text-xs text-muted-foreground">
                    <tr>
                      <th className="py-2 pr-3">Model</th>
                      <th className="pr-3">Tested on</th>
                      <th className="pr-3">Accuracy</th>
                      <th className="pr-3">Precision</th>
                      <th className="pr-3">Recall</th>
                      <th>F1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {study.within_vs_cross.map((r) => (
                      <tr key={`${r.Model}${r["Test domain"]}`} className="border-b border-border/50 tabular-nums last:border-b-0">
                        <td className="py-2.5 pr-3 font-medium text-foreground">{r.Model}</td>
                        <td className="pr-3 text-muted-foreground">
                          {r["Test domain"] === "Source A" ? "UCI test (UK)" : "Indian SMS (cross-domain)"}
                        </td>
                        <td className="pr-3">{pct(r.Accuracy)}</td>
                        <td className="pr-3">{pct(r.Precision)}</td>
                        <td className="pr-3">{pct(r.Recall)}</td>
                        <td className="font-mono font-semibold text-primary">{pct(r["F1-score"])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {tab === "robustness" && study && (
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="console-panel p-6">
              <h3 className="text-base font-semibold text-foreground">Confusion Matrices (Seed 42 · Word TF-IDF)</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {study.confusion_seed42.map((c) => (
                  <div key={c["Evaluation setting"]}>
                    <p className="mb-1.5 text-xs font-medium text-muted-foreground">{c["Evaluation setting"]}</p>
                    <table className="w-full text-center text-xs tabular-nums">
                      <tbody>
                        <tr>
                          <td className="border border-border p-1.5 text-muted-foreground" />
                          <td className="border border-border p-1.5 text-muted-foreground">pred ham</td>
                          <td className="border border-border p-1.5 text-muted-foreground">pred spam</td>
                        </tr>
                        <tr>
                          <td className="border border-border p-1.5 text-muted-foreground">true ham</td>
                          <td className="border border-border p-1.5 font-mono text-foreground">{c.TN}</td>
                          <td className="border border-border p-1.5 font-mono text-destructive">{c.FP}</td>
                        </tr>
                        <tr>
                          <td className="border border-border p-1.5 text-muted-foreground">true spam</td>
                          <td className="border border-border p-1.5 font-mono text-caution">{c.FN}</td>
                          <td className="border border-border p-1.5 font-mono text-safe">{c.TP}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            </section>

            <section className="console-panel p-6">
              <h3 className="text-base font-semibold text-foreground">Near-Duplicate Split Robustness</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                F1 when near-duplicate Indian templates stay on one side of train/test splits.
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm tabular-nums">
                  <thead className="border-b border-border text-xs text-muted-foreground">
                    <tr>
                      <th className="py-2 pr-3">Model</th>
                      <th className="pr-3">Added data</th>
                      <th className="pr-3">Random split</th>
                      <th>Group-aware</th>
                    </tr>
                  </thead>
                  <tbody>
                    {study.group_aware.map((r) => (
                      <tr key={`${r.Model}${r["Target data added"]}`} className="border-b border-border/50 last:border-b-0">
                        <td className="py-2.5 pr-3 font-medium text-foreground">{r.Model}</td>
                        <td className="pr-3 text-muted-foreground">{r["Target data added"]}</td>
                        <td className="pr-3 font-mono">{r["F1, random split"]}</td>
                        <td className="font-mono font-semibold text-primary">{r["F1, group-aware split"]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </section>
    </PublicShell>
  );
}
