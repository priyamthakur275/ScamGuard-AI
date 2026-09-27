"use client";

import { useEffect, useRef, useState } from "react";
import { Download, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { downloadReport, type ReportFormat } from "@/lib/api/reports";

interface ReportDownloadMenuProps {
  kind: "scan" | "case";
  id: string;
}

const FORMATS: { value: ReportFormat; label: string }[] = [
  { value: "pdf", label: "PDF" },
  { value: "json", label: "JSON" },
  { value: "csv", label: "CSV" },
];

export function ReportDownloadMenu({ kind, id }: ReportDownloadMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close on outside click or Escape, like any other menu.
  useEffect(() => {
    if (!isOpen) return;
    const onPointer = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setIsOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [isOpen]);

  async function handleDownload(format: ReportFormat) {
    setIsOpen(false);
    setIsDownloading(true);
    setError(null);
    try {
      await downloadReport(kind, id, format);
    } catch (err) {
      setError(err instanceof ApiError ? `Export failed: ${err.message}` : "Export failed. Try again.");
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div ref={rootRef} className="relative print:hidden">
      <Button
        aria-label="Export report"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        variant="outline"
        size="sm"
        onClick={() => setIsOpen((v) => !v)}
        isLoading={isDownloading}
      >
        {!isDownloading && <Download className="h-4 w-4 sm:mr-2" />}
        <span className="hidden font-medium sm:inline">{isDownloading ? "Exporting…" : "Export"}</span>
        <ChevronDown className="ml-1 h-3 w-3" />
      </Button>
      {isOpen && (
        <div role="menu" className="absolute left-0 top-full z-20 mt-1 w-36 overflow-hidden rounded-md border border-border bg-card shadow-md sm:left-auto sm:right-0">
          {FORMATS.map((f) => (
            <button
              key={f.value}
              role="menuitem"
              onClick={() => handleDownload(f.value)}
              className="block w-full px-3 py-2 text-left text-sm text-foreground transition-colors hover:bg-muted focus-visible:bg-muted"
            >
              {f.label}
            </button>
          ))}
        </div>
      )}
      {error && <p role="alert" className="mt-2 max-w-xs text-xs text-destructive">{error}</p>}
    </div>
  );
}
