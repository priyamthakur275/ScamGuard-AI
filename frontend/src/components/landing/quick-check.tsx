"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { ScanSearch, ShieldAlert, ShieldCheck } from "lucide-react";
import { quickCheck } from "@/lib/api/public";
import { ApiError } from "@/lib/api/client";
import { Button, buttonVariants } from "@/components/ui/button";
import { ShareWarning, displayToken } from "@/components/analysis/share-warning";
import { cn, scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";
import { useLanguage } from "@/lib/i18n/language-context";
import { ScamXray, type XrayData } from "@/components/analysis/scam-xray";
import { WhatIf } from "@/components/analysis/what-if";
import { analyzeWithCopilot } from "@/lib/copilot/stream";
import type { CragVerdict } from "@/lib/copilot/types";
import { RagVerdict } from "@/components/copilot/rag-verdict";
import { ErrorBoundary } from "@/components/error-boundary";

const SAMPLE =
  "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone.";

/** No-login check on the landing page. Hits /public/quick-check, which
 * runs the same model + threat scorer but stores nothing. */
interface QuickCheckProps {
  /** Pre-filled text, e.g. a message shared from WhatsApp into the installed app. */
  initialText?: string;
  /** Run the check immediately when initialText is present. */
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
        // Older backend without the Copilot route: fall back to the plain quick check.
        if (!(err instanceof ApiError && err.status === 404)) throw err;
        setResult(await quickCheck(value.trim()));
        setVerdict(null);
      }
    } catch (err) {
      setResult(null);
      setVerdict(null);
      setError(
        err instanceof ApiError && err.status === 429
          ? t("qc.busy")
          : t("qc.down"),
      );
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

  return (
    <section id="quick-check" className="border-t border-border px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-bold tracking-tight text-foreground">{heading ?? t("qc.heading")}</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {t("qc.sub")}
        </p>

        <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3">
          <textarea
            aria-label="Message to check"
            value={text}
            maxLength={2000}
            rows={4}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("qc.placeholder")}
            className="w-full resize-y border border-border bg-background p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={loading}>
              <ScanSearch className="mr-2 h-4 w-4" />
              {loading ? t("qc.checking") : t("qc.check")}
            </Button>
            <button
              type="button"
              className="text-sm text-primary underline-offset-4 hover:underline"
              onClick={() => {
                setText(SAMPLE);
                void run(SAMPLE);
              }}
            >
              {t("qc.sample")}
            </button>
            <span className="ml-auto font-mono text-[11px] text-muted-foreground">{text.length}/2000</span>
          </div>
        </form>

        {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

        {result && (
          <div
            className={cn(
              "mt-6 border p-5",
              isScam ? "border-destructive/50 bg-destructive/5" : "border-risk-low/50 bg-risk-low/5",
            )}
          >
            {verdict ? (
              <ErrorBoundary area="The result view">
                <RagVerdict verdict={verdict} />
              </ErrorBoundary>
            ) : (
              <>
              <div className="flex items-center gap-2">
                {isScam ? (
                  <ShieldAlert className="h-5 w-5 text-destructive" />
                ) : (
                  <ShieldCheck className="h-5 w-5 text-emerald-600" />
                )}
                <p className="text-lg font-semibold text-foreground">
                  {isScam ? `${t("qc.scam")} · ${scamCategoryLabel(result.scam_category)}` : t("qc.safe")}
                </p>
              </div>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {Math.round(result.threat_score * 100)}% {t("qc.likelihood")} · {t("qc.model")}{" "}
                {Math.round(result.scam_probability * 100)}%
              </p>

              {result.top_contributing_tokens?.length > 0 && (
                <p className="mt-3 text-sm text-muted-foreground">
                  {t("qc.signals")}:{" "}
                  {result.top_contributing_tokens
                    .slice(0, 5)
                    .map((t) => displayToken(t.token))
                    .join(", ")}
                </p>
              )}
              </>
            )}

            <div className="mt-4">
              <ScamXray compact xray={(result.metadata?.xray as XrayData | undefined) ?? null} />
            </div>
            <div className="mt-4">
              <WhatIf result={result} />
            </div>

            {((result.metadata?.community_reports as { display: string; report_count: number }[] | undefined) ?? []).map((c) => (
              <p key={c.display} className="mt-2 text-sm font-medium text-destructive">
                {c.display}: {t("qc.reported")} {c.report_count} {t("qc.users")}
              </p>
            ))}

            {!verdict && isScam && (result.recommended_actions?.length ?? 0) > 0 && (
              <ul className="mt-3 list-disc pl-5 text-sm text-foreground">
                {result.recommended_actions!.slice(0, 3).map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
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
