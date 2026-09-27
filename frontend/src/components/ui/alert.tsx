import type { HTMLAttributes } from "react";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

type AlertVariant = "info" | "success" | "error";

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  title?: string;
}

const variantStyles: Record<AlertVariant, { container: string; icon: JSX.Element }> = {
  info: {
    container: "border-border bg-muted text-foreground",
    icon: <Info className="h-4 w-4" aria-hidden="true" />,
  },
  success: {
    container: "border-risk-low/30 bg-risk-low/10 text-risk-low",
    icon: <CheckCircle2 className="h-4 w-4" aria-hidden="true" />,
  },
  error: {
    container: "border-destructive/30 bg-destructive/10 text-destructive",
    icon: <AlertTriangle className="h-4 w-4" aria-hidden="true" />,
  },
};

export function Alert({ className, variant = "info", title, children, ...props }: AlertProps) {
  const styles = variantStyles[variant];
  return (
    <div
      role="alert"
      className={cn("flex gap-3 rounded-md border p-3 text-sm", styles.container, className)}
      {...props}
    >
      <div className="mt-0.5 shrink-0">{styles.icon}</div>
      <div className="flex flex-col gap-0.5">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="text-sm opacity-90">{children}</div>}
      </div>
    </div>
  );
}
