"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function DailyChart({ daily }: { daily: { date: string; total: number; flagged: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={daily.map((d) => ({ ...d, label: d.date.slice(5) }))}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey="label" fontSize={11} stroke="hsl(var(--muted-foreground))" />
        <YAxis allowDecimals={false} fontSize={11} stroke="hsl(var(--muted-foreground))" />
        <Tooltip contentStyle={{ background: "hsl(var(--background))", border: "1px solid hsl(var(--border))" }} />
        <Line type="monotone" dataKey="total" name="Checked" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="flagged" name="Scams" stroke="hsl(var(--destructive))" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
