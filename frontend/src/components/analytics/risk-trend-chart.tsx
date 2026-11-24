"use client";

import { useReducedMotion } from "framer-motion";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisResult } from "@/types";

export function RiskTrendChart({ entries }: { entries: AnalysisResult[] }) {
  const reduceMotion = useReducedMotion();
  const data = [...entries]
    .reverse()
    .slice(-30)
    .map((entry, index) => ({
      index: index + 1,
      probability: Math.round(entry.threat_score * 100),
    }));

  const avgScore =
    data.length > 0 ? Math.round(data.reduce((sum, d) => sum + d.probability, 0) / data.length) : 0;

  return (
    <Card className="console-panel flex flex-col">
      <CardHeader className="flex-row items-center justify-between gap-2 pb-2">
        <div>
          <CardTitle className="text-base font-semibold">Threat Trend</CardTitle>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Scam likelihood across latest {data.length} scan{data.length === 1 ? "" : "s"}
          </p>
        </div>
        {data.length > 0 && (
          <span className="rounded-md border border-primary/30 bg-primary/10 px-2.5 py-1 font-mono text-xs font-medium text-primary tabular-nums">
            Avg {avgScore}%
          </span>
        )}
      </CardHeader>
      <CardContent className="h-64 flex-1 pt-2">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <AreaChart data={data} margin={{ left: -12, right: 8, top: 8, bottom: 0 }}>
            <defs>
              <linearGradient id="sgThreatArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.42} />
                <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 5" className="stroke-border/80" />
            <XAxis
              dataKey="index"
              allowDecimals={false}
              minTickGap={24}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              stroke="currentColor"
              className="text-muted-foreground"
            />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              stroke="currentColor"
              className="text-muted-foreground"
            />
            <Tooltip
              formatter={(value: number) => [`${value}%`, "Threat Score"]}
              labelFormatter={(label) => `Scan #${label}`}
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--primary) / 0.35)",
                borderRadius: "0.75rem",
                fontSize: "0.8125rem",
                boxShadow: "0 10px 30px rgba(2, 6, 23, 0.5)",
                color: "hsl(var(--foreground))",
              }}
            />
            <Area
              type="monotone"
              dataKey="probability"
              stroke="hsl(var(--primary))"
              strokeWidth={2.5}
              fill="url(#sgThreatArea)"
              dot={data.length <= 12 ? { r: 3, fill: "hsl(var(--primary))", strokeWidth: 0 } : false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "hsl(var(--background))", fill: "hsl(var(--primary))" }}
              isAnimationActive={!reduceMotion}
              animationDuration={450}
              animationEasing="ease-out"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
