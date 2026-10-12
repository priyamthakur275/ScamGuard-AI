"use client";

import { useState } from "react";
import { Check, Copy, ExternalLink, Phone, Siren } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { scamCategoryLabel } from "@/lib/utils";
import type { AnalysisResult } from "@/types";
import { useLanguage } from "@/lib/i18n/language-context";

/** Official Indian reporting channels (verified Oct 2026):
 *  - Chakshu (DoT, Sanchar Saathi): suspected fraud calls/SMS/WhatsApp when no money was lost.
 *  - 1930 / cybercrime.gov.in (I4C, MHA): money already lost -- report within the "golden hour". */
const CHAKSHU = "https://sancharsaathi.gov.in/sfc/";
const CYBERCRIME = "https://cybercrime.gov.in/";

export function buildComplaint(result: AnalysisResult): string {
  const e = result.highlighted_entities ?? {};
  const lines = [
    `Suspected fraud communication - ${scamCategoryLabel(result.scam_category) || "Scam"}`,
    `Received: ${new Date(result.created_at).toLocaleString("en-IN")}`,
    `Medium: ${result.input_type ?? "Text"}`,
  ];
  const add = (label: string, items?: string[]) => items && items.length && lines.push(`${label}: ${items.join(", ")}`);
  add("Sender / phone numbers", e.phones);
  add("Links", e.urls);
  add("UPI IDs", e.upi_ids);
  add("Email addresses", e.emails);
  add("Amounts mentioned", e.payment_amounts);
  lines.push("", "Message:", (result.text.split("\n\nDetected")[0] ?? result.text).slice(0, 1200));
  lines.push("", `ScamGuard assessment: ${Math.round(result.threat_score * 100)}% scam likelihood.`);
  return lines.join("\n");
}

export function ReportScam({ result }: { result: AnalysisResult }) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  const complaint = buildComplaint(result);

  async function copy() {
    try {
      await navigator.clipboard.writeText(complaint);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: the text is visible below to copy manually */
    }
  }

  return (
    <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-5">
      <p className="flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <Siren className="h-3.5 w-3.5 text-destructive" />
        {t("rep.title")}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="border border-border bg-background/60 p-4">
          <p className="text-sm font-semibold">{t("rep.nolossTitle")}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("rep.noloss")}
          </p>
          <a href={CHAKSHU} target="_blank" rel="noopener noreferrer" className={`${buttonVariants({ variant: "outline" })} mt-3`}>
            {t("rep.openChakshu")} <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
          </a>
        </div>
        <div className="border border-border bg-background/60 p-4">
          <p className="text-sm font-semibold">{t("rep.lossTitle")}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("rep.loss")}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a href="tel:1930" className={buttonVariants({ variant: "primary" })}>
              <Phone className="mr-1.5 h-3.5 w-3.5" /> {t("rep.call")}
            </a>
            <a href={CYBERCRIME} target="_blank" rel="noopener noreferrer" className={buttonVariants({ variant: "outline" })}>
              cybercrime.gov.in <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-medium">{t("rep.details")}</summary>
        <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap border border-border bg-background p-3 text-xs">{complaint}</pre>
        <Button variant="outline" className="mt-2" onClick={copy}>
          {copied ? <Check className="mr-1.5 h-3.5 w-3.5" /> : <Copy className="mr-1.5 h-3.5 w-3.5" />}
          {copied ? t("rep.copied") : t("rep.copy")}
        </Button>
      </details>
    </div>
  );
}
