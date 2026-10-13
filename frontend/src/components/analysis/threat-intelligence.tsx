import { LookalikeDomain } from "@/components/analysis/demo-polish";
import { ShieldQuestion, ArrowRight } from "lucide-react";
import type { UrlIntelligence } from "@/types";

interface ThreatIntelligenceProps {
  urlIntelligence: UrlIntelligence | null | undefined;
}

const SEVERITY_LABEL: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

/** Renders the backend's own graded evidence list directly -- each
 * signal already carries its severity and plain-language reason (see
 * ml_common/security/url_intelligence.py). This component does not
 * re-derive or reinterpret anything; it never computes an aggregate
 * verdict from these signals, since that's the risk engine's job
 * elsewhere. A URL with several "low" signals is not "high risk" just
 * because it has several rows here.
 *
 * Also shows the REAL redirect chain (actual hosts visited, from
 * httpx's own response history) and resolved IPs, not just a count --
 * clear evidence of where a link actually led, even when nothing about
 * it triggered a warning signal.
 */
export function ThreatIntelligence({ urlIntelligence }: ThreatIntelligenceProps) {
  if (!urlIntelligence) return null;

  const hasEvidence = urlIntelligence.evidence.length > 0;
  const hasRedirectChain = (urlIntelligence.redirect_chain?.length ?? 0) > 0;
  const hasResolvedIps = (urlIntelligence.resolved_ips?.length ?? 0) > 0;
  const page = urlIntelligence.page_inspection;
  const trust = urlIntelligence.trust;
  const age = urlIntelligence.domain_age;

  if (!hasEvidence && !hasRedirectChain && !hasResolvedIps && !page && !trust) return null;

  return (
    <div className="border border-border p-5">
      <p className="mb-3 flex items-center gap-2 text-xs font-semibold text-foreground">
        <ShieldQuestion className="h-3.5 w-3.5 text-primary" />
        URL intelligence signals
      </p>

      {urlIntelligence.hostname && <LookalikeDomain hostname={urlIntelligence.hostname} backendBrand={urlIntelligence.lookalike_of} />}

      {trust && (
        <div className="mb-4 rounded-xl border border-border bg-background/50 p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm font-medium">Website trust score</p>
              <p className="text-xs text-muted-foreground">
                {age
                  ? `${urlIntelligence.registrable_domain} registered on ${age.registered_on} (${age.age_days} days ago)${age.registrar ? ` via ${age.registrar}` : ""}`
                  : `${urlIntelligence.registrable_domain} · registration date not available`}
              </p>
            </div>
            <p
              className={`font-display text-3xl font-bold tabular-nums ${
                trust.band === "trustworthy" ? "text-risk-low" : trust.band === "caution" ? "text-risk-medium" : "text-destructive"
              }`}
            >
              {trust.score}
              <span className="text-base text-muted-foreground">/100</span>
            </p>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
            <div
              className={`h-full rounded-full ${
                trust.band === "trustworthy" ? "bg-risk-low" : trust.band === "caution" ? "bg-risk-medium" : "bg-destructive"
              }`}
              style={{ width: `${trust.score}%` }}
            />
          </div>
          <ul className="mt-3 grid gap-1 text-sm sm:grid-cols-2">
            {trust.factors.map((f) => (
              <li key={f.label} className="flex items-baseline gap-2">
                <span className={`w-9 shrink-0 text-right text-xs tabular-nums ${f.impact > 0 ? "text-risk-low" : f.impact < 0 ? "text-destructive" : "text-muted-foreground"}`}>
                  {f.impact > 0 ? `+${f.impact}` : f.impact === 0 ? "·" : f.impact}
                </span>
                <span>{f.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasEvidence && (
        <ul className="mb-3 flex flex-col gap-2">
          {urlIntelligence.evidence.map((signal) => (
            <li key={signal.code} className="flex items-start gap-2 text-sm">
              <span className="mt-0.5 shrink-0 text-xs font-semibold text-muted-foreground">
                [{SEVERITY_LABEL[signal.severity] ?? signal.severity}]
              </span>
              <span className="text-muted-foreground">{signal.reason}</span>
            </li>
          ))}
        </ul>
      )}

      {hasRedirectChain && (
        <div className="mb-3">
          <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
            Redirect chain (actually followed)
          </p>
          <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs text-foreground">
            <span>{urlIntelligence.hostname}</span>
            {urlIntelligence.redirect_chain!.slice(1).map((hop, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                {hostOf(hop.url)}
                <span className="text-muted-foreground">({hop.status_code})</span>
              </span>
            ))}
            {urlIntelligence.final_url && (
              <span className="flex items-center gap-1.5">
                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                <strong>{hostOf(urlIntelligence.final_url)}</strong>
              </span>
            )}
          </div>
          {urlIntelligence.final_url && (
            <p className="mt-1.5 break-all text-xs text-muted-foreground">
              Final destination: <span className="font-mono text-foreground">{urlIntelligence.final_url}</span>
            </p>
          )}
        </div>
      )}

      {page && (
        <div className="mb-3 border-t border-border pt-3">
          <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
            Live page inspection{page.title ? ` · “${page.title}”` : ""}
          </p>
          {page.findings.length === 0 ? (
            <p className="text-sm text-muted-foreground">The page does not ask for passwords, OTPs or card details.</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {page.findings.map((f) => (
                <li key={f.code} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 shrink-0 text-xs font-semibold text-destructive">[{f.severity}]</span>
                  <span>{f.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-muted-foreground">
        <span>Domain: {urlIntelligence.registrable_domain}</span>
        {urlIntelligence.redirect_count ? <span>Redirects: {urlIntelligence.redirect_count}</span> : null}
        {hasResolvedIps && <span>Resolved IPs: {urlIntelligence.resolved_ips!.join(", ")}</span>}
        {urlIntelligence.tls?.is_expired === true ? <span className="text-destructive">TLS certificate expired</span> : null}
      </div>
    </div>
  );
}
