import { Badge } from "@/components/ui/badge";
import { riskLevelLabel } from "@/lib/utils";
import type { RiskLevel } from "@/types";

const VARIANT_MAP = {
  low: "success",
  medium: "warning",
  high: "destructive",
} as const;

export function RiskBadge({ level }: { level: RiskLevel }) {
  return <Badge variant={VARIANT_MAP[level] ?? "default"}>{riskLevelLabel(level)}</Badge>;
}

const THREAT_VARIANT = {
  very_low: "success",
  low: "success",
  medium: "warning",
  high: "destructive",
  critical: "destructive",
} as const;

const THREAT_LABEL: Record<string, string> = {
  very_low: "Very low",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

/** Compact badge for list rows. Shows the threat level (what the verdict
 * card and history table display), falling back to the model risk level
 * for older scans that have no threat level. */
export function ThreatBadge({ threatLevel, riskLevel }: { threatLevel?: string | null; riskLevel: RiskLevel }) {
  if (!threatLevel || !(threatLevel in THREAT_VARIANT)) return <RiskBadge level={riskLevel} />;
  const key = threatLevel as keyof typeof THREAT_VARIANT;
  return (
    <Badge variant={THREAT_VARIANT[key]} className={key === "critical" ? "bg-risk-critical/15 text-risk-critical" : undefined}>
      {THREAT_LABEL[key]} threat
    </Badge>
  );
}
