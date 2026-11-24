"use client";

import { useReducedMotion } from "framer-motion";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { inputTypeLabel } from "@/lib/utils";

const CHANNEL_COLORS = [
  "hsl(var(--primary))",
  "#8B5CF6",
  "hsl(var(--caution))",
  "#2DD4BF",
  "hsl(var(--destructive))",
  "hsl(var(--safe))",
];

export default function SourceDonutChart({
  channels,
}: {
  channels: { input_type: string; count: number }[];
}) {
  const reduceMotion = useReducedMotion();
  const sorted = channels
    .filter((c) => c.count > 0)
    .slice()
    .sort((a, b) => b.count - a.count);

  if (sorted.length === 0) {
    return <p className="mt-3 text-sm text-muted-foreground">No data yet.</p>;
  }

  const total = sorted.reduce((acc, c) => acc + c.count, 0);

  return (
    <div className="mt-4 grid items-center gap-6 sm:grid-cols-[176px_minmax(0,1fr)]">
      <div className="relative mx-auto h-44 w-44 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={sorted}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={74}
              paddingAngle={sorted.length > 1 ? 3 : 0}
              stroke="none"
              dataKey="count"
              nameKey="input_type"
              isAnimationActive={!reduceMotion}
              animationDuration={400}
            >
              {sorted.map((entry, idx) => (
                <Cell key={entry.input_type} fill={CHANNEL_COLORS[idx % CHANNEL_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [value, inputTypeLabel(name)]}
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--primary) / 0.35)",
                borderRadius: "0.75rem",
                fontSize: "0.8125rem",
                color: "hsl(var(--foreground))",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="font-display text-2xl font-bold tabular-nums text-foreground">
            {total.toLocaleString("en-IN")}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Sources</span>
        </div>
      </div>

      <ul className="space-y-2.5">
        {sorted.map((c, idx) => {
          const pct = total > 0 ? Math.round((c.count / total) * 100) : 0;
          const color = CHANNEL_COLORS[idx % CHANNEL_COLORS.length];
          return (
            <li key={c.input_type} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/45 px-3 py-2 text-xs">
              <span className="flex items-center gap-2 font-medium text-foreground">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} aria-hidden="true" />
                {inputTypeLabel(c.input_type)}
              </span>
              <span className="font-mono tabular-nums text-muted-foreground">
                <strong className="font-semibold text-foreground">{c.count.toLocaleString("en-IN")}</strong> · {pct}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
