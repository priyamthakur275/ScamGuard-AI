"use client";

import { useEffect } from "react";
import type { LucideIcon } from "lucide-react";
import { motion, useMotionValue, useTransform, animate, useReducedMotion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  accent?: "default" | "success" | "warning" | "destructive";
}

const accentClasses = {
  default: "bg-primary/10 text-primary",
  success: "bg-risk-low/10 text-risk-low",
  warning: "bg-risk-medium/10 text-risk-medium",
  destructive: "bg-risk-high/10 text-risk-high",
};

function Counter({ value }: { value: string }) {
  const numValue = parseFloat(value.replace(/[^0-9.]/g, ""));
  const hasPercent = value.includes("%");
  // Keep the precision of the formatted input ("98%" animates to "98%",
  // never "98.0%"), so the settled number matches the rest of the app.
  const decimals = (value.split(".")[1]?.match(/^\d+/)?.[0].length) ?? 0;
  const isDash = value === "—";
  const reduceMotion = useReducedMotion();

  const count = useMotionValue(reduceMotion ? numValue : 0);
  const display = useTransform(count, (latest) => `${latest.toFixed(decimals)}${hasPercent ? "%" : ""}`);

  useEffect(() => {
    if (isDash || isNaN(numValue)) return;
    if (reduceMotion) {
      count.set(numValue);
      return;
    }
    const controls = animate(count, numValue, { duration: 0.6, ease: "easeOut" });
    return controls.stop;
  }, [numValue, isDash, count, reduceMotion]);

  if (isDash || isNaN(numValue)) return <>{value}</>;

  return <motion.span aria-label={value}>{display}</motion.span>;
}

export function StatCard({ label, value, icon: Icon, accent = "default" }: StatCardProps) {
  return (
    <Card className="group relative overflow-hidden border border-border bg-card">
      <CardContent className="flex items-center gap-4 p-5">
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-transparent", accentClasses[accent])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="font-sans text-2xl font-semibold text-foreground"><Counter value={value} /></p>
        </div>
      </CardContent>
    </Card>
  );
}
