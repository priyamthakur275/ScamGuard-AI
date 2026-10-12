"use client";

import { useState } from "react";
import { Copy, MessageCircle, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";

export function displayToken(token: string): string {
  return token.replace(/__url__/g, "link").replace(/__num__/g, "number");
}

/** Plain-text warning a user can forward to family or a group chat. */
export function buildWarningText(result: AnalysisResult): string {
  const category = result.scam_category ? scamCategoryLabel(result.scam_category).toLowerCase() : "scam";
  const score = Math.round(result.threat_score * 100);
  const signs = (result.top_contributing_tokens ?? []).slice(0, 3).map((t) => displayToken(t.token));
  const lines = [
    `⚠️ Scam alert (checked with ScamGuard)`,
    `This message looks like a ${category} attempt — threat score ${score}/100.`,
  ];
  if (signs.length) lines.push(`Warning signs: ${signs.join(", ")}.`);
  lines.push(
    "Do not click its links, share any OTP/PIN, or send money.",
    "Report it at cybercrime.gov.in or call 1930.",
  );
  return lines.join("\n");
}

export function ShareWarning({ result }: { result: AnalysisResult }) {
  const [copied, setCopied] = useState(false);
  const text = buildWarningText(result);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="outline"
        onClick={() => window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer")}
      >
        <MessageCircle className="mr-1.5 h-4 w-4" aria-hidden="true" />
        Share warning
      </Button>
      <Button variant="ghost" onClick={copy} aria-label="Copy warning text">
        {copied ? <Check className="mr-1.5 h-4 w-4" aria-hidden="true" /> : <Copy className="mr-1.5 h-4 w-4" aria-hidden="true" />}
        {copied ? "Copied" : "Copy"}
      </Button>
    </div>
  );
}
