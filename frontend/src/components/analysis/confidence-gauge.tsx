"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { motion, useMotionValue, useTransform, animate, useReducedMotion } from "framer-motion";

interface ConfidenceGaugeProps {
  value: number; // 0-1
  size?: number;
}

export function ConfidenceGauge({ value, size = 120 }: ConfidenceGaugeProps) {
  const reducedMotion = useReducedMotion();
  const [animated, setAnimated] = useState(false);
  
  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(value, 0), 1);
  const targetOffset = circumference - progress * circumference;
  
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => Math.round(latest * 100));

  useEffect(() => {
    const controls = animate(count, progress, { duration: reducedMotion ? 0 : 0.6, ease: "easeOut" });
    return controls.stop;
  }, [progress, count, reducedMotion]);

  const color = "stroke-primary";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth={strokeWidth}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: animated ? targetOffset : circumference }}
            transition={{ duration: reducedMotion ? 0 : 0.6, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span className="text-2xl font-bold text-foreground">
            {rounded}
          </motion.span>
          <span className="text-2xl font-bold text-foreground absolute ml-12">%</span>
        </div>
      </div>
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Confidence</span>
    </div>
  );
}
