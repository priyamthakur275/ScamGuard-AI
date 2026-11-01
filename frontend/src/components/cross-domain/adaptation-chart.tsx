"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CdAdaptationRow } from "@/lib/api/public";

const SERIES = [
  { key: "lrWord", name: "Logistic Regression, word", color: "hsl(var(--primary))", dash: undefined },
  { key: "nbWord", name: "Naive Bayes, word", color: "hsl(var(--destructive))", dash: undefined },
  { key: "lrChar", name: "Logistic Regression, char", color: "hsl(var(--primary))", dash: "5 4" },
  { key: "nbChar", name: "Naive Bayes, char", color: "hsl(var(--destructive))", dash: "5 4" },
];

const KEY: Record<string, string> = { "logistic_regression|word": "lrWord", "naive_bayes|word": "nbWord", "logistic_regression|char": "lrChar", "naive_bayes|char": "nbChar" };

/** Mean spam F1 on the Indian final test set as labelled Indian messages are added (3 seeds). */
export default function AdaptationChart({ rows }: { rows: CdAdaptationRow[] }) {
  const fractions = Array.from(new Set(rows.filter((r) => r.target_fraction < 1).map((r) => r.target_fraction))).sort((a, b) => a - b);
  const data = fractions.map((f) => {
    const point: Record<string, number | string> = { added: `${Math.round(f * 100)}%` };
    for (const r of rows.filter((x) => x.target_fraction === f)) point[KEY[`${r.model}|${r.feature}`] ?? "x"] = Number(r.B_f1_mean.toFixed(4));
    return point;
  });
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey="added" fontSize={11} stroke="hsl(var(--muted-foreground))" />
        <YAxis domain={[0.5, 1]} fontSize={11} stroke="hsl(var(--muted-foreground))" />
        <Tooltip contentStyle={{ background: "hsl(var(--background))", border: "1px solid hsl(var(--border))" }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {SERIES.map((s) => (
          <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color} strokeDasharray={s.dash} strokeWidth={2} dot isAnimationActive={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
