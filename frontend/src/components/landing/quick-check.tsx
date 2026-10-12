"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ScanSearch, ShieldAlert, ShieldCheck } from "lucide-react";
import { quickCheck } from "@/lib/api/public";
import { ApiError } from "@/lib/api/client";
import { Button, buttonVariants } from "@/components/ui/button";
import { ShareWarning, displayToken } from "@/components/analysis/share-warning";
import { cn, scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";

const SAMPLE =
  "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone.";

/** No-login check on the landing page. Hits /public/quick-check, which
 * runs the same model + threat scorer but stores nothing. */
export function QuickCheck() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(value: string) {
    if (value.trim().length < 3) {
      setError("Paste a message of at least a few characters.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await quickCheck(value.trim()));
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiError && err.status === 429
          ? "Too many quick checks. Sign in for unlimited scans, or try again in a minute."
          : "Could not reach the server. It may be waking up; try again in a few seconds.",
      );
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void run(text);
  }

  const isScam = result && result.verdict !== "legitimate";

  return (
    <section id="quick-check" className="border-t border-border px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-bold tracking-tight text-foreground">Got a suspicious message? Paste it here.</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Quick check, no account needed. Nothing you paste here is saved.
        </p>

        <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3">
          <textarea
            aria-label="Message to check"
            value={text}
            maxLength={2000}
            rows={4}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste an SMS, WhatsApp message or email text..."
            className="w-full resize-y border border-border bg-background p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={loading}>
              <ScanSearch className="mr-2 h-4 w-4" />
              {loading ? "Checking..." : "Check message"}
            </Button>
            <button
              type="button"
              className="text-sm text-primary underline-offset-4 hover:underline"
              onClick={() => {
                setText(SAMPLE);
                void run(SAMPLE);
              }}
            >
              Try a sample scam
            </button>
            <span className="ml-auto font-mono text-[11px] text-muted-foreground">{text.length}/2000</span>
          </div>
        </form>

        {error && <p className="mt-4 text-sm text-destructive">{error}</p>}

        {result && (
          <div
            className={cn(
              "mt-6 border p-5",
              isScam ? "border-destructive/50 bg-destructive/5" : "border-emerald-500/50 bg-emerald-500/5",
            )}
          >
            <div className="flex items-center gap-2">
              {isScam ? (
                <ShieldAlert className="h-5 w-5 text-destructive" />
              ) : (
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
              )}
              <p className="text-lg font-semibold text-foreground">
                {isScam ? `Likely scam · ${scamCategoryLabel(result.scam_category)}` : "Looks legitimate"}
              </p>
            </div>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              Threat score {Math.round(result.threat_score * 100)}% · model probability{" "}
              {Math.round(result.scam_probability * 100)}%
            </p>

            {result.top_contributing_tokens?.length > 0 && (
              <p className="mt-3 text-sm text-muted-foreground">
                Signals:{" "}
                {result.top_contributing_tokens
                  .slice(0, 5)
                  .map((t) => displayToken(t.token))
                  .join(", ")}
              </p>
            )}

            {isScam && (result.recommended_actions?.length ?? 0) > 0 && (
              <ul className="mt-3 list-disc pl-5 text-sm text-foreground">
                {result.recommended_actions!.slice(0, 3).map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              {isScam && <ShareWarning result={result} />}
              <Link href="/register" className={buttonVariants({ variant: "primary" })}>
                Get the full analysis
              </Link>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
