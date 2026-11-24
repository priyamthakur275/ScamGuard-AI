"use client";

import { useMemo } from "react";
import { useReducedMotion } from "framer-motion";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS: Record<string, string> = {
  legitimate: "hsl(var(--safe))",
  spam: "hsl(var(--caution))",
  phishing: "hsl(var(--risk-high))",
  scam: "hsl(var(--destructive))",
};

interface Props {
  /** Pre-aggregated verdict -> count, from the real server-side summary. */
  distribution: Record<string, number>;
}

export function ThreatDistributionPieChart({ distribution }: Props) {
  const reduceMotion = useReducedMotion();
  const data = useMemo(
    () =>
      Object.entries(distribution)
        .filter(([, value]) => value > 0)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value),
    [distribution],
  );

  if (data.length === 0) return null;
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <Card className="console-panel flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold">Verdict Share</CardTitle>
        <p className="text-xs text-muted-foreground">Classification split across analyzed scans</p>
      </CardHeader>
      <CardContent className="grid flex-1 items-center gap-6 pt-2 sm:grid-cols-[180px_minmax(0,1fr)]">
        <div className="relative mx-auto h-44 w-44 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={76}
                paddingAngle={data.length > 1 ? 3 : 0}
                stroke="none"
                dataKey="value"
                nameKey="name"
                isAnimationActive={!reduceMotion}
                animationDuration={400}
                animationEasing="ease-out"
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name] || "hsl(var(--primary))"} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--primary) / 0.35)",
                  borderRadius: "0.75rem",
                  fontSize: "0.8125rem",
                  color: "hsl(var(--foreground))",
                }}
                itemStyle={{ color: "hsl(var(--foreground))", textTransform: "capitalize" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className="font-display text-2xl font-bold tabular-nums text-foreground">
              {total.toLocaleString("en-IN")}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Total</span>
          </div>
        </div>

        <ul className="space-y-3">
          {data.map((item) => {
            const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
            const dotColor = COLORS[item.name] || "hsl(var(--primary))";
            return (
              <li key={item.name} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/45 px-3.5 py-2 text-xs">
                <span className="flex items-center gap-2 font-medium capitalize text-foreground">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: dotColor }} aria-hidden="true" />
                  {item.name}
                </span>
                <span className="font-mono tabular-nums text-muted-foreground">
                  <strong className="font-semibold text-foreground">{item.value}</strong> ({pct}%)
                </span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
