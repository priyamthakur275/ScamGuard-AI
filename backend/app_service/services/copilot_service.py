"""ScamGuard Copilot: deterministic, evidence-grounded engine (Phase 17).

This is the ALWAYS-AVAILABLE default path (see copilot_llm_provider.py
for the optional, currently-unconfigured LLM path). Every answer here is
composed by reading directly from a scan's own already-computed,
already-real fields (verdict, scam_probability, threat_score,
top_contributing_tokens, highlighted_entities, risk_breakdown, and the
metadata sub-objects from url_intelligence/email_forensics/voice_evidence
/correlation) -- there is no free-text generation anywhere in this
module. If a question can't be matched to a known intent, or the
requested evidence genuinely isn't present, the answer says so plainly
rather than inventing something plausible-sounding.
"""
from dataclasses import dataclass

from app_service.schemas.message import AnalysisResult

_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "why_flagged": ("why", "flagged", "why was this", "why is this"),
    "evidence": ("evidence", "what evidence", "caused the risk", "why risky", "risk factors"),
    "attacker_request": ("asking for", "attacker want", "what do they want", "requesting", "want from me"),
    "recommended_action": ("what should i do", "what do i do", "recommend", "advice", "next steps"),
    "suspicious_indicators": ("indicator", "suspicious", "signals", "red flag", "what's suspicious", "whats suspicious"),
}


@dataclass(frozen=True)
class CopilotAnswer:
    answer: str
    grounded_in: tuple[str, ...]
    source: str
    intent: str


def classify_intent(question: str) -> str:
    text_lower = question.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "unknown"


def _all_evidence_signals(scan: AnalysisResult) -> list[tuple[str, str]]:
    metadata = scan.metadata or {}
    signals: list[tuple[str, str]] = []

    url_intel = metadata.get("url_intelligence") or {}
    for e in url_intel.get("evidence", []) or []:
        signals.append((e["code"], e["reason"]))

    email_forensics = metadata.get("email_forensics") or {}
    for key in ("header_evidence", "content_evidence", "attachment_evidence"):
        for e in email_forensics.get(key, []) or []:
            signals.append((e["code"], e["reason"]))

    for e in metadata.get("voice_evidence", []) or []:
        signals.append((e["code"], e["reason"]))

    for e in metadata.get("correlation", []) or []:
        signals.append((e["code"], e["reason"]))

    return signals


_REQUEST_TYPE_CODES = {
    "credential_request": "your login credentials or password",
    "otp_request": "an OTP or verification code",
    "payment_request": "a payment",
    "payment_pressure": "a payment",
    "remote_access_request": "remote access to your device",
}


def _answer_why_flagged(scan: AnalysisResult) -> CopilotAnswer:
    if scan.verdict == "legitimate":
        text = (
            f"This message was classified as {scan.verdict} by the model, with a "
            f"{scan.scam_probability:.0%} scam probability -- below the threshold for a scam "
            "verdict. No strong evidence signals were found."
        )
        return CopilotAnswer(text, ("verdict", "scam_probability"), "deterministic", "why_flagged")

    parts = [
        f"This message was classified as '{scan.verdict}' "
        f"({'category: ' + scan.scam_category.replace('_', ' ') if scan.scam_category else 'uncategorized'}), "
        f"with a model probability of {scan.scam_probability:.0%} and a risk level of '{scan.risk_level}'."
    ]
    top_tokens = scan.top_contributing_tokens[:3]
    if top_tokens:
        token_list = ", ".join(f"'{t.token}'" for t in top_tokens)
        parts.append(f"The model's top contributing words were: {token_list}.")

    signals = _all_evidence_signals(scan)
    if signals:
        parts.append(
            f"There {'was' if len(signals) == 1 else 'were'} also {len(signals)} additional "
            f"evidence signal{'s' if len(signals) != 1 else ''} detected, such as: {signals[0][1]}"
        )
    return CopilotAnswer(" ".join(parts), ("verdict", "scam_probability", "risk_level", "top_contributing_tokens"), "deterministic", "why_flagged")


def _answer_evidence(scan: AnalysisResult) -> CopilotAnswer:
    signals = _all_evidence_signals(scan)
    if not signals:
        return CopilotAnswer(
            "No additional structured evidence signals (URL, email, voice, or correlation) were "
            "recorded for this scan. The verdict is based on the model's own text analysis only.",
            (), "deterministic", "evidence",
        )
    lines = [f"- {reason}" for _, reason in signals]
    text = f"The following {len(signals)} evidence signal(s) were recorded for this scan:\n" + "\n".join(lines)
    return CopilotAnswer(text, ("url_intelligence", "email_forensics", "voice_evidence", "correlation"), "deterministic", "evidence")


def _answer_attacker_request(scan: AnalysisResult) -> CopilotAnswer:
    signals = _all_evidence_signals(scan)
    found_codes = {code for code, _ in signals}
    requests = [label for code, label in _REQUEST_TYPE_CODES.items() if code in found_codes]
    if not requests:
        return CopilotAnswer(
            "No specific request (such as a payment, OTP, credentials, or remote access) was "
            "detected in this message's evidence. This does not necessarily mean the message is "
            "safe -- only that this particular signal wasn't found.",
            (), "deterministic", "attacker_request",
        )
    text = "Based on the detected evidence, this message appears to be requesting: " + ", ".join(requests) + "."
    return CopilotAnswer(text, ("content_evidence",), "deterministic", "attacker_request")


def _answer_recommended_action(scan: AnalysisResult) -> CopilotAnswer:
    actions = scan.recommended_actions or []
    if not actions:
        return CopilotAnswer(
            "No specific recommended actions were generated for this scan.",
            (), "deterministic", "recommended_action",
        )
    text = "Recommended actions:\n" + "\n".join(f"- {a}" for a in actions)
    return CopilotAnswer(text, ("recommended_actions",), "deterministic", "recommended_action")


def _answer_suspicious_indicators(scan: AnalysisResult) -> CopilotAnswer:
    signals = _all_evidence_signals(scan)
    entities = scan.highlighted_entities or {}
    entity_lines = [f"- {k.replace('_', ' ')}: {', '.join(v)}" for k, v in entities.items() if v]

    if not signals and not entity_lines:
        return CopilotAnswer(
            "No specific suspicious indicators (URL/email/voice signals or flagged entities) "
            "were recorded for this scan.",
            (), "deterministic", "suspicious_indicators",
        )
    parts = []
    if signals:
        parts.append("Signals: " + "; ".join(reason for _, reason in signals))
    if entity_lines:
        parts.append("Entities found: " + "; ".join(entity_lines))
    return CopilotAnswer("\n".join(parts), ("evidence", "highlighted_entities"), "deterministic", "suspicious_indicators")


def answer_question(question: str, scan: AnalysisResult) -> CopilotAnswer:
    intent = classify_intent(question)
    handlers = {
        "why_flagged": _answer_why_flagged,
        "evidence": _answer_evidence,
        "attacker_request": _answer_attacker_request,
        "recommended_action": _answer_recommended_action,
        "suspicious_indicators": _answer_suspicious_indicators,
    }
    if intent not in handlers:
        return CopilotAnswer(
            "I can only answer specific questions about this scan's evidence right now, such as "
            "'why was this flagged', 'what evidence caused the risk', 'what is the attacker asking "
            "for', 'what should I do', or 'which indicators are suspicious'. I couldn't match your "
            "question to one of those.",
            (), "deterministic", "unknown",
        )
    return handlers[intent](scan)


def _build_grounding_context(scan: AnalysisResult) -> str:
    """Plain-text rendering of ONLY this scan's real evidence, for an LLM
    provider (if configured) to answer from -- the same facts the
    deterministic engine above reads, just serialized as text instead of
    used to fill a template. An LLM provider must never be given anything
    beyond this.
    """
    lines = [
        f"Verdict: {scan.verdict}",
        f"Model probability: {scan.scam_probability:.2%}",
        f"Confidence: {scan.confidence_score:.2%}",
        f"Threat score: {scan.threat_score:.2%}",
        f"Risk level: {scan.risk_level}",
        f"Category: {scan.scam_category or 'uncategorized'}",
    ]
    if scan.top_contributing_tokens:
        lines.append("Top contributing tokens: " + ", ".join(t.token for t in scan.top_contributing_tokens[:5]))
    signals = _all_evidence_signals(scan)
    if signals:
        lines.append("Evidence signals:")
        lines.extend(f"- {reason}" for _, reason in signals)
    if scan.highlighted_entities:
        for k, v in scan.highlighted_entities.items():
            if v:
                lines.append(f"Entities ({k}): {', '.join(v)}")
    if scan.recommended_actions:
        lines.append("Recommended actions: " + "; ".join(scan.recommended_actions))
    return "\n".join(lines)


def get_answer(question: str, scan: AnalysisResult) -> CopilotAnswer:
    """Top-level entry point: tries the optional LLM provider first (if
    configured), falls back to the deterministic evidence-grounded engine
    otherwise. The deterministic engine is what actually answers today,
    since no LLM provider is configured by default (see
    copilot_llm_provider.py).
    """
    from app_service.services.copilot_llm_provider import get_llm_answer, CopilotLlmUnavailableError

    try:
        grounding_context = _build_grounding_context(scan)
        llm_text = get_llm_answer(question, grounding_context)
        return CopilotAnswer(llm_text, ("llm_grounded_context",), "llm", classify_intent(question))
    except CopilotLlmUnavailableError:
        return answer_question(question, scan)
