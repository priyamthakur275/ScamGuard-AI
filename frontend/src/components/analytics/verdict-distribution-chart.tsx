"use client";

import { useReducedMotion } from "framer-motion";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS: Record<string, string> = {
  legitimate: "hsl(var(--risk-low))",
  spam: "hsl(var(--risk-medium))",
  phishing: "hsl(var(--risk-high))",
  scam: "hsl(var(--risk-critical))",
};

interface Props {
  /** Pre-aggregated verdict -> count, from the real server-side summary --
   * never computed client-side from a paginated page of history. */
  distribution: Record<string, number>;
}

export function VerdictDistributionChart({ distribution }: Props) {
  const reduceMotion = useReducedMotion();
  const data = Object.entries(distribution).map(([verdict, count]) => ({ verdict, count }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Verdict distribution</CardTitle>
      </CardHeader>
      <CardContent className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid vertical={false} strokeDasharray="3 5" className="stroke-border" />
            <XAxis dataKey="verdict" tickFormatter={(v: string) => v.charAt(0).toUpperCase() + v.slice(1)} tick={{ fontSize: 12 }} stroke="currentColor" className="text-muted-foreground" />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="currentColor" className="text-muted-foreground" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                fontSize: "0.875rem",
                color: "hsl(var(--foreground))",
              }}
              cursor={{ fill: "hsl(var(--muted)/0.4)" }}
            />
            <Bar dataKey="count" name="Scans" maxBarSize={72} radius={[3, 3, 0, 0]} isAnimationActive={!reduceMotion} animationDuration={400} animationEasing="ease-out">
              {data.map((entry) => (
                <Cell key={entry.verdict} fill={COLORS[entry.verdict] ?? "hsl(var(--primary))"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
