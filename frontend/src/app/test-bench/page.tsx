"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { CheckCircle2, ChevronDown, FileText, RefreshCw, XCircle } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { getTestBench, type TestBench, type TestBenchCase } from "@/lib/api/public";
import { cn, inputTypeLabel, scamCategoryLabel } from "@/lib/utils";

const pct = (v?: number) => (typeof v === "number" ? `${Math.round(v * 100)}%` : "–");

function InputPreview({ c }: { c: TestBenchCase }) {
  if (c.input_file) {
    const href = `/test-bench/${c.input_file}`;
    if (c.input_file.endsWith(".pdf")) {
      return (
        <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-primary underline">
          <FileText className="h-4 w-4" /> Open the PDF ({c.input_file})
        </a>
      );
    }
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <a href={href} target="_blank" rel="noreferrer"><img src={href} alt={c.title} className="max-h-72 border border-border" /></a>
    );
  }
  return <pre className="whitespace-pre-wrap break-words border border-border bg-muted/40 p-3 font-mono text-xs leading-5">{c.input_text}</pre>;
}

export default function TestBenchPage() {
  const [data, setData] = useState<TestBench | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);

  const load = useCallback((fresh: boolean) => {
    setBusy(true);
    setError(null);
    getTestBench(fresh)
      .then(setData)
      .catch(() => setError("Could not run the test bench. The server may be waking up; try again in a few seconds."))
      .finally(() => setBusy(false));
  }, []);

  useEffect(() => load(false), [load]);

  return (
    <PublicShell>
      <p className="text-xs text-primary">Live evaluation</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Test bench</h1>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
        Fifteen fixed inputs, seven scams and eight genuine messages, across every channel ScamGuard accepts: text, links, emails,
        WhatsApp screenshots, PDFs, QR codes and call transcripts. They are run through the live model and risk engine on the server
        every time this page loads; nothing on this page is typed in by hand. The same scans are also in the demo account&apos;s history.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          onClick={() => load(true)}
          disabled={busy}
          className="inline-flex items-center gap-2 bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
        >
          <RefreshCw className={cn("h-4 w-4", busy && "animate-spin")} /> {busy ? "Running all 15…" : "Run all 15 again"}
        </button>
        {data && (
          <span className="text-xs text-muted-foreground">
            Model {data.model} · run {new Date(data.generated_at).toLocaleString("en-IN")}
          </span>
        )}
      </div>

      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}
      {!data && !error && <p className="mt-6 text-sm text-muted-foreground">Running the 15 inputs through the live model…</p>}

      {data && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-4">
            {[
              ["Correct", `${data.summary.correct} / ${data.summary.total}`],
              ["Accuracy", pct(data.summary.accuracy)],
              ["Precision", data.summary.precision.toFixed(2)],
              ["Recall", data.summary.recall.toFixed(2)],
            ].map(([label, value]) => (
              <div key={label} className="border border-border p-5">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Scams caught {data.summary.tp} of {data.summary.tp + data.summary.fn} · genuine messages passed {data.summary.tn} of{" "}
            {data.summary.tn + data.summary.fp} · false alarms {data.summary.fp} · missed scams {data.summary.fn}
          </p>

          <div className="mt-6 overflow-x-auto border border-border">
            <table className="w-full min-w-[900px] text-sm">
              <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="p-3">#</th>
                  <th className="p-3">Channel</th>
                  <th className="p-3">Input</th>
                  <th className="p-3">Expected</th>
                  <th className="p-3">Result</th>
                  <th className="p-3 text-right">Scam likelihood</th>
                  <th className="p-3 text-right">Model</th>
                  <th className="p-3">Scam type</th>
                  <th className="p-3">Pass</th>
                </tr>
              </thead>
              <tbody>
                {data.cases.map((c) => (
                  <Fragment key={c.id}>
                    <tr
                      className="cursor-pointer border-t border-border hover:bg-muted/30"
                      onClick={() => setOpen(open === c.id ? null : c.id)}
                      aria-expanded={open === c.id}
                    >
                      <td className="whitespace-nowrap p-3 tabular-nums">{c.id}</td>
                      <td className="whitespace-nowrap p-3">{inputTypeLabel(c.input_type).replace("Screenshot / image", "Screenshot")}</td>
                      <td className="p-3">
                        <span className="inline-flex items-center gap-1">
                          {c.title}
                          <ChevronDown className={cn("h-3.5 w-3.5 text-muted-foreground transition-transform", open === c.id && "rotate-180")} />
                        </span>
                      </td>
                      <td className="whitespace-nowrap p-3">{c.expected === "scam" ? "Scam" : "Genuine"}</td>
                      <td className={cn("whitespace-nowrap p-3 font-medium", c.verdict === "scam" ? "text-risk-critical" : c.verdict === "legitimate" ? "text-risk-low" : "text-destructive")}>
                        {c.verdict === "scam" ? "Scam" : c.verdict === "legitimate" ? "Genuine" : "Error"}
                      </td>
                      <td className="whitespace-nowrap p-3 text-right tabular-nums">{pct(c.scam_likelihood)}</td>
                      <td className="whitespace-nowrap p-3 text-right tabular-nums text-muted-foreground">{pct(c.model_probability)}</td>
                      <td className="p-3">{c.verdict === "scam" ? scamCategoryLabel(c.scam_category ?? null) : "–"}</td>
                      <td className="p-3">
                        {c.correct ? <CheckCircle2 className="h-5 w-5 text-risk-low" aria-label="pass" /> : <XCircle className="h-5 w-5 text-destructive" aria-label="fail" />}
                      </td>
                    </tr>
                    {open === c.id && (
                      <tr className="border-t border-border bg-muted/20">
                        <td colSpan={9} className="p-4">
                          <div className="grid gap-4 lg:grid-cols-2">
                            <div>
                              <p className="mb-2 text-xs font-medium text-muted-foreground">Input</p>
                              <InputPreview c={c} />
                            </div>
                            <div>
                              <p className="mb-2 text-xs font-medium text-muted-foreground">What ScamGuard read and decided</p>
                              {c.error ? (
                                <p className="text-sm text-destructive">{c.error}</p>
                              ) : (
                                <>
                                  <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words border border-border bg-background p-3 font-mono text-xs leading-5">{c.extracted_text}</pre>
                                  <p className="mt-2 text-sm">
                                    Risk level <b>{c.risk_level}</b> · confidence <b>{pct(c.confidence)}</b> · {c.seconds}s
                                  </p>
                                </>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Scam likelihood is the final score after the intent risk engine; a message is called a scam at 50% or more. &quot;Model&quot; is the
            machine learning model&apos;s own probability, shown separately so you can see when the risk engine changed its mind. Tap a row to see the
            input and the text ScamGuard extracted from it.
          </p>
        </>
      )}
    </PublicShell>
  );
}
