import type { AnalysisResult } from "@/types";

export type RiskTier = "High" | "Medium" | "Low";
export type RetrievalGrade = "CORRECT" | "AMBIGUOUS" | "INCORRECT";
export type VerdictSource = "engine" | "llm_reviewed" | "engine_kept_over_llm";

export interface MatchedTactic {
  id: string;
  label: string;
  stage: string;
  evidence: string;
  seen_in: string[];
}

export interface Citation {
  kb_id: string;
  title: string;
  scam_type: string;
  source_name: string;
  url: string;
  relevance: number;
  vector_score: number;
  keyword_score: number;
  tactic_score: number;
  shared_tactics: string[];
  what_happens_next: string;
}

export interface CragVerdict {
  is_scam: boolean;
  confidence_percentage: number;
  risk_tier: RiskTier;
  matched_tactics: MatchedTactic[];
  citation_links: Citation[];
  fraud_index: number;
  model_probability: number;
  scam_type: string | null;
  retrieval_grade: RetrievalGrade;
  retrieval_confidence: number;
  emerging_threat: boolean;
  verdict_source: VerdictSource;
  notes: string[];
}

export interface CopilotAnalyzeResponse {
  verdict: CragVerdict;
  analysis: AnalysisResult;
  answer: string;
}

export type ChatRole = "user" | "assistant";
export type ChatStatus = "streaming" | "done" | "error" | "stopped";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  status: ChatStatus;
  verdict?: CragVerdict;
  error?: string;
  createdAt: number;
}

export interface ChatTurnPayload {
  role: ChatRole;
  content: string;
}

export type StreamEvent =
  | { type: "status"; stage: string }
  | { type: "verdict"; verdict: CragVerdict }
  | { type: "token"; text: string }
  | { type: "done"; kind: string }
  | { type: "error"; message: string; retryable: boolean };

const TIERS: readonly RiskTier[] = ["High", "Medium", "Low"];
const GRADES: readonly RetrievalGrade[] = ["CORRECT", "AMBIGUOUS", "INCORRECT"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Runtime check of a verdict coming over the network, so a malformed
 * payload is reported as an error instead of crashing a component. */
export function isCragVerdict(value: unknown): value is CragVerdict {
  if (!isRecord(value)) return false;
  return (
    typeof value.is_scam === "boolean" &&
    typeof value.confidence_percentage === "number" &&
    typeof value.fraud_index === "number" &&
    TIERS.includes(value.risk_tier as RiskTier) &&
    GRADES.includes(value.retrieval_grade as RetrievalGrade) &&
    Array.isArray(value.matched_tactics) &&
    Array.isArray(value.citation_links)
  );
}

export function parseStreamEvent(event: string, data: string): StreamEvent | null {
  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    return null;
  }
  if (!isRecord(payload)) return null;
  switch (event) {
    case "status":
      return { type: "status", stage: String(payload.stage ?? "") };
    case "verdict":
      return isCragVerdict(payload) ? { type: "verdict", verdict: payload } : null;
    case "token":
      return typeof payload.text === "string" ? { type: "token", text: payload.text } : null;
    case "done":
      return { type: "done", kind: String(payload.kind ?? "") };
    case "error":
      return { type: "error", message: String(payload.message ?? "Something went wrong."), retryable: payload.retryable !== false };
    default:
      return null;
  }
}
