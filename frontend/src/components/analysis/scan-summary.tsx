import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { cn, formatPercent, scamCategoryLabel } from "@/lib/utils";
import { ThreatLevelBadge } from "./threat-level-badge";
import type { AnalysisResult } from "@/types";

interface ScanSummaryProps {
  result: AnalysisResult;
}

function getScanStatus(result: AnalysisResult) {
  const tl = result.threat_level;
  if (tl === "critical") {
    return {
      label: "Critical Threat",
      note: "Strong scam indicators detected. Do not engage, click links, or share credentials.",
      icon: ShieldAlert,
      colorClass: "text-risk-critical bg-risk-critical/10 border-risk-critical/35",
    };
  }
  if (tl === "high") {
    return {
      label: "High Risk",
      note: "Multiple scam signals detected. Verify independently before taking any action.",
      icon: ShieldAlert,
      colorClass: "text-risk-high bg-risk-high/10 border-risk-high/35",
    };
  }
  if (result.verdict === "legitimate") {
    if (tl === "medium") {
      return {
        label: "Moderate Risk",
        note: "Some caution signals found. Double-check sender identity before responding.",
        icon: ShieldQuestion,
        colorClass: "text-risk-medium bg-risk-medium/10 border-risk-medium/35",
      };
    }
    return {
      label: tl === "low" ? "Low Risk · Looks Genuine" : "Looks Genuine · No Scam Signals",
      note: "No strong scam indicators found — still never share OTPs, PINs, or remote access.",
      icon: ShieldCheck,
      colorClass: "text-risk-low bg-risk-low/10 border-risk-low/35",
    };
  }
  return {
    label: "Suspicious · Review Carefully",
    note: "Shows questionable cues. Inspect the Scam X-Ray and TrustLens evidence below.",
    icon: ShieldQuestion,
    colorClass: "text-risk-medium bg-risk-medium/10 border-risk-medium/35",
  };
}

export function ScanSummary({ result }: ScanSummaryProps) {
  const status = getScanStatus(result);
  const StatusIcon = status.icon;

  return (
    <div className={cn("flex flex-wrap items-center gap-4 rounded-xl border p-4 sm:px-5", status.colorClass)}>
      <StatusIcon className="h-7 w-7 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5">
          <p className="text-lg font-bold leading-tight">{status.label}</p>
          <span className="font-mono text-xs opacity-85">
            {formatPercent(result.threat_score)} scam likelihood
            {result.scam_category ? ` · ${scamCategoryLabel(result.scam_category)}` : ""}
          </span>
        </div>
        <p className="mt-1 text-xs opacity-90">{status.note}</p>
      </div>
      <ThreatLevelBadge level={result.threat_level} />
    </div>
  );
}
