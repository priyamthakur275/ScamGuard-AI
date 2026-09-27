import { riskDimensionLabel, riskDimensionColor } from "@/lib/utils";

interface RiskBreakdownProps {
  breakdown: Record<string, number> | null | undefined;
}

const DIMENSION_ORDER = [
  "urgency",
  "financial_risk",
  "credential_theft",
  "identity_risk",
  "social_engineering",
  "suspicious_links",
  "malicious_tone",
];

export function RiskBreakdown({ breakdown }: RiskBreakdownProps) {
  if (!breakdown) return null;

  const dimensions = DIMENSION_ORDER.filter((key) => key in breakdown);
  if (dimensions.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-sm font-semibold text-foreground">Risk Breakdown</h4>
      <div className="flex flex-col gap-2.5">
        {dimensions.map((key) => {
          const score = breakdown[key] ?? 0;
          const pct = Math.round(score * 100);
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-24 sm:w-36 shrink-0 text-xs text-muted-foreground">
                {riskDimensionLabel(key)}
              </span>
              <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out ${riskDimensionColor(score)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-10 font-mono tabular-nums text-right text-xs font-medium text-foreground">
                {pct}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
