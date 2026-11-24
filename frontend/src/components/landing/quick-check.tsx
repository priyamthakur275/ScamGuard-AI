"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { Loader2, ScanSearch, ShieldAlert, ShieldCheck, ShieldQuestion, Sparkles } from "lucide-react";
import { quickCheck } from "@/lib/api/public";
import { ApiError } from "@/lib/api/client";
import { Button, buttonVariants } from "@/components/ui/button";
import { ShareWarning, displayToken } from "@/components/analysis/share-warning";
import { ModelXray } from "@/components/analysis/model-xray";
import { MoreDetails } from "@/components/analysis/more-details";
import { ThreatCoreCanvas } from "@/components/visuals/threat-core-canvas";
import { cn, scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";
import { useLanguage } from "@/lib/i18n/language-context";
import { ReviewBand } from "@/components/analysis/review-band";
import { ScamXray, type XrayData } from "@/components/analysis/scam-xray";
import { WhatIf } from "@/components/analysis/what-if";
import { TrustLens } from "@/components/analysis/trust-lens";
import { analyzeWithCopilot } from "@/lib/copilot/stream";
import type { CragVerdict } from "@/lib/copilot/types";
import { RagVerdict } from "@/components/copilot/rag-verdict";
import { ErrorBoundary } from "@/components/error-boundary";

const SAMPLES = [
  {
    label: "SBI KYC scam",
    text: "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone.",
  },
  {
    label: "Fake job UPI",
    text: "Congratulations! Selected for part-time work. Earn Rs 5000 daily liking videos. Pay Rs 999 registration fee via UPI to activate your ID.",
  },
  {
    label: "Genuine bank alert",
    text: "Rs. 1,240.00 debited from A/c XX4821 on 24-11-26 to SWIGGY. Not you? Call 1800-1234 (official helpline). Never share your OTP with anyone.",
  },
];

interface QuickCheckProps {
  initialText?: string;
  autoRun?: boolean;
  heading?: string;
}

export function QuickCheck({ initialText = "", autoRun = false, heading }: QuickCheckProps = {}) {
  const { t } = useLanguage();
  const [text, setText] = useState(initialText);
  const autoRan = useRef(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [verdict, setVerdict] = useState<CragVerdict | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(value: string) {
    if (value.trim().length < 3) {
      setError(t("qc.short"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      try {
        const res = await analyzeWithCopilot(value.trim());
        setResult(res.analysis);
        setVerdict(res.verdict);
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 404)) throw err;
        setResult(await quickCheck(value.trim()));
        setVerdict(null);
      }
    } catch (err) {
      setResult(null);
      setVerdict(null);
      setError(err instanceof ApiError && err.status === 429 ? t("qc.busy") : t("qc.down"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (autoRun && initialText.trim().length >= 3 && !autoRan.current) {
      autoRan.current = true;
      void run(initialText);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRun, initialText]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void run(text);
  }

  const isScam = result && result.verdict !== "legitimate";
  const isSuspicious = Boolean(isScam && result && result.threat_score < 0.7);

  return (
    <section id="quick-check" className="border-t border-border px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6">
          <p className="console-kicker mb-2">Instant Inspection</p>
          <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{heading ?? t("qc.heading")}</h2>
          <p className="mt-1.5 text-sm text-muted-foreground">{t("qc.sub")}</p>
        </div>

        <div className={cn("scanner-panel p-5 sm:p-6", loading && "sg-scan-beam")}>
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <textarea
              aria-label="Message to check"
              value={text}
              maxLength={2000}
              rows={4}
              onChange={(e) => setText(e.target.value)}
              placeholder={t("qc.placeholder")}
              className="w-full resize-y border border-border bg-background/85 p-3.5 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    {t("qc.checking")}
                  </>
                ) : (
                  <>
                    <ScanSearch className="mr-2 h-4 w-4" aria-hidden="true" />
                    {t("qc.check")}
                  </>
                )}
              </Button>
              <span className="ml-1 hidden text-xs text-muted-foreground sm:inline">Examples:</span>
              {SAMPLES.map((sample) => (
                <button
                  key={sample.label}
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    setText(sample.text);
                    void run(sample.text);
                  }}
                  className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground disabled:opacity-50"
                >
                  <Sparkles className="h-3 w-3 text-primary" aria-hidden="true" />
                  {sample.label}
                </button>
              ))}
              <span className="ml-auto font-mono text-[11px] tabular-nums text-muted-foreground">
                {text.length}/2000
              </span>
            </div>
          </form>

          {loading && (
            <div
              role="status"
              aria-live="polite"
              className="mt-5 flex items-center gap-4 rounded-xl border border-primary/30 bg-primary/5 p-4"
            >
              <div className="h-14 w-14 shrink-0">
                <ThreatCoreCanvas mode="scanning" active />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">Running ScamGuard detection pipeline…</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Scoring text de-obfuscation, TF-IDF model probability, and Indian scam-intent signals.
                </p>
              </div>
            </div>
          )}

          {error && (
            <p role="alert" className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        {result && !loading && (
          <div
            className={cn(
              "verdict-heading mt-6 shadow-sm",
              !isScam && "data-safe",
            )}
            data-verdict={!isScam ? "safe" : isSuspicious ? "suspicious" : "scam"}
          >
            {verdict ? (
              <ErrorBoundary area="The result view">
                <RagVerdict verdict={verdict} />
              </ErrorBoundary>
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {!isScam ? (
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-safe/35 bg-safe/15 text-safe">
                        <ShieldCheck className="h-5 w-5" aria-hidden="true" />
                      </div>
                    ) : isSuspicious ? (
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-caution/35 bg-caution/15 text-caution">
                        <ShieldQuestion className="h-5 w-5" aria-hidden="true" />
                      </div>
                    ) : (
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-destructive/35 bg-destructive/15 text-destructive">
                        <ShieldAlert className="h-5 w-5" aria-hidden="true" />
                      </div>
                    )}
                    <div>
                      <p className="text-lg font-semibold text-foreground">
                        {isScam ? `${t("qc.scam")} · ${scamCategoryLabel(result.scam_category)}` : t("qc.safe")}
                      </p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {Math.round(result.threat_score * 100)}% {t("qc.likelihood")} · {t("qc.model")}{" "}
                        {Math.round(result.scam_probability * 100)}%
                      </p>
                    </div>
                  </div>
                </div>

                {!isScam && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    No strong scam indicators found, though automated checks are never a 100% guarantee. Never share OTPs or PINs.
                  </p>
                )}

                {result.top_contributing_tokens?.length > 0 && (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t("qc.signals")}:{" "}
                    <span className="font-mono text-xs text-foreground">
                      {result.top_contributing_tokens
                        .slice(0, 5)
                        .map((tok) => displayToken(tok.token))
                        .join(", ")}
                    </span>
                  </p>
                )}
              </>
            )}

            <ReviewBand threatScore={verdict ? verdict.fraud_index / 100 : result.threat_score} className="mt-4" />
            <div className="mt-4">
              <ScamXray compact xray={(result.metadata?.xray as XrayData | undefined) ?? null} />
            </div>
            <div className="mt-4">
              <TrustLens result={result} collapsible />
            </div>
            <div className="mt-4">
              <MoreDetails hint="What-if test and the model's exact maths for this message">
                <WhatIf result={result} />
                <ModelXray text={result.text} />
              </MoreDetails>
            </div>

            {((result.metadata?.community_reports as { display: string; report_count: number }[] | undefined) ?? []).map((c) => (
              <p key={c.display} className="mt-3 text-sm font-medium text-destructive">
                {c.display}: {t("qc.reported")} {c.report_count} {t("qc.users")}
              </p>
            ))}

            {!verdict && isScam && (result.recommended_actions?.length ?? 0) > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-foreground">
                {result.recommended_actions!.slice(0, 3).map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}

            <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-border pt-4">
              {isScam && <ShareWarning result={result} />}
              <Link href="/register" className={buttonVariants({ variant: "primary" })}>
                {t("qc.full")}
              </Link>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
