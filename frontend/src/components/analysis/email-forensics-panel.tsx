import { Mail, ShieldAlert } from "lucide-react";
import type { EmailForensics, EmailEvidenceSignal } from "@/types";

interface EmailForensicsPanelProps {
  forensics: EmailForensics | null | undefined;
}

const SEVERITY_LABEL: Record<string, string> = { low: "Low", medium: "Medium", high: "High" };
const AUTH_LABEL: Record<string, string> = { not_available: "Not available" };

function EvidenceList({ signals }: { signals: EmailEvidenceSignal[] }) {
  if (signals.length === 0) {
    return <p className="text-sm text-muted-foreground">No signals detected.</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {signals.map((signal) => (
        <li key={signal.code} className="flex items-start gap-2 text-sm">
          <span className="mt-0.5 shrink-0 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            [{SEVERITY_LABEL[signal.severity] ?? signal.severity}]
          </span>
          <span className="text-muted-foreground">{signal.reason}</span>
        </li>
      ))}
    </ul>
  );
}

/** Renders the backend's own graded evidence directly, in explicitly
 * separate HEADER / CONTENT / ATTACHMENT / URL sections, matching what
 * was asked for. SPF/DKIM/DMARC are shown exactly as the backend parsed
 * them from the email's own Authentication-Results header -- "not
 * available" means genuinely not available, never a guessed value.
 */
export function EmailForensicsPanel({ forensics }: EmailForensicsPanelProps) {
  if (!forensics) return null;

  const { headers } = forensics;
  const urlCount = Object.keys(forensics.url_evidence).length;

  return (
    <div className="flex flex-col gap-4 border border-border p-5">
      <p className="flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <Mail className="h-3.5 w-3.5 text-primary" />
        Email forensics
      </p>
      <p className="-mt-2 text-xs text-muted-foreground">
        Deterministic, header/content-derived evidence -- distinct from the model&apos;s own prediction above.
      </p>

      {/* Authentication status -- exactly as reported, never fabricated */}
      <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] text-muted-foreground">
        <span>SPF: {AUTH_LABEL[headers.spf] ?? headers.spf}</span>
        <span>DKIM: {AUTH_LABEL[headers.dkim] ?? headers.dkim}</span>
        <span>DMARC: {AUTH_LABEL[headers.dmarc] ?? headers.dmarc}</span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            From
          </p>
          <p className="text-sm text-foreground">{headers.from_address ?? "Not available"}</p>
        </div>
        <div>
          <p className="mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Reply-To
          </p>
          <p className="text-sm text-foreground">{headers.reply_to ?? "Not available"}</p>
        </div>
      </div>

      {/* HEADER EVIDENCE */}
      <div>
        <p className="mb-2 flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-foreground">
          <ShieldAlert className="h-3 w-3" />
          Header evidence
        </p>
        <EvidenceList signals={forensics.header_evidence} />
      </div>

      {/* CONTENT EVIDENCE */}
      <div>
        <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-wide text-foreground">
          Content evidence
        </p>
        <EvidenceList signals={forensics.content_evidence} />
      </div>

      {/* ATTACHMENT EVIDENCE */}
      {forensics.attachments.length > 0 && (
        <div>
          <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-wide text-foreground">
            Attachments ({forensics.attachments.length})
          </p>
          <ul className="mb-2 flex flex-wrap gap-2">
            {forensics.attachments.map((att, i) => (
              <li key={i} className="border border-border bg-muted px-2 py-1 font-mono text-xs text-foreground">
                {att.filename ?? "unnamed"} ({att.content_type ?? "unknown type"})
              </li>
            ))}
          </ul>
          <EvidenceList signals={forensics.attachment_evidence} />
        </div>
      )}

      {/* URL EVIDENCE (links found in the email body) */}
      {urlCount > 0 && (
        <div>
          <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-wide text-foreground">
            Links found ({urlCount})
          </p>
          <ul className="flex flex-col gap-1.5">
            {Object.entries(forensics.url_evidence).map(([url, intel]) => (
              <li key={url} className="text-sm text-muted-foreground">
                <span className="font-mono text-xs text-foreground">{url}</span>
                {intel.evidence.length > 0 && (
                  <span className="ml-2 text-xs">
                    -- {intel.evidence.map((e) => e.code).join(", ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
