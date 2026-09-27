"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { AlertTriangle, BarChart3, ScanSearch, ShieldAlert } from "lucide-react";
import { getAnalyticsSummary } from "@/lib/api/analytics";
import { getHistory } from "@/lib/api/messages";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/analytics/stat-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { formatPercent, scamCategoryLabel } from "@/lib/utils";
import type { AnalyticsSummary, AnalysisResult } from "@/types";

const ChartSkeleton = () => <Skeleton className="h-64 w-full" />;

const VerdictDistributionChart = dynamic(
  () => import("@/components/analytics/verdict-distribution-chart").then((m) => m.VerdictDistributionChart),
  { ssr: false, loading: ChartSkeleton },
);

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
    load(timeFilter);
  }, [timeFilter, load]);

  if (isLoading && !summary) {
    return (
      <div className="sg-page flex flex-col gap-8">
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Analytics</h1>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Analytics</h1>
        <Alert variant="error">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => load(timeFilter)}>Retry</Button>
          </div>
        </Alert>
      </div>
    );
  }

  if (!summary || summary.total_scans === 0) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Analytics</h1>
        {timeFilter !== "all" && <Button variant="outline" onClick={() => setTimeFilter("all")}>Show all time</Button>}
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
  const highRiskRate = summary.total_scans > 0 ? summary.high_risk_count / summary.total_scans : 0;
  const topCategory = Object.entries(summary.category_distribution).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "None";

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-sans text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Server-side totals across {summary.total_scans} analyzed message{summary.total_scans === 1 ? "" : "s"}.
          </p>
        </div>
        <div role="group" aria-label="Time range" className="flex items-center gap-1 rounded-md border border-border p-1">
          {(["24h", "7d", "30d", "all"] as const).map((filter) => (
            <button
              key={filter}
              aria-pressed={timeFilter === filter}
              onClick={() => setTimeFilter(filter)}
              className={`rounded-sm px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition-colors ${
                timeFilter === filter
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {filter === "24h" ? "24h" : filter === "7d" ? "7 days" : filter === "30d" ? "30 days" : "All time"}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total analyzed" value={String(summary.total_scans)} icon={ScanSearch} />
        <StatCard label="Flagged as scam/spam" value={String(scamCount)} icon={ShieldAlert} accent="destructive" />
        <StatCard label="High-risk rate" value={formatPercent(highRiskRate)} icon={AlertTriangle} accent="warning" />
        <StatCard label="Avg. threat score" value={formatPercent(summary.average_threat_score)} icon={BarChart3} accent="warning" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ThreatDistributionPieChart distribution={summary.verdict_distribution} />
        <VerdictDistributionChart distribution={summary.verdict_distribution} />
        <RiskTrendChart entries={recentEntries} />
      </div>

      <p className="text-sm text-muted-foreground">
        Most common scam category: <span className="font-medium text-foreground">{topCategory === "None" ? "None" : scamCategoryLabel(topCategory)}</span>
        {" · "}
        Feedback: {summary.feedback_accurate} accurate, {summary.feedback_inaccurate} inaccurate, {summary.feedback_pending} pending
      </p>
    </div>
  );
}
