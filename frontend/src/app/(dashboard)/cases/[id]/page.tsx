"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Unlink, Clock, StickyNote } from "lucide-react";
import { getCase, updateCase, unlinkScanFromCase, addCaseNote } from "@/lib/api/cases";
import type { CaseDetail } from "@/types/case";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { ThreatBadge } from "@/components/analysis/risk-badge";
import { ReportDownloadMenu } from "@/components/analysis/report-download-menu";
import { formatDate, formatPercent, verdictLabel, truncate } from "@/lib/utils";

const STATUSES = ["open", "investigating", "resolved", "archived"] as const;

const SEVERITY_VARIANT: Record<string, "default" | "warning" | "destructive"> = {
  low: "default",
  medium: "default",
  high: "warning",
  critical: "destructive",
};

const TIMELINE_LABEL: Record<string, string> = {
  created: "Case created",
  status_changed: "Status changed",
  scan_linked: "Scan linked",
  scan_unlinked: "Scan unlinked",
  note: "Note added",
};

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [isSavingNote, setIsSavingNote] = useState(false);

  // Initial load shows a skeleton; refreshes after an action keep the
  // current case on screen (no flash, focus and scroll are preserved).
  const load = useCallback(async (refresh = false) => {
    if (!refresh) setIsLoading(true);
    setError(null);
    try {
      const data = await getCase(params.id);
      setDetail(data);
    } catch {
      if (refresh) setActionError("Could not refresh this case. Reload the page to see the latest changes.");
      else setError("Could not load this case. It may not exist, or you may not have access to it.");
    } finally {
      setIsLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStatusChange(status: string) {
    if (!detail) return;
    setUpdating(true); setActionError(null);
    try { await updateCase(detail.id, { status }); await load(true); }
    catch { setActionError("Could not update the case status. Please try again."); }
    finally { setUpdating(false); }
  }

  async function handleUnlink(predictionId: string) {
    if (!detail) return;
    setActionError(null);
    try { await unlinkScanFromCase(detail.id, predictionId); await load(true); }
    catch { setActionError("Could not unlink this scan. Please try again."); }
  }

  async function handleAddNote() {
    if (!detail || !noteText.trim()) return;
    setIsSavingNote(true);
    setActionError(null);
    try {
      await addCaseNote(detail.id, noteText.trim());
      setNoteText("");
      await load(true);
    } catch { setActionError("Could not save the note. Your text has been kept so you can retry."); }
    finally {
      setIsSavingNote(false);
    }
  }

  if (isLoading) {
    return (
      <div className="sg-page flex flex-col gap-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="flex flex-col gap-4">
        <Link href="/cases" className="flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to cases
        </Link>
        <Alert variant="error">{error ?? "Case not found."}</Alert>
      </div>
    );
  }

  const entityEntries = Object.entries(detail.aggregated_entities).filter(([, v]) => v.length > 0);

  return (
    <div className="sg-page flex flex-col gap-6">
      <Link href="/cases" className="flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to cases
      </Link>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-sans text-2xl font-semibold tracking-tight">{detail.title}</h1>
            <Badge variant={SEVERITY_VARIANT[detail.severity] ?? "default"}>{detail.severity}</Badge>
          </div>
          {detail.description && <p className="mt-1 text-sm text-muted-foreground">{detail.description}</p>}
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            Created {formatDate(detail.created_at)} · Updated {formatDate(detail.updated_at)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ReportDownloadMenu kind="case" id={detail.id} />
          <div className="flex flex-wrap items-center gap-1 rounded-lg border border-border p-1">
            {STATUSES.map((status) => (
              <button
                key={status}
                disabled={updating}
                aria-pressed={detail.status === status}
                onClick={() => handleStatusChange(status)}
                className={`px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition-colors ${
                  detail.status === status ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {actionError && <Alert variant="error">{actionError}</Alert>}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
            Linked scans ({detail.scans.length})
          </h2>
          {detail.scans.length === 0 ? (
            <p className="text-sm text-muted-foreground">No scans linked to this case yet.</p>
          ) : (
            detail.scans.map((scan) => (
              <Card key={scan.id}>
                <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-foreground">{truncate(scan.text, 80)}</p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {verdictLabel(scan.verdict)} · {formatPercent(scan.scam_probability)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <ThreatBadge threatLevel={scan.threat_level} riskLevel={scan.risk_level} />
                    <Button variant="ghost" size="icon" onClick={() => handleUnlink(scan.id)} aria-label="Unlink scan">
                      <Unlink className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}

          {entityEntries.length > 0 && (
            <div className="mt-2 rounded-lg border border-border bg-card p-5">
              <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
                Entities across linked scans
              </p>
              <div className="flex flex-col gap-2">
                {entityEntries.map(([key, values]) => (
                  <div key={key} className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                      {key.replace(/_/g, " ")}:
                    </span>
                    {values.map((v, i) => (
                      <span key={i} className="border border-border bg-muted px-2 py-0.5 font-mono text-xs text-foreground">
                        {v}
                      </span>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <h2 className="flex items-center gap-1.5 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
            <Clock className="h-3.5 w-3.5" /> Timeline
          </h2>

          <div className="flex flex-col gap-2">
            <Textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              label="Investigation note"
              placeholder="Add an investigation note..."
              className="min-h-[80px] text-sm"
            />
            <Button size="sm" onClick={handleAddNote} disabled={!noteText.trim() || isSavingNote} className="self-end">
              <StickyNote className="mr-1.5 h-3.5 w-3.5" />
              {isSavingNote ? "Saving…" : "Add note"}
            </Button>
          </div>

          <ul className="case-timeline flex flex-col gap-3 border-l border-border pl-4">
            {[...detail.timeline].reverse().map((entry) => (
              <li key={entry.id} className="relative">
                <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-primary" />
                <p className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                  {TIMELINE_LABEL[entry.entry_type] ?? entry.entry_type} · {formatDate(entry.created_at)}
                </p>
                <p className="mt-0.5 text-sm text-foreground">{entry.content}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
