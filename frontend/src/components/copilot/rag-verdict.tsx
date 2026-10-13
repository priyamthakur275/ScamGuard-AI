"use client";

import { useEffect, useId, useState } from "react";
import { AlertTriangle, ExternalLink, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { cn, scamCategoryLabel } from "@/lib/utils";
import type { Citation, CragVerdict, RetrievalGrade, RiskTier } from "@/lib/copilot/types";

const TIER_STYLE: Record<RiskTier, { badge: string; stroke: string; text: string }> = {
  High: { badge: "border-risk-high/40 bg-risk-high/15 text-risk-high", stroke: "hsl(var(--risk-high))", text: "text-risk-high" },
  Medium: { badge: "border-risk-medium/40 bg-risk-medium/15 text-risk-medium", stroke: "hsl(var(--risk-medium))", text: "text-risk-medium" },
  Low: { badge: "border-risk-low/40 bg-risk-low/15 text-risk-low", stroke: "hsl(var(--risk-low))", text: "text-risk-low" },
};

const GRADE_LABEL: Record<RetrievalGrade, string> = {
  CORRECT: "Matches known scams",
  AMBIGUOUS: "Partial match",
  INCORRECT: "No verified match",
};

export function RiskTierBadge({ tier, className }: { tier: RiskTier; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold", TIER_STYLE[tier].badge, className)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {tier} risk
    </span>
  );
}

/** Circular fraud-index gauge. Hover or focus shows the model / confidence breakdown. */
export function FraudGauge({ verdict, size = 132 }: { verdict: CragVerdict; size?: number }) {
  const tipId = useId();
  const [shown, setShown] = useState(0);
  const [hover, setHover] = useState(false);
  const value = Math.max(0, Math.min(100, Math.round(verdict.fraud_index)));

  useEffect(() => {
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setShown(value);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 800);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const style = TIER_STYLE[verdict.risk_tier];

  return (
    <div
      className="relative shrink-0 outline-none"
      style={{ width: size, height: size }}
      tabIndex={0}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      aria-label={`Fraud index ${value} percent`}
      aria-describedby={tipId}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="hsl(var(--border))" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={style.stroke}
          strokeWidth={hover ? stroke + 2 : stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c - (shown / 100) * c}
          style={{ transition: "stroke-width 150ms" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className={cn("text-3xl font-bold tabular-nums", style.text)}>{shown}%</span>
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">fraud index</span>
      </div>
      <div
        id={tipId}
        role="tooltip"
        className={cn(
          "pointer-events-none absolute left-1/2 top-full z-10 mt-2 w-52 -translate-x-1/2 rounded-lg border border-border bg-card p-2.5 text-xs text-card-foreground shadow-lg transition-opacity",
          hover ? "opacity-100" : "opacity-0",
        )}
      >
        <p>Model probability: <b>{verdict.model_probability}%</b></p>
        <p>Verdict confidence: <b>{verdict.confidence_percentage}%</b></p>
        <p>Knowledge match: <b>{Math.round(verdict.retrieval_confidence * 100)}%</b></p>
      </div>
    </div>
  );
}

function CitationCard({ c, active, onSelect }: { c: Citation; active: boolean; onSelect: () => void }) {
  const pct = Math.round(c.relevance * 100);
  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border p-3 text-left transition-colors",
        active ? "border-primary bg-primary/5" : "border-border hover:border-primary/60",
      )}
    >
      <button type="button" onClick={onSelect} aria-expanded={active} className="text-left">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-snug">{c.title}</p>
          <span className="shrink-0 font-mono text-xs text-muted-foreground">{pct}%</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1.5 text-xs text-muted-foreground">{scamCategoryLabel(c.scam_type)}</p>
      </button>
      {active && (
        <div className="mt-2 space-y-1.5 border-t border-border pt-2 text-xs text-muted-foreground">
          <p>{c.what_happens_next}</p>
          <p className="font-mono">
            text {Math.round(c.vector_score * 100)} · words {Math.round(c.keyword_score * 100)} · tactics {Math.round(c.tactic_score * 100)}
          </p>
        </div>
      )}
      <a
        href={c.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
      >
        {c.source_name} <ExternalLink className="h-3 w-3" />
      </a>
    </div>
  );
}

export function CitationGrid({ citations, compact = false }: { citations: Citation[]; compact?: boolean }) {
  const [active, setActive] = useState<string | null>(null);
  if (!citations.length) return null;
  return (
    <div className={cn("grid gap-2", compact ? "grid-cols-1" : "sm:grid-cols-2 lg:grid-cols-3")}>
      {citations.map((c) => (
        <CitationCard key={c.kb_id} c={c} active={active === c.kb_id} onSelect={() => setActive(active === c.kb_id ? null : c.kb_id)} />
      ))}
    </div>
  );
}

/** Full verdict layout: gauge, badges, tactics and the retrieved citations. */
export function RagVerdict({ verdict, compact = false }: { verdict: CragVerdict; compact?: boolean }) {
  const Icon = verdict.is_scam ? ShieldAlert : ShieldCheck;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <FraudGauge verdict={verdict} size={compact ? 108 : 132} />
        <div className="min-w-0 flex-1 space-y-2">
          <p className={cn("flex items-center gap-2 font-semibold", compact ? "text-base" : "text-lg", verdict.is_scam ? "text-risk-high" : "text-risk-low")}>
            <Icon className="h-5 w-5 shrink-0" />
            {verdict.is_scam ? `Likely scam${verdict.scam_type ? ` · ${scamCategoryLabel(verdict.scam_type)}` : ""}` : "Looks genuine"}
          </p>
          <div className="flex flex-wrap gap-1.5">
            <RiskTierBadge tier={verdict.risk_tier} />
            <span className="inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground">
              {GRADE_LABEL[verdict.retrieval_grade]}
            </span>
            {verdict.emerging_threat && (
              <span className="inline-flex items-center gap-1 rounded-full border border-risk-medium/40 bg-risk-medium/15 px-2.5 py-0.5 text-xs font-semibold text-risk-medium">
                <AlertTriangle className="h-3 w-3" /> Emerging threat
              </span>
            )}
            {verdict.verdict_source === "llm_reviewed" && (
              <span className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground">
                <Sparkles className="h-3 w-3" /> AI-reviewed
              </span>
            )}
          </div>
        </div>
      </div>

      {verdict.matched_tactics.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">Tactics found</p>
          <ul className="flex flex-wrap gap-1.5">
            {verdict.matched_tactics.map((t) => (
              <li key={t.id} title={t.evidence ? `"${t.evidence}"` : undefined} className="rounded-md border border-border bg-muted/40 px-2 py-1 text-xs">
                {t.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      {verdict.citation_links.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">Similar known scams</p>
          <CitationGrid compact={compact} citations={compact ? verdict.citation_links.slice(0, 2) : verdict.citation_links} />
        </div>
      )}

      {verdict.notes.length > 0 && (
        <ul className="space-y-1 text-xs text-muted-foreground">
          {verdict.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
