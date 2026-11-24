"use client";

import { useEffect } from "react";
import type { LucideIcon } from "lucide-react";
import { motion, useMotionValue, useTransform, animate, useReducedMotion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
  accent?: "default" | "success" | "warning" | "destructive";
}

const accentClasses = {
  default: "bg-primary/10 text-primary border-primary/20",
  success: "bg-risk-low/10 text-risk-low border-risk-low/20",
  warning: "bg-risk-medium/10 text-risk-medium border-risk-medium/20",
  destructive: "bg-risk-high/10 text-risk-high border-risk-high/20",
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

export function StatCard({ label, value, subtitle, icon: Icon, accent = "default" }: StatCardProps) {
  return (
    <Card className="console-panel group relative overflow-hidden border border-border bg-card transition-colors duration-150 hover:border-primary/35">
      <CardContent className="flex items-center gap-4 p-5">
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-md border", accentClasses[accent])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-muted-foreground">{label}</p>
          <p className="font-sans text-2xl font-semibold tabular-nums text-foreground"><Counter value={value} /></p>
          {subtitle && <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
