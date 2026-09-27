import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThreatLevelBadge } from "./threat-level-badge";
import { formatPercent, scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";

interface ScanSummaryProps {
  result: AnalysisResult;
}

function getScanStatus(result: AnalysisResult) {
  const tl = result.threat_level;
  if (tl === "critical") return { label: "Critical Threat", icon: ShieldAlert, colorClass: "text-risk-critical bg-risk-critical/10 border-risk-critical/30" };
  if (tl === "high") return { label: "High Risk", icon: ShieldAlert, colorClass: "text-risk-high bg-risk-high/10 border-risk-high/30" };
  if (result.verdict === "legitimate") {
    if (tl === "medium") return { label: "Moderate Risk", icon: ShieldQuestion, colorClass: "text-risk-medium bg-risk-medium/10 border-risk-medium/30" };
    if (tl === "low") return { label: "Low Risk", icon: ShieldCheck, colorClass: "text-risk-low bg-risk-low/10 border-risk-low/30" };
    return { label: "Safe", icon: ShieldCheck, colorClass: "text-risk-low bg-risk-low/10 border-risk-low/30" };
  }
  return { label: "Suspicious", icon: ShieldQuestion, colorClass: "text-risk-medium bg-risk-medium/10 border-risk-medium/30" };
}

export function ScanSummary({ result }: ScanSummaryProps) {
  const status = getScanStatus(result);
  const StatusIcon = status.icon;

  return (
    <div className={cn("flex flex-wrap items-center gap-4 rounded-xl border p-4", status.colorClass)}>
      <StatusIcon className="h-8 w-8" aria-hidden="true" />
      <div className="flex-1">
        <p className="text-lg font-bold">{status.label}</p>
        <p className="text-sm opacity-80">
          {formatPercent(result.scam_probability)} scam probability
          {result.scam_category ? ` · ${scamCategoryLabel(result.scam_category)}` : ""}
        </p>
      </div>
      <ThreatLevelBadge level={result.threat_level} />
    </div>
  );
}
