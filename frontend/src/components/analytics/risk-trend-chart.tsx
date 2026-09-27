"use client";

import { useReducedMotion } from "framer-motion";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisResult } from "@/types";

export function RiskTrendChart({ entries }: { entries: AnalysisResult[] }) {
  const reduceMotion = useReducedMotion();
  const data = [...entries]
    .reverse()
    .slice(-30)
    .map((entry, index) => ({
      index: index + 1,
      probability: Math.round(entry.scam_probability * 100),
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scam probability, last {data.length} scans</CardTitle>
      </CardHeader>
      <CardContent className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid vertical={false} strokeDasharray="3 5" className="stroke-border" />
            <XAxis dataKey="index" allowDecimals={false} tick={{ fontSize: 12 }} stroke="currentColor" className="text-muted-foreground" />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 12 }}
              stroke="currentColor"
              className="text-muted-foreground"
            />
            <Tooltip
              formatter={(value: number) => [`${value}%`, "Scam probability"]}
              labelFormatter={(label) => `Scan ${label}`}
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                
                border: "1px solid hsl(var(--border) / 0.5)",
                borderRadius: "0.75rem",
                fontSize: "0.875rem",
                boxShadow: "0 8px 32px 0 rgba(0,0,0,0.36)",
                color: "hsl(var(--foreground))"
              }}
            />
            <Line 
              type="monotone" 
              dataKey="probability" 
              stroke="hsl(var(--risk-critical))" 
              strokeWidth={2} 
              dot={data.length <= 12} 
              activeDot={{ r: 6, strokeWidth: 0, fill: "hsl(var(--risk-critical))" }}
              isAnimationActive={!reduceMotion} animationDuration={400}
              animationEasing="ease-out"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
