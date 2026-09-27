import { GitCompare } from "lucide-react";
import type { CorrelationSignal } from "@/types";

interface CorrelationPanelProps {
  correlation: CorrelationSignal[] | null | undefined;
}

const SEVERITY_LABEL: Record<string, string> = { low: "Low", medium: "Medium", high: "High" };

/** Renders the backend's own correlation evidence directly -- every line
 * here compares this scan against the SAME user's own past scans (see
 * correlation_service.py). This is never an external threat-intelligence
 * or reputation claim; it only answers "have you seen this before".
 */
export function CorrelationPanel({ correlation }: CorrelationPanelProps) {
  if (!correlation || correlation.length === 0) return null;

  return (
    <div className="border border-border p-5">
      <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <GitCompare className="h-3.5 w-3.5 text-primary" />
        Correlation with your past scans
      </p>
      <ul className="flex flex-col gap-2">
        {correlation.map((signal, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span className="mt-0.5 shrink-0 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              [{SEVERITY_LABEL[signal.severity] ?? signal.severity}]
            </span>
            <span className="text-muted-foreground">{signal.reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
