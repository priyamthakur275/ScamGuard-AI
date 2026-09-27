"use client";

import { useReducedMotion } from "framer-motion";

import { useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS: Record<string, string> = {
  legitimate: "hsl(var(--risk-low))",
  spam: "hsl(var(--risk-medium))",
  phishing: "hsl(var(--risk-high))",
  scam: "hsl(var(--risk-critical))",
};

interface Props {
  /** Pre-aggregated verdict -> count, from the real server-side summary. */
  distribution: Record<string, number>;
}

export function ThreatDistributionPieChart({ distribution }: Props) {
  const reduceMotion = useReducedMotion();
  const data = useMemo(
    () => Object.entries(distribution).filter(([, value]) => value > 0).map(([name, value]) => ({ name, value })),
    [distribution],
  );

  if (data.length === 0) return null;

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle>Verdict share</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 pb-4">
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={data.length > 1 ? 3 : 0}
                stroke="none"
                dataKey="value"
                nameKey="name"
                isAnimationActive={!reduceMotion} animationDuration={400}
                animationEasing="ease-out"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.name] || "hsl(var(--muted-foreground))"} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                }}
                itemStyle={{ color: "hsl(var(--foreground))", textTransform: "capitalize" }}
              />
              <Legend formatter={(value) => <span className="capitalize">{value}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
