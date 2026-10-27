"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, Loader2, Presentation, ShieldAlert, ShieldCheck, X } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { quickCheck } from "@/lib/api/public";
import { ScamXray, type XrayData } from "@/components/analysis/scam-xray";
import { ModelXray } from "@/components/analysis/model-xray";
import { ErrorBoundary } from "@/components/error-boundary";
import { cn, scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";

/* Each case shows one claim from the report, on the live model. Every
 * expected verdict was checked against the deployed model before adding. */
const CASES: { title: string; claim: string; text: string; expect: "scam" | "genuine" }[] = [
  {
    title: "A fake bank KYC message",
    claim: "The most common Indian scam: an urgent KYC update with a look-alike link.",
    text: "Dear Customer, your SBI YONO account will be blocked today. Update your KYC immediately: http://sbi-kyc-update.xyz/login",
    expect: "scam",
  },
  {
    title: "A genuine operator notice",
    claim: "Uses the same words as scams (report, SMS, OTP, PIN) but is real. Keyword filters flag it; ScamGuard passes it.",
    text: "Report unsolicited commercial communication (spam calls and SMS) to 1909. Never share your OTP or PIN with anyone. -Airtel",
    expect: "genuine",
  },
  {
    title: "A genuine bank OTP",
    claim: "Real OTP alerts mention money, a card and an OTP. Flagging them would teach people to ignore warnings.",
    text: "482913 is your OTP for a transaction of Rs 2,499.00 at AMAZON on your HDFC Bank card ending 4521. Do not share it with anyone.",
    expect: "genuine",
  },
  {
    title: "A scam in Hindi",
    claim: "Many scams arrive in Hindi. The model keeps Devanagari words and was trained on Hindi messages.",
    text: "प्रिय उपभोक्ता, आपका बिजली कनेक्शन आज रात 9:30 बजे काट दिया जाएगा क्योंकि पिछले महीने का बिल अपडेट नहीं हुआ है। तुरंत बिजली अधिकारी 9123456780 से संपर्क करें।",
    expect: "scam",
  },
  {
    title: "Misspelled to dodge filters",
    claim: "Scammers write bl0cked and K.Y.C so word lists miss them. Character patterns (2–5 letters) still catch it.",
    text: "Dear user ur a/c is bl0cked!! Upd8 your K.Y.C n0w at bit.ly/kyc-upd to avoid permanent suspensi0n",
    expect: "scam",
  },
  {
    title: "A 2025–26 'digital arrest' scam",
    claim: "A newer scam type. Labelled synthetic training data is what lets the model recognise it.",
    text: "This is CBI Mumbai. A parcel in your name contains illegal drugs. You are under digital arrest. Do not tell anyone. Transfer Rs 50,000 to the verification account for clearance.",
    expect: "scam",
  },
];

type State = { status: "idle" | "loading" | "done" | "error"; result?: AnalysisResult; error?: string };

export default function DemoPage() {
  const [step, setStep] = useState(0);
  const [runs, setRuns] = useState<Record<number, State>>({});
  const inFlight = useRef<Set<number>>(new Set());
  const c = CASES[step]!;
  const s = runs[step] ?? { status: "idle" };

  const run = useCallback(async (i: number) => {
    if (inFlight.current.has(i)) return;
    inFlight.current.add(i);
    setRuns((r) => ({ ...r, [i]: { status: "loading" } }));
    try {
      const result = await quickCheck(CASES[i]!.text);
      setRuns((r) => ({ ...r, [i]: { status: "done", result } }));
    } catch {
      setRuns((r) => ({ ...r, [i]: { status: "error", error: "The server didn't answer. It may be waking up: try again in a few seconds." } }));
    } finally {
      inFlight.current.delete(i);
    }
  }, []);

  // Run the current case on arrival, and quietly pre-run the next one so the
  // presenter never waits.
  useEffect(() => {
    if (!runs[step] || runs[step]?.status === "error") void run(step);
    if (step + 1 < CASES.length && !runs[step + 1]) void run(step + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input, textarea")) return;
      if (e.key === "ArrowRight") setStep((v) => Math.min(CASES.length - 1, v + 1));
      if (e.key === "ArrowLeft") setStep((v) => Math.max(0, v - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const res = s.result;
  const isScam = res ? res.verdict !== "legitimate" : false;
  const correct = res ? (isScam ? "scam" : "genuine") === c.expect : null;
  const doneCount = CASES.filter((cc, i) => {
    const r = runs[i]?.result;
    return r && (r.verdict !== "legitimate" ? "scam" : "genuine") === cc.expect;
  }).length;

  return (
    <PublicShell>
      <p className="flex items-center gap-2 text-xs text-primary"><Presentation className="h-3.5 w-3.5" /> Guided demo</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Six messages, six claims, one live model</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Each message tests one thing the project report claims. They run on the real deployed model as you watch. Use the arrow keys
        or the buttons to move between them.
      </p>

      <ol className="mt-6 flex flex-wrap gap-2" aria-label="Demo steps">
        {CASES.map((cc, i) => {
          const r = runs[i]?.result;
          const ok = r ? (r.verdict !== "legitimate" ? "scam" : "genuine") === cc.expect : null;
          return (
            <li key={cc.title}>
              <button
                onClick={() => setStep(i)}
                aria-current={i === step ? "step" : undefined}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-[999px] border px-3 py-1.5 text-xs transition-colors",
                  i === step ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                <span className="font-mono">{i + 1}</span>
                <span className="hidden sm:inline">{cc.title}</span>
                {ok === true && <Check className="h-3 w-3" />}
                {ok === false && <X className="h-3 w-3" />}
              </button>
            </li>
          );
        })}
      </ol>

      <section className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold">{step + 1}. {c.title}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{c.claim}</p>
          <div className="mt-4 rounded-2xl rounded-tl-sm border border-border bg-card p-4 text-sm leading-relaxed shadow-sm">
            {c.text}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Expected: <b className="text-foreground">{c.expect === "scam" ? "Scam" : "Genuine"}</b>
          </p>
          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={() => setStep((v) => Math.max(0, v - 1))}
              disabled={step === 0}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm disabled:opacity-40"
            >
              <ArrowLeft className="h-4 w-4" /> Previous
            </button>
            {step < CASES.length - 1 ? (
              <button onClick={() => setStep((v) => v + 1)} className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
                Next <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <Link href="/research" className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
                See the full test results <ArrowRight className="h-4 w-4" />
              </Link>
            )}
            <span className="ml-auto text-xs text-muted-foreground">{doneCount} of {CASES.length} correct so far</span>
          </div>
        </div>

        <div className="min-w-0 space-y-4" aria-live="polite">
          {(s.status === "loading" || s.status === "idle") && (
            <div className="flex h-40 items-center justify-center gap-2 rounded-2xl border border-border bg-card text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Checking with the live model…
            </div>
          )}
          {s.status === "error" && (
            <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-5 text-sm">
              <p>{s.error}</p>
              <button onClick={() => void run(step)} className="mt-3 rounded-md border border-border px-3 py-1.5 text-sm">Try again</button>
            </div>
          )}
          {res && (
            <ErrorBoundary area="The demo result">
              <div className={cn("rounded-2xl border p-5", isScam ? "border-destructive/50 bg-destructive/5" : "border-safe/50 bg-safe/5")}>
                <div className="flex flex-wrap items-center gap-3">
                  {isScam ? <ShieldAlert className="h-6 w-6 text-destructive" /> : <ShieldCheck className="h-6 w-6 text-safe" />}
                  <p className="text-xl font-semibold">
                    {isScam ? `Scam${res.scam_category ? ` · ${scamCategoryLabel(res.scam_category)}` : ""}` : "Looks genuine"}
                  </p>
                  {correct !== null && (
                    <span className={cn("ml-auto rounded-[999px] px-2.5 py-1 text-xs font-medium", correct ? "bg-safe/15 text-safe" : "bg-destructive/15 text-destructive")}>
                      {correct ? "As expected" : "Not as expected"}
                    </span>
                  )}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-background/70 p-3">
                    <p className="text-[11px] text-muted-foreground">Final risk score</p>
                    <p className="font-mono text-2xl font-semibold tabular-nums">{Math.round(res.threat_score * 100)}%</p>
                  </div>
                  <div className="rounded-lg bg-background/70 p-3">
                    <p className="text-[11px] text-muted-foreground">Classifier alone</p>
                    <p className="font-mono text-2xl font-semibold tabular-nums">{Math.round(res.scam_probability * 100)}%</p>
                  </div>
                </div>
                <div className="mt-4">
                  <ScamXray compact xray={(res.metadata?.xray as XrayData | undefined) ?? null} />
                </div>
              </div>
              <ModelXray text={c.text} autoOpen />
            </ErrorBoundary>
          )}
        </div>
      </section>
    </PublicShell>
  );
}
