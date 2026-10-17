"use client";

import { useState } from "react";
import { AlertTriangle, BadgeCheck, BookOpen, CheckCircle2, ChevronDown, CircleDashed, ExternalLink, Info, ListChecks, ScanEye, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/language-context";
import type { StringKey } from "@/lib/i18n/strings";
import { parseTrustLens, type TlStage, type TrustLensReport } from "@/lib/trustlens";
import type { AnalysisResult } from "@/types";

type T = (key: StringKey) => string;
const human = (id: string) => id.replace(/_/g, " ");

function Scores({ r, t }: { r: TrustLensReport; t: T }) {
  const pct = (v: number | null) => (v === null ? t("tl.na") : `${Math.round(v * 100)}%`);
  const items = [
    { label: t("tl.classifier"), value: pct(r.classifier_probability), hint: t("tl.classifierHint") },
    { label: t("tl.risk"), value: pct(r.risk_score), hint: t("tl.riskHint") },
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

function Journey({ stages, uid, t }: { stages: TlStage[]; uid: string; t: T }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section aria-labelledby={`${uid}-journey`} className="space-y-3">
      <h4 id={`${uid}-journey`} className="text-sm font-semibold">{t("tl.journey")}</h4>
      <ol className="grid gap-2 sm:grid-cols-4">
        {stages.map((s, i) => {
          const isOpen = open === s.stage;
          const name = t(`tl.stage.${s.stage}` as StringKey);
          const body = (
            <>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className={cn("inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold",
                  s.detected ? "bg-destructive text-destructive-foreground" : "border border-border")}>{i + 1}</span>
                {s.detected ? `${s.evidence.length} ${s.evidence.length > 1 ? t("tl.signs") : t("tl.sign")}` : t("tl.notDetected")}
              </span>
              <span className={cn("mt-1 block font-medium", !s.detected && "text-muted-foreground")}>{name}</span>
              <span className="block text-[11px] leading-snug text-muted-foreground">{t(`tl.stage.${s.stage}.m` as StringKey)}</span>
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
      <p className="text-[11px] text-muted-foreground">{t("tl.journeyNote")}</p>
    </section>
  );
}

function Actions({ r, uid, t }: { r: TrustLensReport; uid: string; t: T }) {
  if (r.recommendations.length === 0) return null;
  return (
    <section aria-labelledby={`${uid}-actions`} className="rounded-xl border border-primary/30 bg-primary/5 p-4">
      <h4 id={`${uid}-actions`} className="mb-2 flex items-center gap-2 text-sm font-semibold"><ListChecks className="h-4 w-4 text-primary" aria-hidden /> {t("tl.todo")}</h4>
      <ul className="space-y-1.5 text-sm">
        {r.recommendations.map((a) => (
          <li key={a.id} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />{a.text}</li>
        ))}
      </ul>
    </section>
  );
}

function GenuineContrast({ r, uid, t }: { r: TrustLensReport; uid: string; t: T }) {
  const gc = r.genuine_contrast;
  if (!gc) return null;
  return (
    <section aria-labelledby={`${uid}-genuine`} className="space-y-3">
      <h4 id={`${uid}-genuine`} className="flex items-center gap-2 text-sm font-semibold">
        <BadgeCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden /> {t("tl.gc.title")}
      </h4>
      <ul className="space-y-2">
        {gc.points.map((p) => (
          <li key={p.label} className="grid gap-1 rounded-xl border border-border p-3 text-sm sm:grid-cols-2 sm:gap-3">
            <p><span className="text-xs font-semibold uppercase tracking-wide text-destructive">{t("tl.gc.this")}</span><br />
              <span className="font-medium">{p.label}</span>{p.scam_phrase && <span className="text-muted-foreground"> “{p.scam_phrase}”</span>}</p>
            <p><span className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">{t("tl.gc.genuine")}</span><br />{p.genuine}</p>
          </li>
        ))}
      </ul>
      {gc.example && (
        <figure className="rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-3 text-sm">
          <figcaption className="mb-1 text-xs text-muted-foreground">{t("tl.gc.example")} ({gc.example.title}):</figcaption>
          <blockquote className="font-mono text-[13px] leading-relaxed">{gc.example.text}</blockquote>
          <a href={gc.example.source_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-primary underline">
            {t("tl.gc.source")}: {gc.example.source_name || "source"} <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
        </figure>
      )}
    </section>
  );
}

function Evidence({ r, uid, t }: { r: TrustLensReport; uid: string; t: T }) {
  return (
    <section aria-labelledby={`${uid}-evidence`} className="space-y-3">
      <h4 id={`${uid}-evidence`} className="text-sm font-semibold">{t("tl.evidence")}</h4>
      {(r.uncertainty.conflicting || r.uncertainty.insufficient) && (
        <p className="flex gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm" role="note">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden />
          {r.uncertainty.conflicting ? t("tl.conflict") : t("tl.insufficient")}
        </p>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-border p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("tl.supports")}</p>
          {r.evidence_for.length === 0 ? <p className="text-sm text-muted-foreground">{t("tl.noScamPhrase")}</p> : (
            <ul className="space-y-2 text-sm">
              {r.evidence_for.map((e, i) => (
                <li key={i}><span className="font-medium">{e.label}</span> <span className="text-muted-foreground">“{e.phrase}”</span></li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-xl border border-border p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("tl.against")}</p>
          {r.evidence_against.length === 0 && !r.genuine_transaction ? <p className="text-sm text-muted-foreground">{t("tl.noProtective")}</p> : (
            <ul className="space-y-2 text-sm">
              {r.genuine_transaction && <li>{t("tl.genuineTxn")}</li>}
              {r.evidence_against.map((e, i) => (
                <li key={i}>{e.why}{e.phrase && <span className="text-muted-foreground"> “{e.phrase}”</span>}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("tl.missing")}</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{r.uncertainty.missing_context.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("tl.wrong")}</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{r.uncertainty.may_be_wrong.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      </div>
    </section>
  );
}

function Similar({ r, uid, t }: { r: TrustLensReport; uid: string; t: T }) {
  const { status, match, genuine_match } = r.similar_pattern;
  const tacticLabel = new Map(r.evidence_for.map((e) => [e.intent, e.label]));
  const note = status === "match" ? "" : t(`tl.sim.${status}` as StringKey);
  return (
    <section aria-labelledby={`${uid}-similar`} className="space-y-2">
      <h4 id={`${uid}-similar`} className="flex items-center gap-2 text-sm font-semibold"><BookOpen className="h-4 w-4 text-muted-foreground" aria-hidden /> {t("tl.similar")}</h4>
      {match ? (
        <div className="space-y-2 rounded-xl border border-border p-4 text-sm">
          <p className="font-medium">{match.title}</p>
          {match.shared_tactics.length > 0 && (
            <p><span className="text-muted-foreground">{t("tl.shared")} </span>
              {(match.shared_tactic_labels.length === match.shared_tactics.length ? match.shared_tactic_labels : match.shared_tactics.map((x) => tacticLabel.get(x) ?? human(x))).join(", ")}</p>
          )}
          {match.what_happens_next && <p><span className="text-muted-foreground">{t("tl.howGoes")} </span>{match.what_happens_next}</p>}
          <a href={match.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary underline">
            {t("tl.source")}: {match.source_name || "reference"} <ExternalLink className="h-3 w-3" aria-hidden />
          </a>
          <p className="text-[11px] text-muted-foreground">{t("tl.notProof")}</p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">{note}</p>
      )}
      {genuine_match && (
        <p className="flex gap-2 text-sm"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden />
          {t("tl.genuineFormat")} &ldquo;{genuine_match.title}&rdquo;.</p>
      )}
    </section>
  );
}

/** TrustLens panel. `collapsible` starts it closed (used on the quick check). */
export function TrustLens({ result, collapsible = false }: { result: AnalysisResult; collapsible?: boolean }) {
  const { t, lang } = useLanguage();
  const [open, setOpen] = useState(!collapsible);
  const raw = (result.metadata as Record<string, unknown> | null | undefined)?.trustlens;
  const report = parseTrustLens(raw);
  const uid = `tl-${result.id}`;

  if (!report) {
    return (
      <section className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground" aria-label="TrustLens">
        <p className="flex items-center gap-2"><CircleDashed className="h-4 w-4" aria-hidden />
          {t("tl.unavailable")}{raw === undefined ? t("tl.older") : ""}.</p>
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
            {open ? t("tl.hide") : t("tl.seeWhy")} <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} aria-hidden />
          </button>
        )}
      </div>
      {open && (
        <div id={`${uid}-body`} className="mt-4 space-y-5">
          {lang === "hi" && <p className="text-xs text-muted-foreground">{t("tl.detailsEn")}</p>}
          <Scores r={report} t={t} />
          <Journey stages={report.journey} uid={uid} t={t} />
          <Actions r={report} uid={uid} t={t} />
          <GenuineContrast r={report} uid={uid} t={t} />
          <Evidence r={report} uid={uid} t={t} />
          <Similar r={report} uid={uid} t={t} />
          <p className="flex gap-2 border-t border-border pt-3 text-[11px] text-muted-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />{t("tl.disclaimer")}</p>
        </div>
      )}
    </section>
  );
}
