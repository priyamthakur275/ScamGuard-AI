"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createCase } from "@/lib/api/cases";
import { Alert } from "@/components/ui/alert";
import { ThreatLevelBadge } from "./threat-level-badge";
import { ShieldAlert, ShieldCheck, ThumbsDown, ThumbsUp, Sparkles, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { TokenChip } from "@/components/analysis/token-chip";
import { ScanSummary } from "@/components/analysis/scan-summary";
import { ConfidenceGauge } from "@/components/analysis/confidence-gauge";
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
import { Button } from "@/components/ui/button";
import { formatPercent, scamCategoryLabel, verdictLabel, inputTypeLabel } from "@/lib/utils";
import type { AnalysisResult, UrlIntelligence, EmailForensics, VoiceEvidenceSignal, CorrelationSignal } from "@/types";
import { motion, Variants } from "framer-motion";
import { ReportDownloadMenu } from "@/components/analysis/report-download-menu";

interface VerdictCardProps {
  result: AnalysisResult;
  onFeedback?: (isAccurate: boolean) => void;
}

const containerVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: "easeOut" },
  },
};

export function VerdictCard({ result, onFeedback }: VerdictCardProps) {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [caseError, setCaseError] = useState<string | null>(null);
  const isDemo = result.metadata?.is_demo === true;
  const severity = result.threat_level === "critical" ? "critical" : result.risk_level;
  const severityClass = { low: "text-risk-low", medium: "text-risk-medium", high: "text-risk-high", critical: "text-risk-critical" }[severity];
  async function handleCreateCase() {
    setCreating(true); setCaseError(null);
    try {
      const created = await createCase({ title: `${scamCategoryLabel(result.scam_category)} investigation`, severity, scan_ids: [result.id] });
      router.push(`/cases/${created.id}`);
    } catch { setCaseError("Could not create the case. Please try again."); }
    finally { setCreating(false); }
  }
  const isSafe = result.verdict === "legitimate";
  const maxWeight = Math.max(0, ...result.top_contributing_tokens.map((t) => t.weight));
  const hasExplainableData = Boolean(
    result.ai_explanation ||
    result.executive_summary ||
    result.technical_explanation ||
    result.risk_breakdown ||
    result.threat_level
  );

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      {/* Scan Summary Banner */}
      <ScanSummary result={result} />

      <Card className="console-panel overflow-hidden border border-border bg-card">
          <CardContent className="flex flex-col gap-8 p-5 md:p-8">

            {/* Header: verdict reads as a stamped case-file result, not a
                dashboard tile -- the stamp is the one bold element on this
                screen; everything else here stays quiet. */}
            <div className={`verdict-heading flex flex-col gap-8 xl:flex-row xl:items-start sm:justify-between ${isDemo ? "border-b border-border pb-8" : ""}`}>
              <div className="flex min-w-0 items-start gap-4">
                <div
                  className={`flex h-12 w-12 shrink-0 rounded-lg items-center justify-center border-2 font-mono ${
                    isSafe
                      ? "border-[hsl(var(--risk-very-low))] text-[hsl(var(--risk-very-low))]"
                      : `border-current ${severityClass}`
                  }`}
                >
                  {isSafe ? (
                    <ShieldCheck className="h-8 w-8" aria-hidden="true" />
                  ) : (
                    <ShieldAlert className="h-8 w-8" aria-hidden="true" />
                  )}
                </div>
                <div>
                  <p className="console-kicker flex flex-wrap items-center gap-2">
                    Verdict
                    <span className="border border-border px-1.5 py-0.5 text-[10px] normal-case tracking-normal text-foreground">
                      Source: {inputTypeLabel(result.input_type)}
                    </span>
                    {result.metadata?.is_demo === true && (
                      <span className="border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[10px] normal-case tracking-normal text-primary">
                        Demo example · not saved
                      </span>
                    )}
                  </p>
                  <h3 className="mt-2 text-4xl font-semibold tracking-tight text-foreground">
                    {verdictLabel(result.verdict)}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">{scamCategoryLabel(result.scam_category)}</p>
                  <div className="mt-3"><ThreatLevelBadge level={result.threat_level || result.risk_level} /></div>
                  <p className="mt-1.5 flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                    <Activity className="h-3.5 w-3.5" />
                    {formatPercent(result.scam_probability)} scam probability
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-6 sm:pt-1">
                <div className={`border-l border-current pl-5 ${severityClass}`}><p className="font-mono text-xs uppercase tracking-wider">Threat score</p><p className="mt-1 text-4xl font-semibold tracking-tight">{Math.round(result.threat_score * 100)}<span className="text-base text-muted-foreground"> / 100</span></p><p className="mt-1 text-xs text-muted-foreground">Calculated from observed signals</p></div>
                <ConfidenceGauge value={result.confidence_score} />

              </div>
            </div>

            {!isDemo && <div className="-mt-4 flex flex-wrap items-center gap-3 border-b border-border pb-6">
              <Button onClick={handleCreateCase} isLoading={creating}>Create case</Button>
              <Button variant="outline" onClick={() => document.getElementById(`copilot-${result.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}>Ask Copilot</Button>
              <ReportDownloadMenu kind="scan" id={result.id} />
            </div>}
            {caseError && <Alert variant="error">{caseError}</Alert>}
            {/* AI Explanation */}
            <AIExplanation
              explanation={result.ai_explanation}
              executiveSummary={result.executive_summary}
              technicalExplanation={result.technical_explanation}
            />

            <div className="evidence-grid">
            {/* Risk Breakdown */}
            {hasExplainableData && <RiskBreakdown breakdown={result.risk_breakdown} />}

            {/* Entity Highlights */}
            <EntityHighlights entities={result.highlighted_entities} />

            {/* URL intelligence -- real, computed signals; only for URL scans that have them */}
            <ThreatIntelligence urlIntelligence={(result.metadata?.url_intelligence as UrlIntelligence | undefined) ?? null} />

            {/* Email forensics -- header/content/attachment/URL evidence for EMAIL scans */}
            <EmailForensicsPanel forensics={(result.metadata?.email_forensics as EmailForensics | undefined) ?? null} />

            {/* Voice-call signals -- for VOICE scans */}
            <VoiceSignalsPanel voiceEvidence={(result.metadata?.voice_evidence as VoiceEvidenceSignal[] | undefined) ?? null} />

            {/* Correlation with the user's own past scans -- never external threat-intel */}
            <CorrelationPanel correlation={(result.metadata?.correlation as CorrelationSignal[] | undefined) ?? null} />

            </div>

            {/* Evidence-grounded Copilot Q&A -- only for persisted (non-demo) scans, since it needs a real prediction_id */}
            {!result.metadata?.is_demo && <div id={`copilot-${result.id}`}><CopilotPanel predictionId={result.id} /></div>}

            {/* Suspicious Keywords */}
            {result.top_contributing_tokens.length > 0 && (
              <div className="rounded-lg border border-border bg-background/40 p-5">
                <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
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

            {/* Recommended Actions */}
            <RecommendedActions actions={result.recommended_actions} />

            {/* Similar Patterns */}
            <SimilarPatterns patterns={result.similar_patterns} category={result.scam_category} />

            {/* Model info + Feedback */}
            <div className="flex flex-wrap gap-4 items-center justify-between border-t border-border pt-6">
              <p className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
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

            {/* Realistic Safety Disclaimer */}
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
