"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { PublicShell } from "@/components/layout/public-shell";
import { getTrends, type ScamTrends } from "@/lib/api/public";
import { cn, inputTypeLabel, scamCategoryLabel } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/language-context";

// The chart library is ~100 KB; load it after the page so the numbers appear first.
const DailyChart = dynamic(() => import("@/components/trends/daily-chart"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded bg-muted" aria-label="Loading chart" />,
});

export default function TrendsPage() {
  const { t } = useLanguage();
  const [days, setDays] = useState<7 | 30>(30);
  const [data, setData] = useState<ScamTrends | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setError(null);
    getTrends(days)
      .then((d) => live && setData(d))
      .catch(() => live && setError("Could not load trends. The server may be waking up; refresh in a few seconds."));
    return () => {
      live = false;
    };
  }, [days]);

  const maxCat = Math.max(1, ...(data?.top_categories.map((c) => c.count) ?? [1]));

  return (
    <PublicShell>
      <p className="text-xs text-primary">{t("td.kicker")}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">{t("td.title")}</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        {t("td.sub")}
      </p>

      <div role="radiogroup" aria-label="Time range" className="mt-6 inline-flex border border-border">
        {([7, 30] as const).map((d) => (
          <button
            key={d}
            role="radio"
            aria-checked={days === d}
            onClick={() => setDays(d)}
            className={cn("px-4 py-2 text-sm", days === d ? "bg-primary text-primary-foreground" : "text-muted-foreground")}
          >
            {t("td.last", { n: d })}
          </button>
        ))}
      </div>

      {error && <p className="mt-6 text-sm text-destructive">{error}</p>}
      {!data && !error && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}

      {data && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {[
              [t("td.checked"), data.total_scans.toLocaleString("en-IN")],
              [t("td.flagged"), data.flagged_scans.toLocaleString("en-IN")],
              [t("td.share"), `${Math.round(data.flagged_rate * 100)}%`],
            ].map(([label, value]) => (
              <div key={label} className="border border-border p-5">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <section className="border border-border p-5">
              <h2 className="text-base font-semibold">{t("td.types")}</h2>
              {data.top_categories.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No scams flagged in this period yet.</p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {data.top_categories.map((c) => (
                    <li key={c.category}>
                      <div className="flex justify-between text-sm">
                        <span>{c.category === "uncategorised" ? "Other / mixed" : scamCategoryLabel(c.category)}</span>
                        <span className="tabular-nums text-muted-foreground">{c.count}</span>
                      </div>
                      <div className="mt-1 h-2 bg-muted">
                        <div className="h-2 bg-destructive/80" style={{ width: `${(c.count / maxCat) * 100}%` }} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="border border-border p-5">
              <h2 className="text-base font-semibold">{t("td.where")}</h2>
              {data.channels.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No data yet.</p>
              ) : (
                <ul className="mt-4 grid grid-cols-2 gap-3">
                  {data.channels.map((c) => (
                    <li key={c.input_type} className="border border-border p-3">
                      <p className="text-xs text-muted-foreground">{inputTypeLabel(c.input_type)}</p>
                      <p className="text-xl font-semibold tabular-nums">{c.count}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="mt-6 border border-border p-5">
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
