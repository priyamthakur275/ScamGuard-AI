/** TrustLens report attached by the backend to every analysis
 * (metadata.trustlens, built by app_service/services/trustlens.py). The
 * frontend only displays it; nothing here computes a score. */

export type StageKey = "hook" | "pressure" | "ask" | "cashout";

export interface TlEvidence { phrase: string; intent: string; label: string; stage: StageKey; why: string }
export interface TlProtective { pattern: string; phrase: string; why: string }
export interface TlStage { stage: StageKey; name: string; meaning: string; detected: boolean; evidence: TlEvidence[] }
export interface TlPattern {
  id: string; kind: string; title: string; scam_type: string; relevance: number; shared_tactics: string[]; shared_tactic_labels: string[];
  what_happens_next: string; source_name: string; source_url: string;
}
export interface TrustLensReport {
  verdict: string;
  risk_level: string | null;
  classifier_probability: number | null;
  risk_score: number | null;
  summary: string;
  evidence_for: TlEvidence[];
  evidence_against: TlProtective[];
  genuine_transaction: boolean;
  journey: TlStage[];
  recommendations: { id: string; text: string }[];
  similar_pattern: { status: "match" | "ambiguous" | "none" | "unavailable"; match: TlPattern | null; genuine_match: TlPattern | null };
  uncertainty: { conflicting: boolean; insufficient: boolean; missing_context: string[]; may_be_wrong: string[] };
  disclaimer: string;
}

const STAGES: StageKey[] = ["hook", "pressure", "ask", "cashout"];
type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (v: unknown) => (typeof v === "string" ? v : "");
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const strs = (v: unknown) => arr(v).filter((x): x is string => typeof x === "string" && x.length > 0);

function evidence(v: unknown): TlEvidence | null {
  if (!isObj(v) || !STAGES.includes(v.stage as StageKey) || !str(v.phrase)) return null;
  return { phrase: str(v.phrase), intent: str(v.intent), label: str(v.label) || str(v.intent), stage: v.stage as StageKey, why: str(v.why) };
}

function pattern(v: unknown): TlPattern | null {
  if (!isObj(v) || !str(v.title) || !str(v.source_url).startsWith("https://")) return null;
  return {
    id: str(v.id), kind: str(v.kind), title: str(v.title), scam_type: str(v.scam_type), relevance: num(v.relevance) ?? 0,
    shared_tactics: strs(v.shared_tactics), shared_tactic_labels: strs(v.shared_tactic_labels), what_happens_next: str(v.what_happens_next), source_name: str(v.source_name),
    source_url: str(v.source_url),
  };
}

/** Validate the backend payload. Returns null when it is missing or not a
 * TrustLens report, so the UI can say so instead of showing invented data. */
export function parseTrustLens(raw: unknown): TrustLensReport | null {
  if (!isObj(raw) || !Array.isArray(raw.journey) || typeof raw.verdict !== "string") return null;
  const evFor = arr(raw.evidence_for).map(evidence).filter((e): e is TlEvidence => e !== null);
  const evAgainst = arr(raw.evidence_against)
    .filter(isObj)
    .map((p) => ({ pattern: str(p.pattern), phrase: str(p.phrase), why: str(p.why) }))
    .filter((p) => p.why);
  const byStage = new Map(arr(raw.journey).filter(isObj).map((j) => [j.stage as StageKey, j]));
  const journey: TlStage[] = STAGES.map((key) => {
    const j = byStage.get(key) ?? {};
    const items = arr(j.evidence).map(evidence).filter((e): e is TlEvidence => e !== null && e.stage === key);
    return { stage: key, name: str(j.name) || key, meaning: str(j.meaning), detected: j.detected === true && items.length > 0, evidence: items };
  });
  const sp = isObj(raw.similar_pattern) ? raw.similar_pattern : {};
  const status = (["match", "ambiguous", "none", "unavailable"] as const).find((s) => s === sp.status) ?? "unavailable";
  const match = status === "match" ? pattern(sp.match) : null;
  const unc = isObj(raw.uncertainty) ? raw.uncertainty : {};
  return {
    verdict: raw.verdict,
    risk_level: str(raw.risk_level) || null,
    classifier_probability: num(raw.classifier_probability),
    risk_score: num(raw.risk_score),
    summary: str(raw.summary),
    evidence_for: evFor,
    evidence_against: evAgainst,
    genuine_transaction: raw.genuine_transaction === true,
    journey,
    recommendations: arr(raw.recommendations).filter(isObj).map((r) => ({ id: str(r.id), text: str(r.text) })).filter((r) => r.text),
    similar_pattern: { status: status === "match" && !match ? "none" : status, match, genuine_match: pattern(sp.genuine_match) },
    uncertainty: {
      conflicting: unc.conflicting === true,
      insufficient: unc.insufficient === true,
      missing_context: strs(unc.missing_context),
      may_be_wrong: strs(unc.may_be_wrong),
    },
    disclaimer: str(raw.disclaimer),
  };
}
