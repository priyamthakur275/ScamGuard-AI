"use client";

import { useReducedMotion } from "framer-motion";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function DailyChart({ daily }: { daily: { date: string; total: number; flagged: number }[] }) {
  const reduceMotion = useReducedMotion();
  const chartData = daily.map((d) => ({ ...d, label: d.date.slice(5) }));

  return (
    <ResponsiveContainer width="100%" height={280} minWidth={0}>
      <AreaChart data={chartData} margin={{ top: 8, right: 12, left: -14, bottom: 0 }}>
        <defs>
          <linearGradient id="sgTrendTotal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="sgTrendFlagged" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--destructive))" stopOpacity={0.34} />
            <stop offset="100%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} strokeDasharray="3 5" stroke="hsl(var(--border))" strokeOpacity={0.6} />
        <XAxis
          dataKey="label"
          minTickGap={22}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          stroke="hsl(var(--muted-foreground))"
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          stroke="hsl(var(--muted-foreground))"
        />
        <Tooltip
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
          dataKey="total"
          name="Checked"
          stroke="hsl(var(--primary))"
          strokeWidth={2.25}
          fill="url(#sgTrendTotal)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 2, stroke: "hsl(var(--background))", fill: "hsl(var(--primary))" }}
          isAnimationActive={!reduceMotion}
          animationDuration={450}
        />
        <Area
          type="monotone"
          dataKey="flagged"
          name="Scams"
          stroke="hsl(var(--destructive))"
          strokeWidth={2}
          fill="url(#sgTrendFlagged)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 2, stroke: "hsl(var(--background))", fill: "hsl(var(--destructive))" }}
          isAnimationActive={!reduceMotion}
          animationDuration={450}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
