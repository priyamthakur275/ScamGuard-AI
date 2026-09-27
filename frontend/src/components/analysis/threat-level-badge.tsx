import { cn } from "@/lib/utils";
import { threatLevelLabel, threatLevelColor, threatLevelBg } from "@/lib/utils";
import { Shield } from "lucide-react";

interface ThreatLevelBadgeProps {
  level: string | null | undefined;
}

export function ThreatLevelBadge({ level }: ThreatLevelBadgeProps) {
  if (!level) return null;
  const isHighThreat = level === "high" || level === "critical";

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-semibold",
        threatLevelBg(level),
        "shrink-0"
      )}
    >
      <Shield className={cn("h-4 w-4", threatLevelColor(level))} />
      <span className={threatLevelColor(level)}>{threatLevelLabel(level)} Threat</span>
    </div>
  );
}
