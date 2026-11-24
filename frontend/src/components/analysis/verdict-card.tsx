"use client";

import { useState } from "react";
import { motion, Variants } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TokenChip } from "@/components/analysis/token-chip";
import { AIExplanation } from "@/components/analysis/ai-explanation";
import { RiskBreakdown } from "@/components/analysis/risk-breakdown";
import { EntityHighlights } from "@/components/analysis/entity-highlights";
import { ThreatIntelligence } from "@/components/analysis/threat-intelligence";
import { EmailForensicsPanel } from "@/components/analysis/email-forensics-panel";
import { VoiceSignalsPanel } from "@/components/analysis/voice-signals-panel";
import { CorrelationPanel } from "@/components/analysis/correlation-panel";
import { CopilotPanel } from "@/components/analysis/copilot-panel";
import { RecommendedActions } from "@/components/analysis/recommended-actions";
import { SimilarPatterns } from "@/components/analysis/similar-patterns";
import { CountUp } from "@/components/analysis/demo-polish";
import { CampaignFingerprint, GoldenHourButton, ScamForecast } from "@/components/analysis/protect-features";
import { ReportDownloadMenu } from "@/components/analysis/report-download-menu";
import { ShareWarning } from "@/components/analysis/share-warning";
import { ReportScam } from "@/components/analysis/report-scam";
import { ReviewBand } from "@/components/analysis/review-band";
import { ChatPanel } from "@/components/analysis/chat-panel";
import { ScamXray, type XrayData } from "@/components/analysis/scam-xray";
import { WhatIf } from "@/components/analysis/what-if";
import { TrustLens } from "@/components/analysis/trust-lens";
import { ModelXray } from "@/components/analysis/model-xray";
import { MoreDetails } from "@/components/analysis/more-details";
import { CommunityReports } from "@/components/analysis/community-reports";
import { formatPercent, inputTypeLabel, scamCategoryLabel, truncate } from "@/lib/utils";
import type { AnalysisResult, CorrelationSignal, EmailForensics, UrlIntelligence, VoiceEvidenceSignal } from "@/types";

interface VerdictCardProps {
  result: AnalysisResult;
  onFeedback?: (isAccurate: boolean) => void;
  onScanAnother?: () => void;
}

const containerVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: "easeOut" },
  },
};

function RiskScoreDonut({ score, tone }: { score: number; tone: "safe" | "suspicious" | "scam" }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  const r = 42;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const stroke =
    tone === "safe" ? "hsl(var(--safe))" : tone === "suspicious" ? "hsl(var(--caution))" : "hsl(var(--destructive))";

  return (
    <div className="relative flex h-28 w-28 shrink-0 items-center justify-center">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="8" opacity="0.65" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 6px ${stroke})` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <p className="font-display text-2xl font-bold leading-none tabular-nums text-foreground">
          <CountUp value={pct} />
          <span className="text-xs font-normal text-muted-foreground">/100</span>
        </p>
        <p className="mt-1 text-[10px] font-medium text-muted-foreground">Risk Score</p>
      </div>
    </div>
  );
}

export function VerdictCard({ result, onFeedback, onScanAnother }: VerdictCardProps) {
  const [copied, setCopied] = useState(false);
  const isDemo = result.metadata?.is_demo === true;
  const isSafe = result.verdict === "legitimate";
  const isHighOrCritical =
    result.threat_level === "critical" ||
    result.threat_level === "high" ||
    (!result.threat_level && result.risk_level === "high");
  const isSuspicious = !isSafe && !isHighOrCritical;
  const tone: "safe" | "suspicious" | "scam" = isSafe ? "safe" : isSuspicious ? "suspicious" : "scam";

  const maxWeight = Math.max(0, ...result.top_contributing_tokens.map((t) => t.weight));
  const hasExplainableData = Boolean(
    result.ai_explanation ||
      result.executive_summary ||
      result.technical_explanation ||
      result.risk_breakdown ||
      result.threat_level,
  );

  const badgeLabel =
    tone === "safe"
      ? "Looks Genuine"
      : tone === "suspicious"
      ? "Suspicious"
      : result.threat_level === "critical"
      ? "Critical Risk"
      : "High Risk";

  const badgeCls =
    tone === "safe"
      ? "bg-safe text-white"
      : tone === "suspicious"
      ? "bg-caution text-black"
      : "bg-destructive text-white";

  const headline =
    tone === "safe"
      ? "No strong scam signals detected"
      : tone === "suspicious"
      ? "Suspicious indicators detected — verify carefully"
      : result.input_type?.toUpperCase() === "URL"
      ? "This link is likely a Scam!"
      : "This message is likely a Scam!";

  const xray = (result.metadata?.xray as XrayData | undefined) ?? null;
  const flagReasons: string[] = [];
  if (result.executive_summary) flagReasons.push(result.executive_summary);
  if (xray?.spans?.length) {
    for (const span of xray.spans) {
      const reason = span.why || span.label;
      if (reason && !flagReasons.includes(reason)) {
        flagReasons.push(reason);
      }
      if (flagReasons.length >= 4) break;
    }
  }
  if (flagReasons.length === 0 && result.ai_explanation) flagReasons.push(result.ai_explanation);

  const urlIntel = result.metadata?.url_intelligence as UrlIntelligence | undefined;
  const displayTarget = (() => {
    if (urlIntel?.original_url) return urlIntel.original_url;
    if (result.text.startsWith("URL Target:")) {
      const stripped = result.text.slice("URL Target:".length).trim();
      const idx = stripped.indexOf(" Observed URL signals:");
      return idx >= 0 ? stripped.slice(0, idx).trim() : stripped;
    }
    return result.text;
  })();

  const handleCopyTarget = async () => {
    try {
      await navigator.clipboard.writeText(displayTarget);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard permission denied */
    }
  };

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="flex flex-col gap-6">
      {/* Top Result Header Bar (Reference Panel 4) */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Scan Result</h2>
          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-safe" aria-hidden="true" />
            Analysis complete · {(result.latency_ms / 1000).toFixed(2)}s · Source: {inputTypeLabel(result.input_type)}
            {isDemo && " · Demo example"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {onScanAnother && (
            <Button variant="outline" size="sm" onClick={onScanAnother}>
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              Scan Another
            </Button>
          )}
          {!isDemo && <ReportDownloadMenu kind="scan" id={result.id} />}
        </div>
      </div>

      <Card className="console-panel overflow-hidden">
        <CardContent className="flex flex-col gap-6 p-5 md:p-7">
          {/* Hero Verdict Banner (Reference Panel 4) */}
          <div
            data-verdict={tone}
            className="verdict-heading flex flex-col items-start justify-between gap-6 md:flex-row md:items-center"
          >
            <div className="flex min-w-0 flex-1 items-start gap-4 sm:gap-5">
              <div className="relative flex h-20 w-20 shrink-0 items-center justify-center">
                <div
                  aria-hidden="true"
                  className={`absolute inset-1 rounded-full border ${
                    tone === "safe"
                      ? "border-safe/35 bg-safe/10 shadow-[0_0_32px_-4px_rgba(34,197,94,0.55)]"
                      : tone === "suspicious"
                      ? "border-caution/40 bg-caution/10 shadow-[0_0_32px_-4px_rgba(245,158,11,0.5)]"
                      : "border-destructive/45 bg-destructive/15 shadow-[0_0_36px_-4px_rgba(239,68,68,0.65)]"
                  }`}
                />
                <div
                  aria-hidden="true"
                  className={`absolute inset-3 rounded-full border border-dashed ${
                    tone === "safe" ? "border-safe/40" : tone === "suspicious" ? "border-caution/40" : "border-destructive/45"
                  }`}
                />
                <span
                  className={`relative ${
                    tone === "safe" ? "text-safe" : tone === "suspicious" ? "text-caution" : "text-destructive"
                  }`}
                >
                  {tone === "safe" ? (
                    <ShieldCheck className="h-9 w-9" aria-hidden="true" />
                  ) : tone === "suspicious" ? (
                    <ShieldQuestion className="h-9 w-9" aria-hidden="true" />
                  ) : (
                    <AlertTriangle className="h-9 w-9" aria-hidden="true" />
                  )}
                </span>
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-semibold ${badgeCls}`}>
                    {badgeLabel}
                  </span>
                  {result.scam_category && (
                    <span className="rounded-md border border-border bg-background/60 px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                      {scamCategoryLabel(result.scam_category)}
                    </span>
                  )}
                </div>

                <h3 className="mt-2 font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                  {headline}
                </h3>

                <div className="mt-3 inline-flex max-w-full items-center gap-2 rounded-lg border border-border bg-background/80 px-3 py-1.5 font-mono text-xs text-muted-foreground">
                  <span className="truncate">{truncate(displayTarget, 74)}</span>
                  <button
                    type="button"
                    onClick={() => void handleCopyTarget()}
                    className="shrink-0 text-muted-foreground transition-colors hover:text-primary"
                    aria-label="Copy analyzed target"
                    title="Copy analyzed target"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-safe" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>

                <p className="mt-2.5 flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
                  <Activity className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  Confidence {formatPercent(result.confidence_score)} · Source: {inputTypeLabel(result.input_type)}
                </p>
              </div>
            </div>

            <RiskScoreDonut score={result.threat_score} tone={tone} />
          </div>

          <ReviewBand threatScore={result.threat_score} />

          {/* 2-Column Summary Row matching Reference Panel 4 (strictly real backend outputs) */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-border bg-background/55 p-5">
              <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <ShieldAlert
                  className={`h-4 w-4 ${tone === "safe" ? "text-safe" : tone === "suspicious" ? "text-caution" : "text-destructive"}`}
                  aria-hidden="true"
                />
                {tone === "safe" ? "Detection Summary" : "Why it's flagged?"}
              </p>
              {flagReasons.length > 0 ? (
                <ul className="mt-3 space-y-2 text-sm text-foreground/90">
                  {flagReasons.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span
                        className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                          tone === "safe" ? "bg-safe" : tone === "suspicious" ? "bg-caution" : "bg-destructive"
                        }`}
                        aria-hidden="true"
                      />
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  {tone === "safe"
                    ? "The classifier and intent engine did not detect scam patterns in this input."
                    : "Multiple scam-intent signals and model features contributed to this risk score."}
                </p>
              )}
              {result.top_contributing_tokens.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {result.top_contributing_tokens.slice(0, 6).map((tok) => (
                    <TokenChip key={tok.token} contribution={tok} maxWeight={maxWeight} />
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-background/55 p-5">
              <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <CheckCircle2 className="h-4 w-4 text-safe" aria-hidden="true" />
                Recommended Actions
              </p>
              {result.recommended_actions && result.recommended_actions.length > 0 ? (
                <ul className="mt-3 space-y-2 text-sm text-foreground/90">
                  {result.recommended_actions.slice(0, 4).map((action, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-safe" aria-hidden="true" />
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <ul className="mt-3 space-y-2 text-sm text-foreground/90">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-safe" aria-hidden="true" />
                    <span>Never share OTPs, UPI PINs, or remote screen access.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-safe" aria-hidden="true" />
                    <span>Verify sensitive requests via official bank or government apps.</span>
                  </li>
                </ul>
              )}
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-3 border-b border-border pb-5">
            {!isDemo && (
              <Button
                variant="outline"
                onClick={() => document.getElementById(`copilot-${result.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
              >
                Ask ScamGuard
              </Button>
            )}
            {result.verdict !== "legitimate" && <ShareWarning result={result} />}
            <GoldenHourButton result={result} />
          </div>

          <CampaignFingerprint result={result} />
          <ScamXray xray={xray} />
          <TrustLens result={result} />
          {result.verdict !== "legitimate" && <ReportScam result={result} />}

          <div className="evidence-grid">
            {hasExplainableData && <RiskBreakdown breakdown={result.risk_breakdown} />}
            <ChatPanel chat={(result.metadata?.chat as { incoming?: string[]; outgoing?: string[]; header?: string | null } | undefined) ?? null} />
            <CommunityReports result={result} />
            <EntityHighlights entities={result.highlighted_entities} />
            <ThreatIntelligence urlIntelligence={(result.metadata?.url_intelligence as UrlIntelligence | undefined) ?? null} />
            <EmailForensicsPanel forensics={(result.metadata?.email_forensics as EmailForensics | undefined) ?? null} />
            <VoiceSignalsPanel voiceEvidence={(result.metadata?.voice_evidence as VoiceEvidenceSignal[] | undefined) ?? null} />
            <CorrelationPanel correlation={(result.metadata?.correlation as CorrelationSignal[] | undefined) ?? null} />
          </div>

          <RecommendedActions actions={result.recommended_actions} />

          {!result.metadata?.is_demo && (
            <div id={`copilot-${result.id}`}>
              <CopilotPanel predictionId={result.id} />
            </div>
          )}

          <MoreDetails hint="Written explanation, what-if test, the model's maths and similar known scams">
            <AIExplanation
              explanation={result.ai_explanation}
              executiveSummary={result.executive_summary}
              technicalExplanation={result.technical_explanation}
            />
            <WhatIf result={result} />
            <ScamForecast result={result} />
            {result.top_contributing_tokens.length > 0 && (
              <div className="rounded-lg border border-border bg-background/40 p-5">
                <p className="mb-3 flex items-center gap-2 text-xs font-semibold text-foreground">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  Signals detected
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.top_contributing_tokens.map((contribution) => (
                    <TokenChip key={contribution.token} contribution={contribution} maxWeight={maxWeight} />
                  ))}
                </div>
              </div>
            )}
            <ModelXray text={result.text} />
            <SimilarPatterns patterns={result.similar_patterns} category={result.scam_category} />
          </MoreDetails>

          {/* Model info + Feedback */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6">
            <p className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
              </span>
              Scored by {result.model_name} ({result.model_version}) · {result.latency_ms.toFixed(1)} ms
            </p>

            {onFeedback && (
              <div className="flex items-center gap-2 print:hidden">
                <span className="font-mono text-xs text-muted-foreground">Accurate?</span>
                <Button
                  variant={result.user_feedback === true ? "primary" : "ghost"}
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => onFeedback(true)}
                  aria-label="Mark as accurate"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant={result.user_feedback === false ? "destructive" : "ghost"}
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => onFeedback(false)}
                  aria-label="Mark as inaccurate"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </div>

          <div className="pt-2 text-center">
            <p className="text-xs italic text-muted-foreground/80">
              Notice: ScamGuard provides an automated heuristic and statistical risk assessment. It should not be treated as an absolute guarantee of safety. Always verify sensitive communications via independent official channels.
            </p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
