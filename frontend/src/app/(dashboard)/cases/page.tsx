"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FolderKanban, Plus } from "lucide-react";
import { listCases, createCase } from "@/lib/api/cases";
import type { CaseSummary } from "@/types/case";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { formatDate } from "@/lib/utils";

const STATUS_FILTERS = ["all", "open", "investigating", "resolved", "archived"] as const;

const SEVERITY_VARIANT: Record<string, "default" | "warning" | "destructive"> = {
  low: "default",
  medium: "default",
  high: "warning",
  critical: "destructive",
};

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("all");
  const [isCreating, setIsCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(async (status: (typeof STATUS_FILTERS)[number]) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listCases(status === "all" ? undefined : status);
      setCases(data);
    } catch {
      setError("Could not load cases. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load(statusFilter);
  }, [statusFilter, load]);

  async function handleCreate() {
    if (!newTitle.trim() || saving) return;
    setSaving(true);
    setCreateError(null);
    try {
      const created = await createCase({ title: newTitle.trim() });
      router.push(`/cases/${created.id}`);
    } catch {
      setCreateError("Could not create the case. Please try again.");
    } finally { setSaving(false); }
  }

  return (
    <div className="sg-page flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-sans text-2xl font-semibold tracking-tight">Investigation cases</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Group related scans into a case, track status, and keep an investigation timeline.
          </p>
        </div>
        <Button onClick={() => setIsCreating((v) => !v)}>
          <Plus className="mr-2 h-4 w-4" />
          New case
        </Button>
      </div>

      {isCreating && (
        <Card>
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Input
                label="Case title"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="e.g. Banking impersonation cluster - Sept 2026"
                error={createError ?? undefined}
              />
            </div>
            <Button onClick={handleCreate} isLoading={saving} disabled={!newTitle.trim()}>
              Create
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="flex max-w-full flex-wrap items-center gap-1 rounded-lg border border-border p-1 w-fit">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            aria-pressed={statusFilter === status}
            onClick={() => setStatusFilter(status)}
            className={`px-3 py-1.5 font-mono text-xs uppercase tracking-wide transition-colors ${
              statusFilter === status ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : cases.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No cases yet"
          description="Create a case to start tracking a related group of scans and your investigation notes."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cases.map((c) => (
            <Link key={c.id} href={`/cases/${c.id}`} className="block rounded-lg">
            <Card className="h-full transition-colors duration-150 hover:border-primary/40 hover:bg-muted/30">
              <CardContent className="flex flex-col gap-3 p-6">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-sans text-base font-semibold text-foreground">{c.title}</h3>
                  <Badge variant={SEVERITY_VARIANT[c.severity] ?? "default"}>{c.severity}</Badge>
                </div>
                {c.description && <p className="line-clamp-2 text-sm text-muted-foreground">{c.description}</p>}
                <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4 font-mono text-[11px] text-muted-foreground">
                  <span className="uppercase tracking-wide">{c.status}</span>
                  <span>
                    {c.scan_count} scan{c.scan_count === 1 ? "" : "s"} · {formatDate(c.updated_at)}
                  </span>
                </div>
              </CardContent>
            </Card></Link>
          ))}
        </div>
      )}
    </div>
  );
}
