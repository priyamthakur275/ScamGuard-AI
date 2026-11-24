"use client";

import { useReducedMotion } from "framer-motion";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CdAdaptationRow } from "@/lib/api/public";

const SERIES = [
  { key: "lrWord", name: "LogReg · word", color: "hsl(var(--primary))", dash: undefined },
  { key: "lrChar", name: "LogReg · char", color: "#2DD4BF", dash: "5 4" },
  { key: "nbWord", name: "Naive Bayes · word", color: "hsl(var(--destructive))", dash: undefined },
  { key: "nbChar", name: "Naive Bayes · char", color: "hsl(var(--caution))", dash: "5 4" },
];

const KEY: Record<string, string> = {
  "logistic_regression|word": "lrWord",
  "naive_bayes|word": "nbWord",
  "logistic_regression|char": "lrChar",
  "naive_bayes|char": "nbChar",
};

/** Mean spam F1 on the Indian final test set as labelled Indian messages are added (3 seeds). */
export default function AdaptationChart({ rows }: { rows: CdAdaptationRow[] }) {
  const reduceMotion = useReducedMotion();
  const fractions = Array.from(new Set(rows.filter((r) => r.target_fraction < 1).map((r) => r.target_fraction))).sort((a, b) => a - b);
  const data = fractions.map((f) => {
    const point: Record<string, number | string> = { added: `${Math.round(f * 100)}%` };
    for (const r of rows.filter((x) => x.target_fraction === f)) {
      point[KEY[`${r.model}|${r.feature}`] ?? "x"] = Number(r.B_f1_mean.toFixed(4));
    }
    return point;
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: -10 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 5" stroke="hsl(var(--border))" strokeOpacity={0.6} />
        <XAxis
          dataKey="added"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          stroke="hsl(var(--muted-foreground))"
        />
        <YAxis
          domain={[0.5, 1]}
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
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
        {SERIES.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeDasharray={s.dash}
            strokeWidth={2.25}
            dot={{ r: 3, strokeWidth: 0, fill: s.color }}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "hsl(var(--background))" }}
            isAnimationActive={!reduceMotion}
            animationDuration={400}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
