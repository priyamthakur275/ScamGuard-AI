"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowUpRight, CircleDot, ScanSearch, ShieldCheck, Target, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import { getHistory } from "@/lib/api/messages";
import { useAuth } from "@/lib/auth/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { ThreatBadge } from "@/components/analysis/risk-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { formatDate, formatPercent, truncate, verdictLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<AnalysisResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHistory()
      .then(setEntries)
      .catch(() => setError("Could not load your activity. Please try again."))
      .finally(() => setIsLoading(false));
  }, []);

  const totalScanned = entries.length;
  const flagged = entries.filter((e) => e.verdict !== "legitimate").length;
  // One definition of "high risk" across the page: high/critical threat
  // level, or a high model risk level for scans without a threat level.
  const isHighRisk = (e: AnalysisResult) =>
    e.threat_level === "high" || e.threat_level === "critical" || (!e.threat_level && e.risk_level === "high");
  const allHighPriority = entries.filter(isHighRisk);
  const highRisk = allHighPriority.length;
  const highPriority = allHighPriority.slice(0, 5);
  const recentEntries = entries.slice(0, 6);
  const indicatorCounts = new Map<string, number>();
  entries.forEach((entry) => {
    new Set(Object.values(entry.highlighted_entities ?? {}).flat()).forEach((value) => {
      if (value) indicatorCounts.set(value, (indicatorCounts.get(value) ?? 0) + 1);
    });
  });
  const recurringIndicators = Array.from(indicatorCounts.entries()).filter(([, count]) => count > 1).sort((a, b) => b[1] - a[1]).slice(0, 5);

  return (
    <div className="sg-page flex flex-col gap-8">
      <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p className="console-kicker mb-3">Security command center</p>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Your threat overview.
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">Your investigation surface for active threats, recurring indicators, and recent decisions.</p>
        </div>
        <Link href="/analyze" className={buttonVariants({ size: "md" })}>
          <ScanSearch className="h-4 w-4" />
          New investigation
        </Link>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {isLoading ? <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]"><Skeleton className="h-72 w-full" /><Skeleton className="h-72 w-full" /></div> : (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
          <Card className="console-panel min-w-0 overflow-hidden">
            <CardHeader className="border-b border-border bg-card/60 md:flex-row md:items-center md:justify-between">
              <div><p className="console-kicker mb-2">Immediate attention</p><CardTitle className="text-xl">Priority findings</CardTitle></div>
              <span className="font-mono text-xs text-muted-foreground">{highRisk > highPriority.length ? `Showing ${highPriority.length} of ${highRisk}` : `${highRisk} high-risk ${highRisk === 1 ? "finding" : "findings"}`}</span>
            </CardHeader>
            <CardContent className="p-0">
              {highPriority.length === 0 ? <EmptyState icon={ShieldCheck} title="No high-risk findings" description="New high-risk results will appear here when detected." actionHref="/analyze" actionLabel="Start an investigation" /> : (
                <ul className="divide-y divide-border">{highPriority.map((entry) => <li key={entry.id} className="flex items-start gap-3 px-4 py-4 sm:items-center sm:gap-4 sm:px-6"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm bg-risk-high/10 text-risk-high"><AlertTriangle className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{truncate(entry.text, 78)}</p><p className="mt-1 font-mono text-[11px] text-muted-foreground">{verdictLabel(entry.verdict)} · {formatDate(entry.created_at)}</p><div className="mt-2 sm:hidden"><ThreatBadge threatLevel={entry.threat_level} riskLevel={entry.risk_level} /></div></div><div className="hidden sm:block"><ThreatBadge threatLevel={entry.threat_level} riskLevel={entry.risk_level} /></div><Link href="/history" aria-label="Open scan history" title="Open scan history" className="shrink-0 p-2 text-primary"><ArrowUpRight className="h-4 w-4" /></Link></li>)}</ul>
              )}
            </CardContent>
          </Card>
          <Card className="console-panel min-w-0">
            <CardHeader><p className="console-kicker mb-2">Workspace signal</p><CardTitle className="text-xl">{totalScanned >= 50 ? "Latest 50 scans" : "Your scans"}</CardTitle></CardHeader>
            <CardContent className="space-y-5">
              <div className="flex items-center justify-between border-b border-border pb-4"><span className="flex items-center gap-2 text-sm text-muted-foreground"><Target className="h-4 w-4 text-primary" /> Scans</span><strong className="text-2xl">{totalScanned}</strong></div>
              <div className="flex items-center justify-between border-b border-border pb-4"><span className="flex items-center gap-2 text-sm text-muted-foreground"><CircleDot className="h-4 w-4 text-risk-medium" /> Flagged</span><strong className="text-2xl">{flagged}</strong></div>
              <div className="flex items-center justify-between"><span className="flex items-center gap-2 text-sm text-muted-foreground"><TrendingUp className="h-4 w-4 text-risk-high" /> High risk</span><strong className="text-2xl">{highRisk}</strong></div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.8fr)]">
        <Card className="console-panel min-w-0"><CardHeader className="flex-row items-center justify-between"><div><p className="console-kicker mb-2">Latest investigations</p><CardTitle>Recent scans</CardTitle></div><Link href="/history" className="text-xs font-medium text-primary hover:underline">View history</Link></CardHeader><CardContent>{recentEntries.length === 0 ? <EmptyState icon={ScanSearch} title="No activity yet" description="Analyze your first message to see results here." actionHref="/analyze" actionLabel="Analyze a message" /> : <ul className="divide-y divide-border">{recentEntries.map((entry) => <li key={entry.id} className="flex items-center justify-between gap-3 py-3"><div className="min-w-0 flex-1"><p className="truncate text-sm text-foreground">{truncate(entry.text, 70)}</p><p className="mt-1 font-mono text-xs text-muted-foreground">{verdictLabel(entry.verdict)} · {formatDate(entry.created_at)}</p></div><ThreatBadge threatLevel={entry.threat_level} riskLevel={entry.risk_level} /></li>)}</ul>}</CardContent></Card>
        <Card className="console-panel min-w-0"><CardHeader><p className="console-kicker mb-2">Observed more than once</p><CardTitle>Recurring indicators</CardTitle></CardHeader><CardContent>{recurringIndicators.length === 0 ? <p className="text-sm leading-6 text-muted-foreground">No recurring indicators have been observed in your scan history yet.</p> : <div className="space-y-3">{recurringIndicators.map(([indicator, count]) => <div key={indicator} className="flex items-center justify-between gap-3 rounded-sm border border-border bg-muted/30 px-3 py-2"><span className="truncate font-mono text-xs">{indicator}</span><span className="shrink-0 text-xs text-primary">{count} scans</span></div>)}</div>}</CardContent></Card>
      </div>
    </div>
  );
}
