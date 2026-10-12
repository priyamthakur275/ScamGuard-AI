import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "destructive" | "outline";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-secondary text-secondary-foreground",
  success: "bg-risk-low/15 text-risk-low",
  warning: "bg-risk-medium/15 text-risk-medium",
  destructive: "bg-risk-high/15 text-risk-high",
  outline: "text-foreground",
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        variant === "outline" ? "border-border" : "border-transparent",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
