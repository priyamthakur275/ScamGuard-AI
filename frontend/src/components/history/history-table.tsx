"use client";

import { Fragment, useState, memo, useMemo, useCallback, useRef } from "react";
import { FolderPlus, ChevronDown, ChevronUp, History as HistoryIcon, ThumbsDown, ThumbsUp, Search, FileText, Link as LinkIcon, Mail, Image as ImageIcon, File as FileIcon, QrCode, Download, Trash2, Mic } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { RiskBadge } from "@/components/analysis/risk-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { truncate, verdictLabel, formatDate, formatPercent, scamCategoryLabel } from "@/lib/utils";
import { createCase } from "@/lib/api/cases";
import { saveBlob } from "@/lib/api/client";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { AnimatePresence, motion } from "framer-motion";

const AIExplanation = dynamic(() => import("@/components/analysis/ai-explanation").then(mod => mod.AIExplanation), { ssr: false });
const RiskBreakdown = dynamic(() => import("@/components/analysis/risk-breakdown").then(mod => mod.RiskBreakdown), { ssr: false });
const RecommendedActions = dynamic(() => import("@/components/analysis/recommended-actions").then(mod => mod.RecommendedActions), { ssr: false });
const EntityHighlights = dynamic(() => import("@/components/analysis/entity-highlights").then(mod => mod.EntityHighlights), { ssr: false });
import { ThreatLevelBadge } from "@/components/analysis/threat-level-badge";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { useModKeyLabel } from "@/lib/platform";
import type { AnalysisResult } from "@/types";

interface HistoryTableProps {
  entries: AnalysisResult[];
  onFeedback: (predictionId: string, isAccurate: boolean) => void;
  onDelete?: (predictionId: string) => void;
}

function getInputIcon(type?: string | null) {
  switch (type?.toLowerCase()) {
    case "url": return <span title="URL"><LinkIcon className="w-4 h-4 text-muted-foreground" /></span>;
    case "email": return <span title="Email"><Mail className="w-4 h-4 text-muted-foreground" /></span>;
    case "image": return <span title="Image"><ImageIcon className="w-4 h-4 text-muted-foreground" /></span>;
    case "pdf": return <span title="PDF"><FileIcon className="w-4 h-4 text-muted-foreground" /></span>;
    case "qr": return <span title="QR Code"><QrCode className="w-4 h-4 text-muted-foreground" /></span>;
    case "voice": return <span title="Voice call"><Mic className="w-4 h-4 text-muted-foreground" /></span>;
    case "text":
    default:
      return <span title="Text"><FileText className="w-4 h-4 text-muted-foreground" /></span>;
  }
}

export const HistoryTable = memo(function HistoryTable({ entries, onFeedback, onDelete }: HistoryTableProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterVerdict, setFilterVerdict] = useState("all");
  const [filterRiskLevel, setFilterRiskLevel] = useState("all");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const modKey = useModKeyLabel();

  async function handleAddToCase(entryId: string, text: string) {
    try {
      const created = await createCase({
        title: truncate(text, 60) || "New case",
        scan_ids: [entryId],
      });
      router.push(`/cases/${created.id}`);
    } catch {
      toast({ title: "Could not create a case. Please try again.", variant: "error" });
    }
  }

  useKeyboardShortcuts({
    "mod+k": (e) => {
      e.preventDefault();
      searchInputRef.current?.focus();
    },
  });

  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      const matchesSearch = entry.text.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesVerdict = filterVerdict === "all" || entry.verdict === filterVerdict;
      // Filter on the same level the Threat column displays (threat_level,
      // falling back to risk_level for older scans without one).
      const matchesRisk = filterRiskLevel === "all" || (entry.threat_level ?? entry.risk_level) === filterRiskLevel;
      return matchesSearch && matchesVerdict && matchesRisk;
    });
  }, [entries, searchQuery, filterVerdict, filterRiskLevel]);

  const exportJSON = useCallback(() => {
    const dataStr = JSON.stringify(filteredEntries, null, 2);
    saveBlob(new Blob([dataStr], { type: "application/json" }), `scamguard-history-${new Date().toISOString().split("T")[0]}.json`);
  }, [filteredEntries]);

  const exportCSV = useCallback(() => {
    if (filteredEntries.length === 0) return;
    
    // Pick fields for CSV
    const headers = ["id", "created_at", "verdict", "risk_level", "threat_level", "scam_category", "threat_score", "text"];
    const csvRows = [];
    csvRows.push(headers.join(","));

    for (const entry of filteredEntries) {
      const values = headers.map(header => {
        // @ts-ignore
        const val = entry[header];
        // Escape quotes and wrap in quotes for CSV
        const raw = String(val ?? "");
        const strVal = (/^[=+@\-\t\r]/.test(raw) ? "'" + raw : raw).replace(/"/g, '""');
        return `"${strVal}"`;
      });
      csvRows.push(values.join(","));
    }

    saveBlob(new Blob([csvRows.join("\n")], { type: "text/csv" }), `scamguard-history-${new Date().toISOString().split("T")[0]}.csv`);
  }, [filteredEntries]);

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={HistoryIcon}
        title="No analyses yet"
        description="Messages you analyze will appear here so you can review them later."
        actionHref="/analyze"
        actionLabel="Analyze a message"
      />
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-slide-up">
      <div className="flex flex-col gap-4 border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col sm:flex-row gap-4 flex-1">
          <div className="relative flex-1 max-w-md group">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" />
            <input
              ref={searchInputRef}
              type="text"
              aria-label="Search history"
              placeholder="Search messages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-10 w-full rounded-lg border border-border/50 bg-background/50 pl-10 pr-12 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all shadow-inner"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none hidden sm:flex items-center">
              <kbd className="inline-flex h-5 items-center gap-1 rounded border border-border bg-muted/50 px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                {modKey} K
              </kbd>
            </div>
          </div>
          <div className="flex gap-3">
            <select
              aria-label="Filter verdict"
              value={filterVerdict}
              onChange={(e) => setFilterVerdict(e.target.value)}
              className="h-10 rounded-lg border border-border/50 bg-background/50 px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
            >
              <option value="all">All verdicts</option>
              <option value="legitimate">Legitimate</option>
              <option value="spam">Spam</option>
              <option value="phishing">Phishing</option>
              <option value="scam">Scam</option>
            </select>
            <select
              aria-label="Filter threat level"
              value={filterRiskLevel}
              onChange={(e) => setFilterRiskLevel(e.target.value)}
              className="h-10 rounded-lg border border-border/50 bg-background/50 px-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
            >
              <option value="all">All threat levels</option>
              <option value="very_low">Very low</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
        
        <div className="flex items-center gap-3 self-end sm:self-auto">
          <Button variant="outline" size="sm" onClick={exportCSV} className="h-10 rounded-lg" title="Export CSV">
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
          <Button variant="outline" size="sm" onClick={exportJSON} className="h-10 rounded-lg" title="Export JSON">
            <Download className="h-4 w-4 mr-2" />
            JSON
          </Button>
        </div>
      </div>

      <div className="custom-scrollbar relative max-h-[700px] overflow-x-auto overflow-y-auto border border-border">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="sticky top-0 z-20 bg-background/80 backdrop-blur-xl text-xs uppercase text-muted-foreground shadow-sm after:absolute after:inset-x-0 after:bottom-0 after:h-px after:bg-border/50">
            <tr>
              <th className="px-4 py-3 font-semibold tracking-wider">Type</th>
              <th className="px-4 py-3 font-semibold tracking-wider w-full">Message</th>
              <th className="px-4 py-3 font-semibold tracking-wider">Verdict</th>
              <th className="px-4 py-3 font-semibold tracking-wider">Threat</th>
              <th className="px-4 py-3 font-semibold tracking-wider">Category</th>
              <th className="px-4 py-3 font-semibold tracking-wider">Date</th>
              <th className="px-4 py-3 text-right"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/30 bg-card/40">
            {filteredEntries.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-muted-foreground">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <Search className="w-8 h-8 text-muted-foreground/50" />
                    <p>No matching entries found</p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredEntries.map((entry) => {
                const isExpanded = expandedId === entry.id;
                return (
                  <Fragment key={entry.id}>
                    <tr 
                      className={`group hover:bg-primary/5 transition-colors cursor-pointer ${isExpanded ? 'bg-primary/5' : ''}`}
                      onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                    >
                      <td className="px-4 py-3">{getInputIcon(entry.input_type)}</td>
                      <td className="px-4 py-3 max-w-[14rem] truncate font-medium text-foreground lg:max-w-[18rem] 2xl:max-w-md" title={entry.text}>{entry.text}</td>
                      <td className="px-4 py-3">{verdictLabel(entry.verdict)}</td>
                      <td className="px-4 py-3">
                        {entry.threat_level ? (
                          <ThreatLevelBadge level={entry.threat_level} />
                        ) : (
                          <RiskBadge level={entry.risk_level} />
                        )}
                      </td>
                      <td className="px-4 py-3 text-foreground">{scamCategoryLabel(entry.scam_category)}</td>
                      <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{formatDate(entry.created_at)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1 opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-full"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleAddToCase(entry.id, entry.text);
                            }}
                            aria-label="Add to case"
                            title="Create an investigation case from this scan"
                          >
                            <FolderPlus className="h-4 w-4" />
                          </Button>
                          {onDelete && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 rounded-full text-destructive hover:bg-destructive/10 hover:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                onDelete(entry.id);
                              }}
                              aria-label="Delete entry"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-full"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedId(isExpanded ? null : entry.id);
                            }}
                            aria-label={isExpanded ? "Collapse details" : "Expand details"}
                          >
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>
                        </div>
                      </td>
                    </tr>
                    <AnimatePresence>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="whitespace-normal border-b-0 p-0">
                            <motion.div 
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2, ease: "easeInOut" }}
                              className="overflow-hidden"
                            >
                              <div className="px-8 py-8 bg-muted/30 border-y border-border/50 flex flex-col gap-8 shadow-inner">
                                <div>
                                  <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-primary" />
                                    Analyzed text
                                  </h4>
                                  <div className="bg-background/50 border border-border/50 rounded-lg p-4 text-sm text-foreground whitespace-pre-wrap">
                                    {entry.text}
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                                  <div className="flex flex-col gap-6">
                                    <AIExplanation 
                                      explanation={entry.ai_explanation} 
                                      executiveSummary={entry.executive_summary}
                                      technicalExplanation={entry.technical_explanation}
                                    />
                                    <RiskBreakdown breakdown={entry.risk_breakdown} />
                                  </div>
                                  <div className="flex flex-col gap-6">
                                    <EntityHighlights entities={entry.highlighted_entities} />
                                    <RecommendedActions actions={entry.recommended_actions} />
                                  </div>
                                </div>

                                <div className="flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-border/50">
                                  <div className="flex items-center gap-6 text-xs font-medium text-muted-foreground">
                                    <span className="flex items-center gap-1.5 bg-background/50 px-2 py-1 rounded-md border border-border/50">
                                      Confidence: <span className="text-foreground">{formatPercent(entry.confidence_score)}</span>
                                    </span>
                                    <span className="flex items-center gap-1.5 bg-background/50 px-2 py-1 rounded-md border border-border/50">
                                      Threat score: <span className="text-foreground">{formatPercent(entry.threat_score)}</span>
                                    </span>
                                    <span className="flex items-center gap-1.5 bg-background/50 px-2 py-1 rounded-md border border-border/50">
                                      Model: <span className="text-foreground">{entry.model_name} (v{entry.model_version})</span>
                                    </span>
                                  </div>

                                  <div className="flex items-center gap-3 bg-background/50 px-3 py-1.5 rounded-full border border-border/50">
                                    <span className="text-xs font-medium text-muted-foreground">Accurate?</span>
                                    <Button
                                      variant={entry.user_feedback === true ? "primary" : "ghost"}
                                      size="icon"
                                      className="h-7 w-7 rounded-full hover:bg-risk-low/10 hover:text-risk-low"
                                      aria-label="Mark as accurate"
                                      onClick={(e) => { e.stopPropagation(); onFeedback(entry.id, true); }}
                                    >
                                      <ThumbsUp className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button
                                      variant={entry.user_feedback === false ? "destructive" : "ghost"}
                                      size="icon"
                                      className="h-7 w-7 rounded-full hover:bg-destructive/10 hover:text-destructive"
                                      aria-label="Mark as inaccurate"
                                      onClick={(e) => { e.stopPropagation(); onFeedback(entry.id, false); }}
                                    >
                                      <ThumbsDown className="h-3.5 w-3.5" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </motion.div>
                          </td>
                        </tr>
                      )}
                    </AnimatePresence>
                  </Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
});
