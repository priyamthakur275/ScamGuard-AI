"use client";

import { AlertTriangle } from "lucide-react";
import { useLanguage } from "@/lib/i18n/language-context";
import { needsReview } from "@/lib/utils";

/** Shown when the final score is in the uncertain band; renders nothing otherwise. */
export function ReviewBand({ threatScore, className = "" }: { threatScore: number; className?: string }) {
  const { t } = useLanguage();
  if (!needsReview(threatScore)) return null;
  return (
    <div role="status" data-testid="review-band" className={`flex items-start gap-3 border border-risk-medium/50 bg-risk-medium/10 p-3 ${className}`}>
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-risk-medium" aria-hidden="true" />
      <div>
        <p className="text-sm font-semibold text-foreground">{t("review.title")}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{t("review.body")}</p>
      </div>
    </div>
  );
}
