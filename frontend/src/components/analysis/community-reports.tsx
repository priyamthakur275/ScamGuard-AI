"use client";

import { useState } from "react";
import { Check, Megaphone, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { reportIndicator, type IndicatorType } from "@/lib/api/community";
import { useAuth } from "@/lib/auth/auth-context";
import type { AnalysisResult } from "@/types";

interface CommunityHit {
  indicator_type: IndicatorType;
  indicator_value: string;
  display: string;
  report_count: number;
}

const ENTITY_KEYS: Array<[keyof NonNullable<AnalysisResult["highlighted_entities"]>, IndicatorType]> = [
  ["phones", "phone"],
  ["urls", "url"],
  ["upi_ids", "upi"],
  ["emails", "email"],
];

/** "Reported by N users" for the scan's numbers/links, plus a one-click
 * report so the next person who checks the same number is warned. */
export function CommunityReports({ result }: { result: AnalysisResult }) {
  const { isAuthenticated } = useAuth();
  const hits = (result.metadata?.community_reports as CommunityHit[] | undefined) ?? [];
  const indicators = ENTITY_KEYS.flatMap(([key, type]) =>
    ((result.highlighted_entities?.[key] as string[] | undefined) ?? []).map((value) => ({ type, value })),
  ).slice(0, 10);
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");
  const canReport = isAuthenticated && result.verdict !== "legitimate" && indicators.length > 0 && !result.metadata?.is_quick_check;

  if (hits.length === 0 && !canReport) return null;

  async function reportAll() {
    setState("sending");
    try {
      await Promise.all(indicators.map((i) => reportIndicator(i.type, i.value, result.scam_category)));
      setState("done");
    } catch {
      setState("error");
    }
  }

  return (
    <div className="border border-border p-5">
      <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <Users className="h-3.5 w-3.5 text-primary" />
        Community reports
      </p>
      {hits.length > 0 ? (
        <ul className="space-y-1.5 text-sm">
          {hits.map((h) => (
            <li key={`${h.indicator_type}-${h.indicator_value}`}>
              <span className="font-mono">{h.display}</span>{" "}
              <span className={h.report_count >= 2 ? "font-semibold text-destructive" : "text-muted-foreground"}>
                reported as a scam by {h.report_count} {h.report_count === 1 ? "user" : "users"}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">Nobody has reported the numbers or links in this message yet.</p>
      )}
      {canReport && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button variant="outline" onClick={reportAll} isLoading={state === "sending"} disabled={state === "done"}>
            {state === "done" ? <Check className="mr-1.5 h-4 w-4" /> : <Megaphone className="mr-1.5 h-4 w-4" />}
            {state === "done" ? "Reported — thank you" : `Warn others (${indicators.length} ${indicators.length === 1 ? "item" : "items"})`}
          </Button>
          {state === "error" && <span className="text-xs text-destructive">Could not send the report. Try again.</span>}
          <span className="text-xs text-muted-foreground">Each person counts once. Scores rise only after 2+ independent reports.</span>
        </div>
      )}
    </div>
  );
}
