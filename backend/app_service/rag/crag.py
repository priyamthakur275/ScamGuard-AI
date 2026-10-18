"""ScamGuard Corrective RAG (CRAG) analyzer.

Pipeline for one piece of evidence (a message, link or call transcript):

1. Analyse     -- the trained classifier and the intent risk engine score the
                  text exactly as a normal scan does (nothing is stored).
2. Retrieve    -- hybrid search over the curated knowledge base
                  (rag/retriever.py) using the text and the detected tactics.
3. Evaluate    -- the retrieval evaluator grades the top match:
                    CORRECT    relevance >= CORRECT_MIN   -> trusted context
                    AMBIGUOUS  relevance >= AMBIGUOUS_MIN -> context kept, marked partial
                    INCORRECT  below AMBIGUOUS_MIN        -> context discarded; a scam
                               verdict is flagged as an unverified / emerging threat
                  Knowledge refinement keeps the best match and only other strong matches.
4. Decide      -- a strict JSON verdict. When an LLM provider is configured it
                  reviews the validated context under STRICT_ANALYZER_PROMPT and
                  its JSON is schema-checked and guarded; otherwise, or on any
                  provider failure, the deterministic engine's verdict is used.

The thresholds are calibrated for this retriever's score scale: near copies of a
known scam score about 0.75, rewordings of the same scheme 0.45 to 0.65, and
unrelated or genuine messages below 0.30.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app_service.rag.retriever import RetrievedEntry, get_retriever
from app_service.schemas.message import AnalysisResult

logger = logging.getLogger(__name__)

CORRECT_MIN = 0.45
AMBIGUOUS_MIN = 0.30
MAX_CITATIONS = 3

RetrievalGrade = Literal["CORRECT", "AMBIGUOUS", "INCORRECT"]
RiskTier = Literal["High", "Medium", "Low"]

STRICT_ANALYZER_PROMPT = """You are ScamGuard's deterministic scam analyzer. You are not a chat assistant.

INPUT: a suspicious message, the verdict of ScamGuard's trained classifier and intent engine, the red-flag tactics found in the message, and a VALIDATED CONTEXT of known scam patterns with their source URLs.

RULES:
1. Judge only from the message and the VALIDATED CONTEXT. Do not use outside knowledge, do not invent facts, URLs, phone numbers or organisations.
2. matched_tactics may contain only labels from the DETECTED TACTICS list.
3. citation_links may contain only URLs that appear in the VALIDATED CONTEXT. If the context is empty, return an empty list.
4. confidence_percentage is an integer from 0 to 100: how certain you are that is_scam is correct.
5. risk_tier is exactly one of "High", "Medium", "Low".
6. If the evidence is weak or contradictory, keep the engine's verdict and lower confidence_percentage.

OUTPUT: exactly one JSON object and nothing else. No markdown, no code fences, no text before or after it. Schema:
{"is_scam": boolean, "confidence_percentage": integer, "risk_tier": "High" | "Medium" | "Low", "matched_tactics": [string], "citation_links": [string]}"""


class MatchedTactic(BaseModel):
    id: str
    label: str
    stage: str
    evidence: str
    seen_in: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    kb_id: str
    kind: Literal["scam", "genuine"] = "scam"
    title: str
    scam_type: str
    source_name: str
    url: str
    relevance: float
    vector_score: float
    keyword_score: float
    tactic_score: float
    shared_tactics: list[str]
    what_happens_next: str


class CragVerdict(BaseModel):
    is_scam: bool
    confidence_percentage: int = Field(ge=0, le=100)
    risk_tier: RiskTier
    matched_tactics: list[MatchedTactic]
    citation_links: list[Citation]
    genuine_matches: list[Citation] = Field(default_factory=list)
    fraud_index: int = Field(ge=0, le=100)
    model_probability: int = Field(ge=0, le=100)
    scam_type: str | None
    retrieval_grade: RetrievalGrade
    retrieval_confidence: float
    emerging_threat: bool
    verdict_source: Literal["engine", "llm_reviewed", "engine_kept_over_llm"]
    notes: list[str] = Field(default_factory=list)


class LlmVerdict(BaseModel):
    is_scam: bool
    confidence_percentage: int = Field(ge=0, le=100)
    risk_tier: RiskTier
    matched_tactics: list[str]
    citation_links: list[str]


@dataclass(frozen=True)
class CragOutcome:
    verdict: CragVerdict
    analysis: AnalysisResult
    answer: str


_TIER = {"high": "High", "medium": "Medium", "low": "Low"}


def _tactics_from_analysis(analysis: AnalysisResult, raw_text: str) -> list[MatchedTactic]:
    xray = (analysis.metadata or {}).get("xray") or {}
    source_text = xray.get("text") or raw_text
    seen: dict[str, MatchedTactic] = {}
    for span in xray.get("spans") or []:
        intent = span.get("intent")
        if not intent or intent in seen:
            continue
        start, end = int(span.get("start", 0)), int(span.get("end", 0))
        phrase = source_text[start:end].strip() if 0 <= start < end <= len(source_text) else ""
        seen[intent] = MatchedTactic(id=intent, label=span.get("label", intent), stage=span.get("stage", ""), evidence=phrase[:120])
    return list(seen.values())


def grade_retrieval(results: list[RetrievedEntry]) -> tuple[RetrievalGrade, float, list[RetrievedEntry]]:
    if not results:
        return "INCORRECT", 0.0, []
    top = results[0].relevance
    # Knowledge refinement: the best match is kept if it passes the evaluator;
    # further matches only when they are strong in their own right, so a weak
    # look-alike from another scam family is never shown as a citation.
    second_bar = max(CORRECT_MIN, 0.6 * top)
    refined = [r for i, r in enumerate(results) if r.relevance >= (AMBIGUOUS_MIN if i == 0 else second_bar)][:MAX_CITATIONS]
    if top >= CORRECT_MIN:
        return "CORRECT", top, refined
    if top >= AMBIGUOUS_MIN:
        return "AMBIGUOUS", top, refined
    return "INCORRECT", top, []


def _citation(r: RetrievedEntry) -> Citation:
    e = r.entry
    return Citation(
        kb_id=e.id, kind=e.kind, title=e.title, scam_type=e.scam_type, source_name=e.source_name, url=e.source_url,
        relevance=r.relevance, vector_score=r.vector_score, keyword_score=r.keyword_score, tactic_score=r.tactic_score,
        shared_tactics=list(r.shared_tactics), what_happens_next=e.what_happens_next,
    )


def _context_block(citations: list[Citation]) -> str:
    if not citations:
        return "(empty: no known scam pattern passed the retrieval evaluator)"
    lines = []
    for c in citations:
        lines.append(f"- [{c.kb_id}] {c.title} | type: {c.scam_type} | relevance {c.relevance:.2f} | source: {c.url}\n  pattern: {c.what_happens_next}")
    return "\n".join(lines)


def parse_llm_json(raw: str) -> LlmVerdict:
    text = raw.strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise ValueError("LLM output is not a bare JSON object")
    data = json.loads(text)
    return LlmVerdict.model_validate(data)


def _llm_review(raw_text: str, base: CragVerdict) -> CragVerdict:
    """Ask the configured LLM for a strict JSON verdict and apply guarded results.
    Raises CopilotLlmUnavailableError when no provider is configured."""
    from app_service.services.copilot_llm_provider import get_llm_completion

    detected = [t.label for t in base.matched_tactics]
    user = (
        f"MESSAGE:\n{raw_text[:3000]}\n\n"
        f"ENGINE VERDICT: is_scam={str(base.is_scam).lower()}, fraud_index={base.fraud_index}, risk_tier={base.risk_tier}, "
        f"scam_type={base.scam_type or 'none'}\n"
        f"DETECTED TACTICS: {json.dumps(detected)}\n"
        f"RETRIEVAL GRADE: {base.retrieval_grade}\n"
        f"VALIDATED CONTEXT:\n{_context_block(base.citation_links)}"
    )
    llm = parse_llm_json(get_llm_completion(STRICT_ANALYZER_PROMPT, user, max_tokens=400))

    notes = list(base.notes)
    allowed_urls = {c.url for c in base.citation_links}
    dropped_urls = [u for u in llm.citation_links if u not in allowed_urls]
    if dropped_urls:
        notes.append(f"Removed {len(dropped_urls)} citation(s) the model invented outside the validated context.")
    kept_labels = {label for label in llm.matched_tactics if label in set(detected)}

    engine_sure = base.confidence_percentage >= 60
    if llm.is_scam != base.is_scam and engine_sure:
        notes.append("The language model disagreed with a confident engine verdict, so the engine verdict was kept.")
        return base.model_copy(update={"verdict_source": "engine_kept_over_llm", "notes": notes})

    tactics = [t for t in base.matched_tactics if t.label in kept_labels] or base.matched_tactics
    citations = [c for c in base.citation_links if c.url in set(llm.citation_links)] or base.citation_links
    return base.model_copy(update={
        "is_scam": llm.is_scam,
        "confidence_percentage": llm.confidence_percentage,
        "risk_tier": llm.risk_tier,
        "matched_tactics": tactics,
        "citation_links": citations,
        "emerging_threat": llm.is_scam and base.retrieval_grade == "INCORRECT",
        "verdict_source": "llm_reviewed",
        "notes": notes,
    })


def compose_answer(v: CragVerdict) -> str:
    parts: list[str] = []
    if v.is_scam:
        kind = (v.scam_type or "scam").replace("_", " ")
        parts.append(f"This looks like a scam ({kind}). Fraud index {v.fraud_index}%, {v.risk_tier.lower()} risk.")
        if v.matched_tactics:
            flags = "; ".join(f"{t.label}" + (f' ("{t.evidence}")' if t.evidence else "") for t in v.matched_tactics[:4])
            parts.append(f"Red flags I found: {flags}.")
        if v.citation_links and v.retrieval_grade != "INCORRECT":
            top = v.citation_links[0]
            strength = "closely matches" if v.retrieval_grade == "CORRECT" else "partly matches"
            parts.append(f"It {strength} a known scam: {top.title}. {top.what_happens_next}")
        if v.emerging_threat:
            parts.append("It does not match any scam in my verified knowledge base, so treat it as a new or emerging scam and be extra careful.")
        parts.append("Do not reply, click links, install apps or share any OTP, PIN or card details.")
        parts.append("If you already paid or shared an OTP, call 1930 right away and file a complaint at cybercrime.gov.in. You can report the message itself on Chakshu (sancharsaathi.gov.in/sfc).")
    else:
        parts.append(f"This looks genuine. Fraud index {v.fraud_index}%, {v.risk_tier.lower()} risk.")
        if v.genuine_matches:
            parts.append(f"It follows the usual format of a genuine {v.genuine_matches[0].title.lower()}: it reports something that already happened and asks you for nothing.")
        if v.matched_tactics:
            parts.append("A few words resemble scam wording (" + ", ".join(t.label for t in v.matched_tactics[:3]) + "), but nothing in it asks you to act in a risky way.")
        parts.append("Still, never share an OTP or PIN, and contact the sender through their official number if anything feels off.")
    return " ".join(parts)


def analyze_evidence(db: Session, raw_text: str, llm_review: bool = True) -> CragOutcome:
    from app_service.services.extraction import ExtractionService
    from app_service.services.message_service import MessageService

    text, metadata = ExtractionService.extract(None, raw_text, "TEXT")
    metadata = {**(metadata or {}), "is_quick_check": True, "source": "copilot"}
    analysis = MessageService(db).analyze_ephemeral(text, "TEXT", metadata)

    tactics = _tactics_from_analysis(analysis, raw_text)
    results = get_retriever().search(raw_text, {t.id for t in tactics}, top_k=5)
    grade, top_relevance, refined = grade_retrieval(results)
    citations = [_citation(r) for r in refined]
    for t in tactics:
        t.seen_in = [c.kb_id for c in citations if t.id in c.shared_tactics]

    is_scam = analysis.verdict != "legitimate"
    genuine: list[Citation] = []
    if not is_scam:
        genuine = [_citation(r) for r in get_retriever().search(raw_text, {t.id for t in tactics}, top_k=2, kind="genuine") if r.relevance >= CORRECT_MIN]
    notes: list[str] = []
    if genuine:
        notes.append(f"Matches the usual format of a genuine message ({genuine[0].title.lower()}).")
    if grade == "INCORRECT" and is_scam:
        notes.append("No known scam pattern passed the retrieval evaluator; the verdict rests on the classifier and intent engine alone.")
    verdict = CragVerdict(
        is_scam=is_scam,
        confidence_percentage=int(round(analysis.confidence_score * 100)),
        risk_tier=_TIER.get(analysis.risk_level, "Medium"),
        matched_tactics=tactics,
        citation_links=citations if is_scam or grade == "CORRECT" else [],
        genuine_matches=genuine,
        fraud_index=int(round(analysis.threat_score * 100)),
        model_probability=int(round(analysis.scam_probability * 100)),
        scam_type=analysis.scam_category if is_scam else None,
        retrieval_grade=grade,
        retrieval_confidence=round(top_relevance, 4),
        emerging_threat=is_scam and grade == "INCORRECT",
        verdict_source="engine",
        notes=notes,
    )

    from app_service.services.copilot_llm_provider import CopilotLlmUnavailableError

    try:
        if not llm_review:
            raise CopilotLlmUnavailableError("LLM review not requested")
        verdict = _llm_review(raw_text, verdict)
    except CopilotLlmUnavailableError:
        pass
    except (ValidationError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("LLM verdict rejected (%s); using engine verdict", type(exc).__name__)
        verdict = verdict.model_copy(update={"notes": verdict.notes + ["The language model's output failed validation, so the engine verdict was used."]})
    except Exception:
        logger.warning("LLM provider failed; using engine verdict", exc_info=True)
        verdict = verdict.model_copy(update={"notes": verdict.notes + ["The language model could not be reached, so the engine verdict was used."]})

    return CragOutcome(verdict=verdict, analysis=analysis, answer=compose_answer(verdict))
