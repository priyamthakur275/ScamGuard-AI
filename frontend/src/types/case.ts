import { AnalysisResult } from "./index";

export interface CaseSummary {
  id: string;
  title: string;
  description: string | null;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "investigating" | "resolved" | "archived";
  scan_count: number;
  created_at: string;
  updated_at: string;
}

export interface CaseTimelineEntry {
  id: string;
  entry_type: "created" | "status_changed" | "scan_linked" | "scan_unlinked" | "note";
  content: string;
  created_at: string;
}

export interface CaseDetail {
  id: string;
  title: string;
  description: string | null;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "investigating" | "resolved" | "archived";
  created_at: string;
  updated_at: string;
  scans: AnalysisResult[];
  aggregated_entities: Record<string, string[]>;
  timeline: CaseTimelineEntry[];
}
