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
  kind: "scam" | "genuine";
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
  genuine_matches: Citation[];
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
  | { type: "error"; message: string; retryable: boolean; fallbackAnswer?: string };

const TIERS: readonly RiskTier[] = ["High", "Medium", "Low"];
const GRADES: readonly RetrievalGrade[] = ["CORRECT", "AMBIGUOUS", "INCORRECT"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function num(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function str(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function strList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

function toTactic(value: unknown): MatchedTactic | null {
  if (!isRecord(value) || typeof value.id !== "string") return null;
  return { id: value.id, label: str(value.label, value.id), stage: str(value.stage), evidence: str(value.evidence), seen_in: strList(value.seen_in) };
}

function toCitation(value: unknown): Citation | null {
  if (!isRecord(value) || typeof value.kb_id !== "string" || typeof value.url !== "string" || !/^https:\/\//.test(value.url)) return null;
  return {
    kb_id: value.kb_id,
    kind: value.kind === "genuine" ? "genuine" : "scam",
    title: str(value.title, "Known pattern"),
    scam_type: str(value.scam_type),
    source_name: str(value.source_name, "Source"),
    url: value.url,
    relevance: num(value.relevance, 0),
    vector_score: num(value.vector_score, 0),
    keyword_score: num(value.keyword_score, 0),
    tactic_score: num(value.tactic_score, 0),
    shared_tactics: strList(value.shared_tactics),
    what_happens_next: str(value.what_happens_next),
  };
}

function list<T>(value: unknown, map: (v: unknown) => T | null): T[] {
  return Array.isArray(value) ? value.map(map).filter((v): v is T => v !== null) : [];
}

/** Turns whatever came over the network into a complete CragVerdict, or null
 * when the essentials are missing. Optional parts that are absent or of the
 * wrong type become empty lists, so components never read undefined. */
export function normalizeVerdict(value: unknown): CragVerdict | null {
  if (!isRecord(value) || typeof value.is_scam !== "boolean") return null;
  const fraud = Math.max(0, Math.min(100, Math.round(num(value.fraud_index, value.is_scam ? 100 : 0))));
  const tier = TIERS.includes(value.risk_tier as RiskTier) ? (value.risk_tier as RiskTier) : fraud >= 70 ? "High" : fraud >= 40 ? "Medium" : "Low";
  return {
    is_scam: value.is_scam,
    confidence_percentage: Math.max(0, Math.min(100, Math.round(num(value.confidence_percentage, 0)))),
    risk_tier: tier,
    matched_tactics: list(value.matched_tactics, toTactic),
    citation_links: list(value.citation_links, toCitation),
    genuine_matches: list(value.genuine_matches, toCitation),
    fraud_index: fraud,
    model_probability: Math.max(0, Math.min(100, Math.round(num(value.model_probability, fraud)))),
    scam_type: typeof value.scam_type === "string" ? value.scam_type : null,
    retrieval_grade: GRADES.includes(value.retrieval_grade as RetrievalGrade) ? (value.retrieval_grade as RetrievalGrade) : "INCORRECT",
    retrieval_confidence: num(value.retrieval_confidence, 0),
    emerging_threat: value.emerging_threat === true,
    verdict_source: value.verdict_source === "llm_reviewed" || value.verdict_source === "engine_kept_over_llm" ? value.verdict_source : "engine",
    notes: strList(value.notes),
  };
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
    case "verdict": {
      const verdict = normalizeVerdict(payload);
      return verdict ? { type: "verdict", verdict } : null;
    }
    case "token":
      return typeof payload.text === "string" ? { type: "token", text: payload.text } : null;
    case "done":
      return { type: "done", kind: String(payload.kind ?? "") };
    case "error":
      return {
        type: "error",
        message: String(payload.message ?? "Something went wrong."),
        retryable: payload.retryable !== false,
        fallbackAnswer: typeof payload.fallback_answer === "string" ? payload.fallback_answer : undefined,
      };
    default:
      return null;
  }
}
