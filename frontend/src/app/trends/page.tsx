"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { RefreshCw } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { Skeleton } from "@/components/ui/skeleton";
import { getTrends, type ScamTrends } from "@/lib/api/public";
import { cn, inputTypeLabel, scamCategoryLabel } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/language-context";

// The chart library is ~100 KB; load it after the page so the numbers appear first.
const DailyChart = dynamic(() => import("@/components/trends/daily-chart"), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

export default function TrendsPage() {
  const { t } = useLanguage();
  const [days, setDays] = useState<7 | 30>(30);
  const [data, setData] = useState<ScamTrends | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let live = true;
    setError(null);
    getTrends(days)
      .then((d) => live && setData(d))
      .catch(() => live && setError("Could not load trends. The server may be waking up; refresh in a few seconds."));
    return () => {
      live = false;
    };
  }, [days, retryKey]);

  const maxCat = Math.max(1, ...(data?.top_categories.map((c) => c.count) ?? [1]));
  const totalChannels = Math.max(1, ...(data?.channels.reduce((acc, c) => acc + c.count, 0) ? [data.channels.reduce((acc, c) => acc + c.count, 0)] : [1]));
  const topTactic = data?.top_categories[0];
  const topChannel = data?.channels.slice().sort((a, b) => b.count - a.count)[0];

  return (
    <PublicShell>
      <div className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="console-kicker">{t("td.kicker")}</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">{t("td.title")}</h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">{t("td.sub")}</p>
        </div>

        <div role="radiogroup" aria-label="Time range" className="inline-flex shrink-0 rounded-lg border border-border bg-muted/40 p-1">
          {([7, 30] as const).map((d) => (
            <button
              key={d}
              type="button"
              role="radio"
              aria-checked={days === d}
              onClick={() => setDays(d)}
              className={cn(
                "rounded-md px-4 py-1.5 text-xs font-medium transition-colors",
                days === d ? "bg-card text-primary shadow-sm ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t("td.last", { n: d })}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div role="alert" className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setRetryKey((k) => k + 1)}
            className="inline-flex items-center gap-1.5 rounded-md border border-destructive/40 px-3 py-1 text-xs font-medium hover:bg-destructive/15"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Retry
          </button>
        </div>
      )}

      {!data && !error && (
        <div className="mt-6 space-y-6">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-72 w-full" />
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-56 w-full" />
          </div>
        </div>
      )}

      {data && (
        <div className="mt-6 space-y-6">
          {/* Sleek 3-metric telemetry strip */}
          <section aria-label="Threat intelligence summary" className="console-panel grid divide-y divide-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <div className="p-5 sm:px-6">
              <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{t("td.checked")}</p>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-foreground">
                {data.total_scans.toLocaleString("en-IN")}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {topChannel ? `Primary channel: ${inputTypeLabel(topChannel.input_type)}` : "All channels"}
              </p>
            </div>
            <div className="p-5 sm:px-6">
              <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{t("td.flagged")}</p>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-destructive">
                {data.flagged_scans.toLocaleString("en-IN")}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {topTactic
                  ? `Leading threat: ${topTactic.category === "uncategorised" ? "Other / mixed" : scamCategoryLabel(topTactic.category)}`
                  : "Zero flagged scams in window"}
              </p>
            </div>
            <div className="p-5 sm:px-6">
              <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{t("td.share")}</p>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-primary">
                {Math.round(data.flagged_rate * 100)}%
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Across {days}-day inspection volume
              </p>
            </div>
          </section>

          {/* Daily Activity Area Chart centerpiece */}
          <section className="console-panel p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-foreground">{t("td.daily")}</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">Daily inspection volume vs detected scams</p>
              </div>
              <div className="flex items-center gap-4 font-mono text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
                  Checked
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-destructive" aria-hidden="true" />
                  Scams
                </span>
              </div>
            </div>
            <div className="mt-4 h-72">
              <DailyChart daily={data.daily} />
            </div>
          </section>

          {/* Typologies & Channels breakdown */}
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="console-panel p-6">
              <h2 className="text-base font-semibold text-foreground">{t("td.types")}</h2>
              {data.top_categories.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No scams flagged in this period yet.</p>
              ) : (
                <ul className="mt-4 space-y-3.5">
                  {data.top_categories.map((c) => {
                    const share = data.flagged_scans > 0 ? Math.round((c.count / data.flagged_scans) * 100) : 0;
                    return (
                      <li key={c.category}>
                        <div className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-medium text-foreground">
                            {c.category === "uncategorised" ? "Other / mixed" : scamCategoryLabel(c.category)}
                          </span>
                          <span className="font-mono tabular-nums text-muted-foreground">
                            <strong className="font-semibold text-foreground">{c.count}</strong> · {share}%
                          </span>
                        </div>
                        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-destructive/85 transition-all duration-500"
                            style={{ width: `${Math.max(6, (c.count / maxCat) * 100)}%` }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section className="console-panel p-6">
              <h2 className="text-base font-semibold text-foreground">{t("td.where")}</h2>
              {data.channels.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No data yet.</p>
              ) : (
                <ul className="mt-4 space-y-3.5">
                  {data.channels
                    .slice()
                    .sort((a, b) => b.count - a.count)
                    .map((c) => {
                      const pct = Math.round((c.count / totalChannels) * 100);
                      return (
                        <li key={c.input_type}>
                          <div className="flex items-center justify-between gap-2 text-xs">
                            <span className="font-medium text-foreground">{inputTypeLabel(c.input_type)}</span>
                            <span className="font-mono tabular-nums text-muted-foreground">
                              <strong className="font-semibold text-foreground">{c.count.toLocaleString("en-IN")}</strong> · {pct}%
                            </span>
                          </div>
                          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full rounded-full bg-primary/85 transition-all duration-500"
                              style={{ width: `${Math.max(5, pct)}%` }}
                            />
                          </div>
                        </li>
                      );
                    })}
                </ul>
              )}
            </section>
          </div>
        </div>
      )}
    </PublicShell>
  );
}
