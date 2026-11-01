"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { PublicShell } from "@/components/layout/public-shell";
import { Button } from "@/components/ui/button";
import {
  crossDomainClassify,
  getCrossDomainResults,
  type CdClassification,
  type CdClassifier,
  type CdResults,
  type CdVersion,
} from "@/lib/api/public";
import { cn } from "@/lib/utils";

const AdaptationChart = dynamic(() => import("@/components/cross-domain/adaptation-chart"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded bg-muted" aria-label="Loading chart" />,
});

const CLASSIFIERS: { id: CdClassifier; label: string }[] = [
  { id: "logistic_regression", label: "Logistic Regression" },
  { id: "naive_bayes", label: "Naive Bayes" },
];
const VERSIONS: { id: CdVersion; label: string; hint: string }[] = [
  { id: "baseline", label: "Baseline", hint: "trained on UCI (UK) SMS only" },
  { id: "adapted40", label: "Adapted", hint: "UCI + 40% of the labelled Indian pool" },
];
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

function Choice<T extends string>({ value, options, onChange, label }: {
  value: T; options: { id: T; label: string; hint?: string }[]; onChange: (v: T) => void; label: string;
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <div role="radiogroup" aria-label={label} className="mt-1 inline-flex border border-border">
        {options.map((o) => (
          <button
            key={o.id}
            role="radio"
            aria-checked={value === o.id}
            title={o.hint}
            onClick={() => onChange(o.id)}
            className={cn("px-3 py-2 text-sm", value === o.id ? "bg-primary text-primary-foreground" : "text-muted-foreground")}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function CrossDomainPage() {
  const [text, setText] = useState("");
  const [classifier, setClassifier] = useState<CdClassifier>("logistic_regression");
  const [version, setVersion] = useState<CdVersion>("adapted40");
  const [result, setResult] = useState<CdClassification | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [study, setStudy] = useState<CdResults | null>(null);
  const [studyError, setStudyError] = useState<string | null>(null);

  useEffect(() => {
    getCrossDomainResults()
      .then(setStudy)
      .catch(() => setStudyError("Could not load the study results. The server may be waking up; refresh in a few seconds."));
  }, []);

  async function classify() {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await crossDomainClassify(text, classifier, version));
    } catch {
      setError("Could not classify the message. Try again in a few seconds.");
    } finally {
      setBusy(false);
    }
  }

  const maxContribution = Math.max(0.0001, ...(result?.top_features.map((f) => Math.abs(f.contribution)) ?? [0]));

  return (
    <PublicShell>
      <p className="text-xs text-primary">Capstone research study</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Cross-Domain SMS Spam Detection System</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
        A spam classifier trained on UK messages (UCI SMS Spam Collection) is tested on Indian SMS, then adapted by adding a small
        labelled Indian sample. Try both versions on the same message. Spam = unwanted promotional or fraudulent SMS; ham = a normal
        message. Nothing you type is stored.
      </p>

      <section className="mt-6 border border-border p-5">
        <div className="flex flex-wrap gap-6">
          <Choice label="Classifier" value={classifier} options={CLASSIFIERS} onChange={(v) => { setClassifier(v); setResult(null); }} />
          <Choice label="Model version" value={version} options={VERSIONS} onChange={(v) => { setVersion(v); setResult(null); }} />
        </div>
        <label htmlFor="cd-text" className="mt-4 block text-sm font-medium">SMS message</label>
        <textarea
          id="cd-text"
          value={text}
          maxLength={2000}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="e.g. CONGRATULATIONS! FREE 2GB data is yours! Claim on the app now. Hurry i.airtel.in/e/..."
          className="mt-1 w-full border border-border bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <div className="mt-3 flex items-center gap-3">
          <Button onClick={classify} disabled={busy || !text.trim()}>{busy ? "Classifying…" : "Classify"}</Button>
          <span className="text-xs text-muted-foreground">{VERSIONS.find((v) => v.id === version)?.hint}</span>
        </div>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

        {result && (
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <div>
              <p className={cn("text-2xl font-semibold", result.label === "spam" ? "text-destructive" : "text-primary")}>
                {result.label === "spam" ? "SPAM" : "HAM"}
              </p>
              <p className="mt-1 text-sm">Probability of spam: <span className="font-semibold tabular-nums">{result.spam_probability.toFixed(3)}</span></p>
              <dl className="mt-3 space-y-1 text-xs text-muted-foreground">
                <div><dt className="inline">Model: </dt><dd className="inline font-mono">{result.model.id}</dd></div>
                <div><dt className="inline">Classifier: </dt><dd className="inline">{result.model.classifier}, {result.model.features}</dd></div>
                <div><dt className="inline">Version: </dt><dd className="inline">{result.model.version}</dd></div>
                {result.model.train_messages != null && (
                  <div><dt className="inline">Trained on: </dt><dd className="inline">{result.model.train_messages.toLocaleString("en-IN")} messages, seed {result.model.seed}</dd></div>
                )}
                {result.model.target_test_f1 != null && (
                  <div><dt className="inline">Spam F1 on the Indian final test set: </dt><dd className="inline">{result.model.target_test_f1.toFixed(3)}</dd></div>
                )}
              </dl>
            </div>
            <div>
              <p className="text-sm font-medium">Features behind this prediction</p>
              <p className="text-xs text-muted-foreground">Red pushes towards spam, blue towards ham.</p>
              {result.top_features.length === 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">None of the words in this message are in the model&apos;s vocabulary.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {result.top_features.map((f) => (
                    <li key={f.feature} className="grid grid-cols-[8rem_1fr_3.5rem] items-center gap-2 text-xs">
                      <span className="truncate font-mono" title={f.feature}>{f.feature}</span>
                      <span className="h-2 bg-muted">
                        <span
                          className={cn("block h-2", f.contribution > 0 ? "bg-destructive" : "bg-primary")}
                          style={{ width: `${(Math.abs(f.contribution) / maxContribution) * 100}%` }}
                        />
                      </span>
                      <span className="text-right tabular-nums">{f.contribution > 0 ? "+" : ""}{f.contribution.toFixed(3)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </section>

      <h2 className="mt-10 text-xl font-semibold">Experiment results</h2>
      <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
        Measured by the study notebook (research/cross_domain in the repository){study ? `; adaptation results are the mean over seeds ${study.seeds.join(", ")}` : ""}.
      </p>
      {studyError && <p className="mt-3 text-sm text-destructive">{studyError}</p>}
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
