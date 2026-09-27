"use client";

import { useEffect, useState, useCallback } from "react";
import { getHistory, submitFeedback, clearHistory, deleteMessage } from "@/lib/api/messages";
import { useToast } from "@/hooks/use-toast";
import { HistoryTable } from "@/components/history/history-table";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import type { AnalysisResult } from "@/types";

export default function HistoryPage() {
  const [page, setPage] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [entries, setEntries] = useState<AnalysisResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true); setError(null);
    getHistory(page * 25, 26)
      .then(data => { if (!cancelled) { setEntries(data.slice(0, 25)); setHasNext(data.length > 25); } })
      .catch(() => { if (!cancelled) setError("Could not load your history. Please try again."); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [page, reloadKey]);

  const handleFeedback = useCallback(async (predictionId: string, isAccurate: boolean) => {
    try {
      const updated = await submitFeedback(predictionId, isAccurate);
      setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      toast({ title: "Feedback saved", variant: "success" });
    } catch {
      toast({ title: "Could not save feedback", variant: "error" });
    }
  }, [toast]);

  const handleDelete = useCallback(async (predictionId: string) => {
    if (!window.confirm("Delete this scan from your history? This can't be undone.")) return;
    try {
      await deleteMessage(predictionId);
      setEntries((prev) => prev.filter((e) => e.id !== predictionId));
      toast({ title: "Scan deleted", variant: "success" });
    } catch {
      toast({ title: "Could not delete the scan. Try again.", variant: "error" });
    }
  }, [toast]);

  return (
    <div className="sg-page flex flex-col gap-6">
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Scan history</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            A record of every message you&apos;ve analyzed, saved to your account.
          </p>
        </div>
        {entries.length > 0 && (
          <Button 
            variant="outline"
            size="sm"
            className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
            onClick={async () => {
              if (!window.confirm("Permanently delete every scan in your history? This can't be undone.")) {
                return;
              }
              try {
                await clearHistory();
                setEntries([]); setPage(0); setReloadKey(k => k + 1);
                toast({ title: "History cleared", variant: "success" });
              } catch {
                toast({ title: "Could not clear history. Try again.", variant: "error" });
              }
            }}
          >
            Clear history
          </Button>
        )}
      </div>

      {error && (
        <Alert variant="error">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => setReloadKey((k) => k + 1)}>Retry</Button>
          </div>
        </Alert>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : (
        !error && (
          <>
            {entries.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Page {page + 1} · search, filters and exports apply to the {entries.length} scans on this page.
              </p>
            )}
            <HistoryTable entries={entries} onFeedback={handleFeedback} onDelete={handleDelete} />
            {(page > 0 || hasNext) && (
              <div className="flex justify-end gap-3">
                <Button variant="outline" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous page</Button>
                <Button variant="outline" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>Next page</Button>
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
