import { PhoneCall } from "lucide-react";
import type { VoiceEvidenceSignal } from "@/types";

interface VoiceSignalsPanelProps {
  voiceEvidence: VoiceEvidenceSignal[] | null | undefined;
}

const SEVERITY_LABEL: Record<string, string> = { low: "Low", medium: "Medium", high: "High" };

/** Renders the backend's own graded evidence from the transcript
 * directly -- see ml_common/security/voice_signals.py. Only rendered
 * when there's something to show; a clean call produces no signals and
 * this component renders nothing, rather than an empty "all clear" box.
 */
export function VoiceSignalsPanel({ voiceEvidence }: VoiceSignalsPanelProps) {
  if (!voiceEvidence || voiceEvidence.length === 0) return null;

  return (
    <div className="border border-border p-5">
      <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <PhoneCall className="h-3.5 w-3.5 text-primary" />
        Voice-call signals
      </p>
      <ul className="flex flex-col gap-2">
        {voiceEvidence.map((signal) => (
          <li key={signal.code} className="flex items-start gap-2 text-sm">
            <span className="mt-0.5 shrink-0 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              [{SEVERITY_LABEL[signal.severity] ?? signal.severity}]
            </span>
            <span className="text-muted-foreground">{signal.reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
