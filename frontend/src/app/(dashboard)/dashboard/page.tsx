"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Eye,
  RefreshCw,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import { motion } from "framer-motion";
import { getAnalyticsSummary } from "@/lib/api/analytics";
import { getHistory } from "@/lib/api/messages";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { ThreatBadge } from "@/components/analysis/risk-badge";
import { StatCard } from "@/components/analytics/stat-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { formatDate, formatPercent, scamCategoryLabel, truncate, verdictLabel } from "@/lib/utils";
import type { AnalysisResult, AnalyticsSummary } from "@/types";
import { PhoneLookup } from "@/components/dashboard/phone-lookup";

const ChartSkeleton = () => <Skeleton className="h-64 w-full" />;

const ThreatDistributionPieChart = dynamic(
  () => import("@/components/analytics/threat-distribution-pie-chart").then((m) => m.ThreatDistributionPieChart),
  { ssr: false, loading: ChartSkeleton },
);

const RiskTrendChart = dynamic(
  () => import("@/components/analytics/risk-trend-chart").then((m) => m.RiskTrendChart),
  { ssr: false, loading: ChartSkeleton },
);

function isHighRisk(entry: AnalysisResult): boolean {
  return (
    entry.threat_level === "high" ||
    entry.threat_level === "critical" ||
    (!entry.threat_level && entry.risk_level === "high")
  );
}

export default function DashboardPage() {
  const [entries, setEntries] = useState<AnalysisResult[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<AnalysisResult | null>(null);

  const loadDashboard = useCallback(async (refresh = false) => {
    if (refresh) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);
    try {
      const [historyData, summaryData] = await Promise.all([
        getHistory(0, 50),
        getAnalyticsSummary("all").catch(() => null),
      ]);
      setEntries(historyData);
      setSummary(summaryData);
    } catch {
      setError("Could not load your threat overview. Please try again.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard(false);
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedFinding) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedFinding(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedFinding]);

  // Metrics derived strictly from server-side analytics (falling back to loaded history if summary unavailable)
  const totalScans = summary?.total_scans ?? entries.length;
  const safeCount =
    summary?.verdict_distribution?.legitimate ??
    entries.filter((e) => e.verdict === "legitimate").length;
  const highRiskCount = summary?.high_risk_count ?? entries.filter(isHighRisk).length;
  const flaggedCount = summary
    ? Object.entries(summary.verdict_distribution)
        .filter(([verdict]) => verdict !== "legitimate")
        .reduce((acc, [, count]) => acc + count, 0)
    : entries.filter((e) => e.verdict !== "legitimate").length;
  const suspiciousCount = Math.max(0, flaggedCount - highRiskCount);
  const detectionRate = totalScans > 0 ? flaggedCount / totalScans : 0;

  const allHighPriority = entries.filter(isHighRisk);
  const highPriority = allHighPriority.slice(0, 5);
  const recentEntries = entries.slice(0, 8);

  const indicatorCounts = new Map<string, number>();
  entries.forEach((entry) => {
    new Set(Object.values(entry.highlighted_entities ?? {}).flat()).forEach((value) => {
      if (value) indicatorCounts.set(value, (indicatorCounts.get(value) ?? 0) + 1);
    });
  });
  const recurringIndicators = Array.from(indicatorCounts.entries())
    .filter(([, count]) => count > 1)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <div className="sg-page flex flex-col gap-7">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="console-kicker mb-1.5">Threat Operations Center</p>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Threat overview
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted-foreground">
            Live detection telemetry, priority findings, and recurring threat indicators across your workspace.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadDashboard(true)}
            disabled={isLoading || isRefreshing}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Link href="/analyze" className={buttonVariants({ size: "md" })}>
            <ScanSearch className="h-4 w-4" />
            New investigation
          </Link>
        </div>
      </div>

      {error && (
        <Alert variant="error">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => void loadDashboard(true)}>
              Retry
            </Button>
          </div>
        </Alert>
      )}

      {/* KPI Strip */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5"
        >
          <StatCard
            label="Total scans"
            value={String(totalScans)}
            subtitle="All-time analyzed"
            icon={ScanSearch}
          />
          <StatCard
            label="Safe detections"
            value={String(safeCount)}
            subtitle="Verified legitimate"
            icon={CheckCircle2}
            accent="success"
          />
          <StatCard
            label="Suspicious"
            value={String(suspiciousCount)}
            subtitle="Review recommended"
            icon={AlertTriangle}
            accent="warning"
          />
          <StatCard
            label="High risk"
            value={String(highRiskCount)}
            subtitle="Immediate action"
            icon={ShieldAlert}
            accent="destructive"
          />
          <StatCard
            label="Detection rate"
            value={formatPercent(detectionRate)}
            subtitle={`${flaggedCount} of ${totalScans} flagged`}
            icon={Activity}
          />
        </motion.div>
      )}

      {/* Priority Findings + Threat Analytics */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      ) : (
        <>
          <Card className="console-panel min-w-0 overflow-hidden">
            <CardHeader className="flex-col gap-2 border-b border-border bg-card/60 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-lg">Priority findings</CardTitle>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  High and critical risk detections requiring review.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-muted-foreground">
                  {allHighPriority.length > highPriority.length
                    ? `Showing ${highPriority.length} of ${allHighPriority.length}`
                    : `${allHighPriority.length} high-risk ${allHighPriority.length === 1 ? "finding" : "findings"}`}
                </span>
                <Link href="/history" className="text-xs font-medium text-primary hover:underline">
                  All history
                </Link>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {highPriority.length === 0 ? (
                <EmptyState
                  icon={ShieldCheck}
                  title="No high-risk findings"
                  description="New high-risk results will appear here as soon as they are detected."
                  actionHref="/analyze"
                  actionLabel="Start an investigation"
                />
              ) : (
                <ul className="divide-y divide-border">
                  {highPriority.map((entry) => (
                    <li
                      key={entry.id}
                      className="flex flex-col gap-3 px-4 py-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:gap-4 sm:px-6"
                    >
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-risk-high/25 bg-risk-high/10 text-risk-high">
                          <AlertTriangle className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-foreground">
                            {truncate(entry.text, 92)}
                          </p>
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] text-muted-foreground">
                            <span className="text-foreground/85">{verdictLabel(entry.verdict)}</span>
                            {entry.scam_category && (
                              <>
                                <span>·</span>
                                <span>{scamCategoryLabel(entry.scam_category)}</span>
                              </>
                            )}
                            {entry.input_type && (
                              <>
                                <span>·</span>
                                <span className="uppercase">{entry.input_type}</span>
                              </>
                            )}
                            <span>·</span>
                            <span>Score {formatPercent(entry.threat_score)}</span>
                            <span>·</span>
                            <span>{formatDate(entry.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center justify-between gap-2.5 sm:justify-end">
                        <ThreatBadge threatLevel={entry.threat_level} riskLevel={entry.risk_level} />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedFinding(entry)}
                          aria-label="Inspect finding"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          Inspect
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {/* Threat Analytics — strictly rendered from real data */}
          {summary && summary.total_scans > 0 && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold tracking-tight text-foreground">Threat analytics</h2>
                  <p className="text-xs text-muted-foreground">
                    Distribution and recent risk trajectory from your actual scan history.
                  </p>
                </div>
                <Link
                  href="/analytics"
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  Full analytics
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <ThreatDistributionPieChart distribution={summary.verdict_distribution} />
                <RiskTrendChart entries={entries.slice(0, 30)} />
              </div>
            </div>
          )}

          {/* Recent Scan Activity + Sidebar Widgets */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
            <Card className="console-panel min-w-0 overflow-hidden">
              <CardHeader className="flex-row items-center justify-between border-b border-border bg-card/60">
                <div>
                  <CardTitle className="text-lg">Recent scan activity</CardTitle>
                  <p className="mt-0.5 text-xs text-muted-foreground">Latest messages, URLs, and artifacts inspected.</p>
                </div>
                <Link href="/history" className="text-xs font-medium text-primary hover:underline">
                  View all
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {recentEntries.length === 0 ? (
                  <EmptyState
                    icon={ScanSearch}
                    title="No activity yet"
                    description="Analyze your first message, link, or screenshot to populate your feed."
                    actionHref="/analyze"
                    actionLabel="Analyze a message"
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-muted-foreground">
                          <th className="px-4 py-2.5 font-medium">Target / Input</th>
                          <th className="px-3 py-2.5 font-medium">Verdict</th>
                          <th className="px-3 py-2.5 font-medium">Risk</th>
                          <th className="hidden px-3 py-2.5 font-medium sm:table-cell">Score</th>
                          <th className="hidden px-3 py-2.5 font-medium md:table-cell">Date</th>
                          <th className="px-4 py-2.5 text-right font-medium">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {recentEntries.map((entry) => (
                          <tr key={entry.id} className="transition-colors hover:bg-muted/30">
                            <td className="max-w-[240px] px-4 py-3">
                              <p className="truncate font-medium text-foreground">
                                {truncate(entry.text, 56)}
                              </p>
                              <p className="mt-0.5 font-mono text-[11px] uppercase text-muted-foreground">
                                {entry.input_type ?? "TEXT"}
                                {entry.scam_category ? ` · ${scamCategoryLabel(entry.scam_category)}` : ""}
                              </p>
                            </td>
                            <td className="whitespace-nowrap px-3 py-3 text-xs font-medium text-foreground">
                              {verdictLabel(entry.verdict)}
                            </td>
                            <td className="whitespace-nowrap px-3 py-3">
                              <ThreatBadge threatLevel={entry.threat_level} riskLevel={entry.risk_level} />
                            </td>
                            <td className="hidden whitespace-nowrap px-3 py-3 font-mono text-xs tabular-nums text-muted-foreground sm:table-cell">
                              {formatPercent(entry.threat_score)}
                            </td>
                            <td className="hidden whitespace-nowrap px-3 py-3 font-mono text-xs text-muted-foreground md:table-cell">
                              {formatDate(entry.created_at)}
                            </td>
                            <td className="whitespace-nowrap px-4 py-3 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedFinding(entry)}
                              >
                                Details
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="flex min-w-0 flex-col gap-5">
              <Card className="console-panel min-w-0">
                <CardHeader className="border-b border-border bg-card/60">
                  <CardTitle className="text-lg">Recurring indicators</CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  {recurringIndicators.length === 0 ? (
                    <p className="text-sm leading-6 text-muted-foreground">
                      No recurring URLs, phone numbers, or UPI IDs have appeared across multiple scans yet.
                    </p>
                  ) : (
                    <div className="space-y-2.5">
                      {recurringIndicators.map(([indicator, count]) => (
                        <div
                          key={indicator}
                          className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/30 px-3 py-2"
                        >
                          <span className="truncate font-mono text-xs text-foreground">{indicator}</span>
                          <span className="shrink-0 font-mono text-xs font-medium text-primary">
                            {count}×
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              <PhoneLookup />
            </div>
          </div>
        </>
      )}

      {/* Finding Inspector Modal */}
      {selectedFinding && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          onClick={() => setSelectedFinding(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="finding-dialog-title"
            className="w-full max-w-2xl rounded-lg border border-border bg-card p-6 text-card-foreground shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
              <div>
                <p className="console-kicker mb-1">Finding inspection</p>
                <h2 id="finding-dialog-title" className="text-xl font-semibold text-foreground">
                  {verdictLabel(selectedFinding.verdict)}
                  {selectedFinding.scam_category ? ` — ${scamCategoryLabel(selectedFinding.scam_category)}` : ""}
                </h2>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {formatDate(selectedFinding.created_at)} · {(selectedFinding.input_type ?? "TEXT").toUpperCase()} · Threat score{" "}
                  {formatPercent(selectedFinding.threat_score)} · Confidence {formatPercent(selectedFinding.confidence_score)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <ThreatBadge threatLevel={selectedFinding.threat_level} riskLevel={selectedFinding.risk_level} />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedFinding(null)}
                  aria-label="Close finding details"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Analyzed content
                </p>
                <div className="max-h-40 overflow-y-auto rounded-md border border-border bg-muted/40 p-3 font-mono text-xs leading-relaxed text-foreground">
                  {selectedFinding.text}
                </div>
              </div>

              {(selectedFinding.executive_summary || selectedFinding.ai_explanation) && (
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Why it was flagged
                  </p>
                  <p className="text-sm leading-6 text-foreground/90">
                    {selectedFinding.executive_summary ?? selectedFinding.ai_explanation}
                  </p>
                </div>
              )}

              {selectedFinding.top_contributing_tokens && selectedFinding.top_contributing_tokens.length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Top signal tokens
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedFinding.top_contributing_tokens.slice(0, 10).map((tok) => (
                      <span
                        key={tok.token}
                        className="rounded-sm border border-primary/25 bg-primary/10 px-2 py-0.5 font-mono text-xs text-primary"
                      >
                        {tok.token}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedFinding.recommended_actions && selectedFinding.recommended_actions.length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Recommended actions
                  </p>
                  <ul className="list-disc space-y-1 pl-5 text-sm text-foreground/90">
                    {selectedFinding.recommended_actions.slice(0, 4).map((action, idx) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-border pt-4">
              <Link
                href="/history"
                className={buttonVariants({ variant: "outline", size: "sm" })}
                onClick={() => setSelectedFinding(null)}
              >
                Open in history
              </Link>
              <Button size="sm" onClick={() => setSelectedFinding(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
