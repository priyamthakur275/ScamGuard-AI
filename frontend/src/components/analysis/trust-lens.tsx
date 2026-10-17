"use client";

import { useState } from "react";
import { AlertTriangle, BookOpen, CheckCircle2, ChevronDown, CircleDashed, ExternalLink, Info, ListChecks, ScanEye, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { parseTrustLens, type TlStage, type TrustLensReport } from "@/lib/trustlens";
import type { AnalysisResult } from "@/types";

const pct = (v: number | null) => (v === null ? "Not available" : `${Math.round(v * 100)}%`);
const human = (id: string) => id.replace(/_/g, " ");

function Scores({ r }: { r: TrustLensReport }) {
  const items = [
    { label: "Classifier probability", value: pct(r.classifier_probability), hint: "What the trained text model alone says, before any rules." },
    { label: "Risk score (final)", value: pct(r.risk_score), hint: "The model combined with matched scam and protective phrases. The verdict uses this." },
  ];
  return (
    <dl className="grid grid-cols-2 gap-2">
      {items.map((i) => (
        <div key={i.label} className="rounded-xl border border-border p-3">
          <dt className="text-xs text-muted-foreground">{i.label}</dt>
          <dd className="font-mono text-lg font-semibold">{i.value}</dd>
          <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">{i.hint}</p>
        </div>
      ))}
    </dl>
  );
}

function Journey({ stages, uid }: { stages: TlStage[]; uid: string }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section aria-labelledby={`${uid}-journey`} className="space-y-3">
      <h4 id={`${uid}-journey`} className="text-sm font-semibold">Scam journey</h4>
      <ol className="grid gap-2 sm:grid-cols-4">
        {stages.map((s, i) => {
          const isOpen = open === s.stage;
          const body = (
            <>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className={cn("inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold",
                  s.detected ? "bg-destructive text-destructive-foreground" : "border border-border")}>{i + 1}</span>
                {s.detected ? `${s.evidence.length} sign${s.evidence.length > 1 ? "s" : ""}` : "Not detected"}
              </span>
              <span className={cn("mt-1 block font-medium", !s.detected && "text-muted-foreground")}>{s.name}</span>
              <span className="block text-[11px] leading-snug text-muted-foreground">{s.meaning}</span>
            </>
          );
          return (
            <li key={s.stage}>
              {s.detected ? (
                <button type="button" onClick={() => setOpen(isOpen ? null : s.stage)} aria-expanded={isOpen} aria-controls={`${uid}-${s.stage}`}
                  className={cn("w-full rounded-xl border p-3 text-left text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                    isOpen ? "border-destructive bg-destructive/10" : "border-destructive/40 hover:bg-destructive/5")}>
                  {body}
                  <ChevronDown className={cn("mt-1 h-4 w-4 text-muted-foreground transition-transform", isOpen && "rotate-180")} aria-hidden />
                </button>
              ) : (
                <div className="h-full rounded-xl border border-dashed border-border p-3 text-sm">{body}</div>
              )}
            </li>
          );
        })}
      </ol>
      {stages.filter((s) => s.stage === open).map((s) => (
        <div key={s.stage} id={`${uid}-${s.stage}`} className="space-y-2 rounded-xl border border-destructive/30 bg-destructive/5 p-3">
          {s.evidence.map((e, i) => (
            <div key={i} className="text-sm">
              <p><span className="font-medium">{e.label}</span> <span className="text-muted-foreground">“{e.phrase}”</span></p>
              {e.why && <p className="text-foreground/80">{e.why}</p>}
            </div>
          ))}
        </div>
      ))}
      <p className="text-[11px] text-muted-foreground">Stages are marked only when a matching phrase was found. &ldquo;Not detected&rdquo; means no phrase matched, not that the stage is impossible.</p>
    </section>
  );
}

function Evidence({ r, uid }: { r: TrustLensReport; uid: string }) {
  return (
    <section aria-labelledby={`${uid}-evidence`} className="space-y-3">
      <h4 id={`${uid}-evidence`} className="text-sm font-semibold">Evidence and uncertainty</h4>
      {(r.uncertainty.conflicting || r.uncertainty.insufficient) && (
        <p className="flex gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm" role="note">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden />
          {r.uncertainty.conflicting
            ? "The evidence conflicts: the message has both scam signs and reassuring phrases."
            : "There is not enough specific evidence to explain this result; it comes from the classifier's word patterns alone."}
        </p>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-border p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Supports a scam assessment</p>
          {r.evidence_for.length === 0 ? <p className="text-sm text-muted-foreground">No scam phrase matched.</p> : (
            <ul className="space-y-2 text-sm">
              {r.evidence_for.map((e, i) => (
                <li key={i}><span className="font-medium">{e.label}</span> <span className="text-muted-foreground">“{e.phrase}”</span></li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-xl border border-border p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Points the other way</p>
          {r.evidence_against.length === 0 && !r.genuine_transaction ? <p className="text-sm text-muted-foreground">No protective phrase matched.</p> : (
            <ul className="space-y-2 text-sm">
              {r.genuine_transaction && <li>Reads like a genuine transaction alert: no request, no link and no number to call.</li>}
              {r.evidence_against.map((e, i) => (
                <li key={i}>{e.why}{e.phrase && <span className="text-muted-foreground"> “{e.phrase}”</span>}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Missing context</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{r.uncertainty.missing_context.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Why this may be wrong</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{r.uncertainty.may_be_wrong.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}

function Actions({ r, uid }: { r: TrustLensReport; uid: string }) {
  if (r.recommendations.length === 0) return null;
  return (
    <section aria-labelledby={`${uid}-actions`} className="rounded-xl border border-primary/30 bg-primary/5 p-4">
      <h4 id={`${uid}-actions`} className="mb-2 flex items-center gap-2 text-sm font-semibold"><ListChecks className="h-4 w-4 text-primary" aria-hidden /> What to do</h4>
      <ul className="space-y-1.5 text-sm">
        {r.recommendations.map((a) => (
          <li key={a.id} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />{a.text}</li>
        ))}
      </ul>
    </section>
  );
}

function Similar({ r, uid }: { r: TrustLensReport; uid: string }) {
  const { status, match, genuine_match } = r.similar_pattern;
  const tacticLabel = new Map(r.evidence_for.map((e) => [e.intent, e.label]));
  const note = {
    ambiguous: "A weak resemblance to a known pattern was found but it did not pass the similarity check, so none is shown.",
    none: "No known scam pattern in ScamGuard's library closely matched this message.",
    unavailable: "The pattern library could not be searched just now. The verdict above does not depend on it.",
    match: "",
  }[status];
  return (
    <section aria-labelledby={`${uid}-similar`} className="space-y-2">
      <h4 id={`${uid}-similar`} className="flex items-center gap-2 text-sm font-semibold"><BookOpen className="h-4 w-4 text-muted-foreground" aria-hidden /> Similar known pattern</h4>
      {match ? (
        <div className="space-y-2 rounded-xl border border-border p-4 text-sm">
          <p className="font-medium">{match.title}</p>
          {match.shared_tactics.length > 0 && (
            <p><span className="text-muted-foreground">Shared tactics: </span>{(match.shared_tactic_labels.length === match.shared_tactics.length ? match.shared_tactic_labels : match.shared_tactics.map((t) => tacticLabel.get(t) ?? human(t))).join(", ")}</p>
          )}
          {match.what_happens_next && <p><span className="text-muted-foreground">How this scam usually goes: </span>{match.what_happens_next}</p>}
          <a href={match.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary underline">
            Source: {match.source_name || "reference"} <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
          <p className="text-[11px] text-muted-foreground">Similarity to a known scam is context, not proof that this message is a scam. It is not used in the risk score.</p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{note}</p>
      )}
      {genuine_match && (
        <p className="flex gap-2 text-sm"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden />
          Also resembles a known genuine format: &ldquo;{genuine_match.title}&rdquo;.</p>
      )}
    </section>
  );
}

/** TrustLens panel. `collapsible` starts it closed (used on the quick check). */
export function TrustLens({ result, collapsible = false }: { result: AnalysisResult; collapsible?: boolean }) {
  const [open, setOpen] = useState(!collapsible);
  const raw = (result.metadata as Record<string, unknown> | null | undefined)?.trustlens;
  const report = parseTrustLens(raw);
  const uid = `tl-${result.id}`;

  if (!report) {
    return (
      <section className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground" aria-label="TrustLens">
        <p className="flex items-center gap-2"><CircleDashed className="h-4 w-4" aria-hidden />
          TrustLens analysis isn&apos;t available for this result{raw === undefined ? " (it was analysed before TrustLens was added)" : ""}.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-5" aria-labelledby={`${uid}-title`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 id={`${uid}-title`} className="flex items-center gap-2 font-semibold"><ScanEye className="h-4 w-4 text-primary" aria-hidden /> TrustLens</h3>
          <p className="text-sm text-muted-foreground">{report.summary}</p>
        </div>
        {collapsible && (
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls={`${uid}-body`}
            className="inline-flex items-center gap-1 rounded-xl border border-border px-3 py-1.5 text-sm hover:border-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary">
            {open ? "Hide" : "See why"} <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} aria-hidden />
          </button>
        )}
      </div>
      {open && (
        <div id={`${uid}-body`} className="mt-4 space-y-5">
          <Scores r={report} />
          <Journey stages={report.journey} uid={uid} />
          <Actions r={report} uid={uid} />
          <Evidence r={report} uid={uid} />
          <Similar r={report} uid={uid} />
          <p className="flex gap-2 border-t border-border pt-3 text-[11px] text-muted-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />{report.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
