"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
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

  return (
    <PublicShell>
      <p className="console-kicker">{t("td.kicker")}</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">{t("td.title")}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
        {t("td.sub")}
      </p>

      <div role="radiogroup" aria-label="Time range" className="mt-6 inline-flex rounded-lg border border-border bg-muted/40 p-1">
        {([7, 30] as const).map((d) => (
          <button
            key={d}
            role="radio"
            aria-checked={days === d}
            onClick={() => setDays(d)}
            className={cn(
              "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
              days === d ? "bg-card text-primary shadow-sm ring-1 ring-primary/30" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t("td.last", { n: d })}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setRetryKey((k) => k + 1)}
            className="rounded-md border border-destructive/40 px-3 py-1 text-xs font-medium hover:bg-destructive/15"
          >
            Retry
          </button>
        </div>
      )}
      {!data && !error && (
        <div className="mt-6 space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      )}

      {data && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {[
              [t("td.checked"), data.total_scans.toLocaleString("en-IN")],
              [t("td.flagged"), data.flagged_scans.toLocaleString("en-IN")],
              [t("td.share"), `${Math.round(data.flagged_rate * 100)}%`],
            ].map(([label, value]) => (
              <div key={label} className="console-panel p-5">
                <p className="text-xs font-medium text-muted-foreground">{label}</p>
                <p className="mt-2 font-sans text-3xl font-bold tabular-nums text-foreground">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section className="console-panel p-6">
              <h2 className="text-base font-semibold">{t("td.types")}</h2>
              {data.top_categories.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No scams flagged in this period yet.</p>
              ) : (
                <ul className="mt-4 space-y-3.5">
                  {data.top_categories.map((c) => (
                    <li key={c.category}>
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-foreground">
                          {c.category === "uncategorised" ? "Other / mixed" : scamCategoryLabel(c.category)}
                        </span>
                        <span className="font-mono text-xs tabular-nums text-muted-foreground">{c.count}</span>
                      </div>
                      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-destructive/80 transition-all duration-500" style={{ width: `${(c.count / maxCat) * 100}%` }} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="console-panel p-6">
              <h2 className="text-base font-semibold">{t("td.where")}</h2>
              {data.channels.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No data yet.</p>
              ) : (
                <ul className="mt-4 grid grid-cols-2 gap-3">
                  {data.channels.map((c) => (
                    <li key={c.input_type} className="rounded-lg border border-border bg-background/60 p-3.5">
                      <p className="text-xs text-muted-foreground">{inputTypeLabel(c.input_type)}</p>
                      <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-foreground">{c.count}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="console-panel mt-6 p-6">
            <h2 className="text-base font-semibold">{t("td.daily")}</h2>
            <div className="mt-4 h-64">
              <DailyChart daily={data.daily} />
            </div>
          </section>
        </>
      )}
    </PublicShell>
  );
}
