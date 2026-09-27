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

  if (!hasEvidence && !hasRedirectChain && !hasResolvedIps) return null;

  return (
    <div className="border border-border p-5">
      <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <ShieldQuestion className="h-3.5 w-3.5 text-primary" />
        URL intelligence signals
      </p>

      {hasEvidence && (
        <ul className="mb-3 flex flex-col gap-2">
          {urlIntelligence.evidence.map((signal) => (
            <li key={signal.code} className="flex items-start gap-2 text-sm">
              <span className="mt-0.5 shrink-0 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                [{SEVERITY_LABEL[signal.severity] ?? signal.severity}]
              </span>
              <span className="text-muted-foreground">{signal.reason}</span>
            </li>
          ))}
        </ul>
      )}

      {hasRedirectChain && (
        <div className="mb-3">
          <p className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
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
          </div>
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
