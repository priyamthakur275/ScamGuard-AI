"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { BarChart3, CheckCircle2, RefreshCw } from "lucide-react";
import { getAnalyticsSummary } from "@/lib/api/analytics";
import { getHistory } from "@/lib/api/messages";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { cn, formatPercent, scamCategoryLabel } from "@/lib/utils";
import type { AnalyticsSummary, AnalysisResult } from "@/types";

const ChartSkeleton = () => <Skeleton className="h-64 w-full" />;

const RiskTrendChart = dynamic(
  () => import("@/components/analytics/risk-trend-chart").then((m) => m.RiskTrendChart),
  { ssr: false, loading: ChartSkeleton },
);

const ThreatDistributionPieChart = dynamic(
  () => import("@/components/analytics/threat-distribution-pie-chart").then((m) => m.ThreatDistributionPieChart),
  { ssr: false, loading: ChartSkeleton },
);

type TimeFilter = "24h" | "7d" | "30d" | "all";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  // The risk-trend chart shows the most RECENT scans regardless of the
  // selected range (it's explicitly a "recent trend" view, not an
  // all-time one) -- so it's fetched separately from the real aggregate.
  const [recentEntries, setRecentEntries] = useState<AnalysisResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("all");

  const load = useCallback(async (range: TimeFilter) => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryData, historyData] = await Promise.all([
        getAnalyticsSummary(range),
        getHistory(0, 30),
      ]);
      setSummary(summaryData);
      setRecentEntries(historyData);
    } catch {
      setError("Could not load analytics. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(timeFilter);
  }, [timeFilter, load]);

  if (isLoading && !summary) {
    return (
      <div className="sg-page flex flex-col gap-6">
        <div>
          <p className="console-kicker mb-1.5">Detection Telemetry</p>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Analytics</h1>
        </div>
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sg-page flex flex-col gap-6">
        <div>
          <p className="console-kicker mb-1.5">Detection Telemetry</p>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Analytics</h1>
        </div>
        <Alert variant="error">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => void load(timeFilter)}>
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
              Retry
            </Button>
          </div>
        </Alert>
      </div>
    );
  }

  if (!summary || summary.total_scans === 0) {
    return (
      <div className="sg-page flex flex-col gap-6">
        <div>
          <p className="console-kicker mb-1.5">Detection Telemetry</p>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Analytics</h1>
        </div>
        {timeFilter !== "all" && (
          <div>
            <Button variant="outline" size="sm" onClick={() => setTimeFilter("all")}>
              Show all time
            </Button>
          </div>
        )}
        <EmptyState
          icon={BarChart3}
          title="Nothing to analyze yet"
          description="Once you've scored a few messages, trends and breakdowns will appear here."
          actionHref="/analyze"
          actionLabel="Analyze a message"
        />
      </div>
    );
  }

  const scamCount = Object.entries(summary.verdict_distribution)
    .filter(([verdict]) => verdict !== "legitimate")
    .reduce((sum, [, count]) => sum + count, 0);
  const flaggedRate = summary.total_scans > 0 ? scamCount / summary.total_scans : 0;

  const categories = Object.entries(summary.category_distribution)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);
  const maxCategoryCount = Math.max(1, ...(categories.map(([, c]) => c)));
  const topCategory = categories[0]?.[0] ?? null;

  const ratedFeedback = summary.feedback_accurate + summary.feedback_inaccurate;
  const accurateShare = ratedFeedback > 0 ? Math.round((summary.feedback_accurate / ratedFeedback) * 100) : null;

  return (
    <div className="sg-page flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="console-kicker mb-1.5">Detection Telemetry</p>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Analytics</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Server-verified threat patterns across {summary.total_scans.toLocaleString("en-IN")} analyzed item
            {summary.total_scans === 1 ? "" : "s"}.
          </p>
        </div>

        <div role="group" aria-label="Time range" className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted/40 p-1">
          {(["24h", "7d", "30d", "all"] as const).map((filter) => (
            <button
              key={filter}
              type="button"
              aria-pressed={timeFilter === filter}
              onClick={() => setTimeFilter(filter)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                timeFilter === filter ? "bg-card text-primary shadow-sm ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {filter === "24h" ? "24h" : filter === "7d" ? "7 days" : filter === "30d" ? "30 days" : "All time"}
            </button>
          ))}
        </div>
      </div>

      {/* Focused 3-metric hairline telemetry strip */}
      <section aria-label="Key telemetry" className="console-panel grid divide-y divide-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-5 sm:px-6">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Total Analyzed</p>
          <p className="mt-2 font-display text-3xl font-bold tabular-nums text-foreground">
            {summary.total_scans.toLocaleString("en-IN")}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {topCategory ? `Top tactic: ${scamCategoryLabel(topCategory)}` : "No threat categories flagged"}
          </p>
        </div>

        <div className="p-5 sm:px-6">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Flagged Rate</p>
          <p className="mt-2 font-display text-3xl font-bold tabular-nums text-destructive">
            {formatPercent(flaggedRate)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {scamCount.toLocaleString("en-IN")} scam or suspicious · {summary.high_risk_count.toLocaleString("en-IN")} high risk
          </p>
        </div>

        <div className="p-5 sm:px-6">
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Avg Threat Score</p>
          <p className="mt-2 font-display text-3xl font-bold tabular-nums text-primary">
            {formatPercent(summary.average_threat_score)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {accurateShare !== null ? `${accurateShare}% analyst agreement (${ratedFeedback} rated)` : `${summary.feedback_pending} awaiting feedback`}
          </p>
        </div>
      </section>

      {/* Primary Charts: Threat Trend + Verdict Share */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
        <RiskTrendChart entries={recentEntries} />
        <ThreatDistributionPieChart distribution={summary.verdict_distribution} />
      </div>

      {/* Category Breakdown & Feedback Calibration */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)]">
        <Card className="console-panel">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Scam Categories</CardTitle>
            <p className="text-xs text-muted-foreground">Frequency by detected scam typology in the selected range</p>
          </CardHeader>
          <CardContent className="pt-3">
            {categories.length === 0 ? (
              <p className="py-6 text-sm text-muted-foreground">
                No scam categories recorded in this window.
              </p>
            ) : (
              <ul className="space-y-3.5">
                {categories.slice(0, 6).map(([category, count]) => {
                  const pct = Math.round((count / Math.max(1, summary.total_scans)) * 100);
                  const barWidth = Math.max(6, Math.round((count / maxCategoryCount) * 100));
                  return (
                    <li key={category}>
                      <div className="flex items-center justify-between gap-2 text-xs">
                        <span className="font-medium text-foreground">{scamCategoryLabel(category)}</span>
                        <span className="font-mono tabular-nums text-muted-foreground">
                          <strong className="font-semibold text-foreground">{count}</strong> ({pct}%)
                        </span>
                      </div>
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-primary to-cyan-400"
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="console-panel flex flex-col justify-between">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Feedback Calibration</CardTitle>
            <p className="text-xs text-muted-foreground">User verification labels submitted on scan verdicts</p>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col justify-between gap-5 pt-3">
            <div className="grid grid-cols-3 gap-2.5 text-center">
              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="font-mono text-lg font-bold tabular-nums text-safe">{summary.feedback_accurate}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">Accurate</p>
              </div>
              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="font-mono text-lg font-bold tabular-nums text-destructive">{summary.feedback_inaccurate}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">Inaccurate</p>
              </div>
              <div className="rounded-lg border border-border bg-background/60 p-3">
                <p className="font-mono text-lg font-bold tabular-nums text-foreground">{summary.feedback_pending}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">Unrated</p>
              </div>
            </div>

            <div className="space-y-2 border-t border-border/70 pt-3">
              <div className="flex items-center justify-between text-xs">
                <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-safe" aria-hidden="true" />
                  Confirmed precision
                </span>
                <span className="font-mono font-semibold tabular-nums text-foreground">
                  {accurateShare !== null ? `${accurateShare}%` : "No ratings yet"}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-safe transition-all duration-300"
                  style={{ width: `${accurateShare ?? 0}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
