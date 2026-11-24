"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Eye,
  File,
  Image as ImageIcon,
  Link as LinkIcon,
  Mail,
  MessageSquareText,
  Mic,
  QrCode,
  Radio,
  RefreshCw,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { getAnalyticsSummary } from "@/lib/api/analytics";
import { getHistory } from "@/lib/api/messages";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { ThreatBadge } from "@/components/analysis/risk-badge";
import { ThreatCoreCanvas } from "@/components/visuals/threat-core-canvas";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { cn, formatDate, formatPercent, scamCategoryLabel, truncate, verdictLabel } from "@/lib/utils";
import type { AnalysisResult, AnalyticsSummary } from "@/types";
import { PhoneLookup } from "@/components/dashboard/phone-lookup";

const ChartSkeleton = () => <Skeleton className="h-64 w-full" />;

const RiskTrendChart = dynamic(
  () => import("@/components/analytics/risk-trend-chart").then((m) => m.RiskTrendChart),
  { ssr: false, loading: ChartSkeleton },
);

function displayEntryText(entry: AnalysisResult): string {
  const urlMeta = entry.metadata?.url_intelligence as { original_url?: string } | undefined;
  if (urlMeta?.original_url) return urlMeta.original_url;
  if (entry.text.startsWith("URL Target:")) {
    const stripped = entry.text.slice("URL Target:".length).trim();
    const idx = stripped.indexOf(" Observed URL signals:");
    return idx >= 0 ? stripped.slice(0, idx).trim() : stripped;
  }
  return entry.text;
}

function isHighRisk(entry: AnalysisResult): boolean {
  return (
    entry.threat_level === "high" ||
    entry.threat_level === "critical" ||
    (!entry.threat_level && entry.risk_level === "high")
  );
}

function ChannelIcon({ inputType }: { inputType?: string | null }) {
  const key = (inputType ?? "TEXT").toUpperCase();
  if (key === "URL") return <LinkIcon className="h-4 w-4 text-primary" aria-hidden="true" />;
  if (key === "EMAIL") return <Mail className="h-4 w-4 text-primary" aria-hidden="true" />;
  if (key === "IMAGE") return <ImageIcon className="h-4 w-4 text-primary" aria-hidden="true" />;
  if (key === "VOICE") return <Mic className="h-4 w-4 text-primary" aria-hidden="true" />;
  if (key === "PDF") return <File className="h-4 w-4 text-primary" aria-hidden="true" />;
  if (key === "QR") return <QrCode className="h-4 w-4 text-primary" aria-hidden="true" />;
  return <MessageSquareText className="h-4 w-4 text-primary" aria-hidden="true" />;
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

  const safePct = totalScans > 0 ? Math.round((safeCount / totalScans) * 100) : 0;
  const suspiciousPct = totalScans > 0 ? Math.round((suspiciousCount / totalScans) * 100) : 0;
  const highPct = totalScans > 0 ? Math.round((highRiskCount / totalScans) * 100) : 0;

  const topCategoryRaw = summary
    ? Object.entries(summary.category_distribution).sort((a, b) => b[1] - a[1])[0]?.[0]
    : undefined;
  const topCategory = topCategoryRaw ? scamCategoryLabel(topCategoryRaw) : null;

  const allHighPriority = entries.filter(isHighRisk);
  const highPriority = allHighPriority.slice(0, 5);
  const recentEntries = entries.slice(0, 6);

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

  const kpiCards = [
    {
      label: "Total Scans",
      value: totalScans.toLocaleString("en-IN"),
      badge: totalScans > 0 ? `${formatPercent(detectionRate)} flagged` : "No scans yet",
      badgeCls: "text-primary",
      icon: ScanSearch,
      iconCls: "border-primary/30 bg-primary/10 text-primary",
      wideMobile: false,
    },
    {
      label: "Safe",
      value: safeCount.toLocaleString("en-IN"),
      badge: `${safePct}% legitimate`,
      badgeCls: "text-safe",
      icon: CheckCircle2,
      iconCls: "border-safe/30 bg-safe/10 text-safe",
      wideMobile: false,
    },
    {
      label: "Suspicious",
      value: suspiciousCount.toLocaleString("en-IN"),
      badge: `${suspiciousPct}% caution`,
      badgeCls: "text-caution",
      icon: AlertTriangle,
      iconCls: "border-caution/30 bg-caution/10 text-caution",
      wideMobile: false,
    },
    {
      label: "High Risk",
      value: highRiskCount.toLocaleString("en-IN"),
      badge: `${highPct}% critical/high`,
      badgeCls: "text-destructive",
      icon: ShieldAlert,
      iconCls: "border-destructive/30 bg-destructive/10 text-destructive",
      wideMobile: false,
    },
  ];

  return (
    <div className="sg-page flex flex-col gap-6">
      {/* Header matching Reference Panel 2 */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="console-kicker mb-1.5">Threat Operations Center</p>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Threat Overview</h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted-foreground">
            Real-time insights into detected scams and risks across your workspace.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadDashboard(true)}
            disabled={isLoading || isRefreshing}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} aria-hidden="true" />
            Refresh
          </Button>
          <Link href="/analyze" className={buttonVariants({ size: "md" })}>
            <ScanSearch className="h-4 w-4" aria-hidden="true" />
            New Scan
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

      {/* 4 KPI Cards Row (Reference Panel 2) */}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <motion.section
          aria-label="Threat summary metrics"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22 }}
          className="grid grid-cols-2 gap-4 lg:grid-cols-4"
        >
          {kpiCards.map((card) => {
            const Icon = card.icon;
            return (
              <Card key={card.label} className="console-panel p-4 sm:p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-sans text-2xl font-bold tabular-nums tracking-tight text-foreground sm:text-3xl">
                      {card.value}
                    </p>
                    <p className="mt-1 text-xs font-medium text-muted-foreground">{card.label}</p>
                  </div>
                  <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border", card.iconCls)}>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </div>
                </div>
                <p className={cn("mt-3 font-mono text-[11px] font-medium", card.badgeCls)}>{card.badge}</p>
              </Card>
            );
          })}
        </motion.section>
      )}

      {/* Middle Row: Live Threat Radar (left) + Glowing Cyan Threat Trend (right) */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <Skeleton className="h-80 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          {/* Live Threat Radar */}
          <Card className="console-panel flex flex-col justify-between p-5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-primary" aria-hidden="true" />
                <CardTitle className="text-base font-semibold">Live Threat Radar</CardTitle>
              </div>
              <span className="font-mono text-[11px] text-muted-foreground">
                {topCategory ? `Top: ${topCategory}` : "Monitoring"}
              </span>
            </div>

            <div className="my-2 h-56 w-full">
              <ThreatCoreCanvas
                mode="radar"
                threatRatio={detectionRate}
                counts={{ safe: safeCount, suspicious: suspiciousCount, highRisk: highRiskCount }}
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs">
              <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-safe" aria-hidden="true" />
                  {safeCount} safe
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-caution" aria-hidden="true" />
                  {suspiciousCount} suspicious
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-destructive" aria-hidden="true" />
                  {highRiskCount} high risk
                </span>
              </div>
              <Link href="/analytics" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">
                Analytics
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </div>
          </Card>

          {/* Threat Trend */}
          {entries.length > 0 ? (
            <RiskTrendChart entries={entries.slice(0, 30)} />
          ) : (
            <Card className="console-panel flex flex-col justify-center p-6">
              <EmptyState
                icon={ScanSearch}
                title="No scan trend yet"
                description="Run your first scan to plot live threat likelihood over recent activity."
                actionHref="/analyze"
                actionLabel="Run first scan"
              />
            </Card>
          )}
        </div>
      )}

      {/* Recent Scan Activity (Reference Panel 2 Bottom) */}
      {!isLoading && (
        <Card className="console-panel min-w-0 overflow-hidden">
          <CardHeader className="flex-row items-center justify-between gap-3 border-b border-border bg-card/60">
            <div className="min-w-0">
              <CardTitle className="text-lg">Recent Scan Activity</CardTitle>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Latest messages, links, emails, and files inspected in your workspace.
              </p>
            </div>
            <Link href="/history" className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-xs font-medium text-primary hover:underline">
              View All
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            {recentEntries.length === 0 ? (
              <EmptyState
                icon={ScanSearch}
                title="No activity yet"
                description="Analyze your first message, link, or screenshot to populate your activity stream."
                actionHref="/analyze"
                actionLabel="Analyze a message"
              />
            ) : (
              <ul className="divide-y divide-border">
                {recentEntries.map((entry) => (
                  <li
                    key={entry.id}
                    className="flex flex-col gap-3 px-4 py-3.5 transition-colors hover:bg-muted/35 md:flex-row md:items-center md:justify-between md:px-6"
                  >
                    <div className="flex min-w-0 flex-1 items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background/70">
                        <ChannelIcon inputType={entry.input_type} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{truncate(displayEntryText(entry), 84)}</p>
                        <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
                          {verdictLabel(entry.verdict)}
                          {entry.scam_category ? ` · ${scamCategoryLabel(entry.scam_category)}` : ""}
                          {" · Score "}
                          {formatPercent(entry.threat_score)}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center justify-between gap-3 md:justify-end">
                      <ThreatBadge threatLevel={entry.threat_level} riskLevel={entry.risk_level} />
                      <span className="hidden font-mono text-xs text-muted-foreground xl:inline">
                        {formatDate(entry.created_at)}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="whitespace-nowrap text-primary hover:text-primary"
                        onClick={() => setSelectedFinding(entry)}
                      >
                        <Eye className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
                        Inspect
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {/* Priority Findings + Recurring Indicators & Phone Lookup */}
      {!isLoading && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.28fr)_minmax(0,0.72fr)]">
          <Card className="console-panel min-w-0 overflow-hidden">
            <CardHeader className="flex-row items-center justify-between gap-3 border-b border-border bg-card/60">
              <div className="min-w-0">
                <CardTitle className="text-lg">Priority Findings</CardTitle>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  High and critical risk items requiring review or reporting.
                </p>
              </div>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {allHighPriority.length} high-risk
              </span>
            </CardHeader>
            <CardContent className="p-0">
              {highPriority.length === 0 ? (
                <EmptyState
                  icon={ShieldCheck}
                  title="No high-risk findings"
                  description="New high-risk detections will appear here automatically."
                  actionHref="/analyze"
                  actionLabel="Start an investigation"
                />
              ) : (
                <ul className="divide-y divide-border">
                  {highPriority.map((entry) => (
                    <li
                      key={entry.id}
                      className="flex items-center justify-between gap-3 border-l-2 border-l-destructive/80 px-4 py-3.5 transition-colors hover:bg-muted/30 sm:px-5"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{truncate(entry.text, 76)}</p>
                        <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                          {entry.scam_category ? scamCategoryLabel(entry.scam_category) : verdictLabel(entry.verdict)} ·{" "}
                          {formatPercent(entry.threat_score)} · {formatDate(entry.created_at)}
                        </p>
                      </div>
                      <Button variant="outline" size="sm" className="shrink-0 whitespace-nowrap" onClick={() => setSelectedFinding(entry)}>
                        Inspect
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <div className="flex min-w-0 flex-col gap-5">
            <Card className="console-panel min-w-0">
              <CardHeader className="border-b border-border bg-card/60">
                <CardTitle className="text-lg">Recurring Indicators</CardTitle>
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
                        className="flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-3 py-2"
                      >
                        <span className="truncate font-mono text-xs text-foreground">{indicator}</span>
                        <span className="shrink-0 font-mono text-xs font-medium text-primary">{count}×</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
            <PhoneLookup />
          </div>
        </div>
      )}

      {/* Animated Finding Inspector Modal */}
      <AnimatePresence>
        {selectedFinding && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
            onClick={() => setSelectedFinding(null)}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-labelledby="finding-dialog-title"
              initial={{ opacity: 0, scale: 0.97, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 8 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="w-full max-w-2xl rounded-xl border border-border bg-card p-6 text-card-foreground shadow-2xl"
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
                  <div className="max-h-40 overflow-y-auto rounded-lg border border-border bg-muted/40 p-3 font-mono text-xs leading-relaxed text-foreground">
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
                          className="rounded-md border border-primary/25 bg-primary/10 px-2 py-0.5 font-mono text-xs text-primary"
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
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
