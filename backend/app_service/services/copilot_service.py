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
from ml_common.preprocessing.display import display_token

_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    # Checked first: someone who already acted needs damage control, not an explanation.
    "already_acted": ("already paid", "i paid", "i have paid", "sent money", "transferred", "shared otp", "shared the otp",
                      "gave otp", "gave the otp", "told the otp", "i clicked", "clicked the link", "installed", "anydesk",
                      "lost money", "money deducted", "paise chale", "paise kat", "otp de diya", "otp bata diya",
                      "pay kar diya", "click kar diya", "bhej diya"),
    "report": ("report", "complain", "complaint", "police", "1930", "chakshu", "cyber cell", "shikayat"),
    "call_back": ("call back", "callback", "call them", "should i call", "should i reply", "reply to", "respond",
                  "call karu", "call karun", "reply karu"),
    "is_scam": ("is this a scam", "is it a scam", "is this real", "is it real", "is it safe", "is this safe", "genuine",
                "legit", "real or fake", "fake hai", "scam hai", "fraud hai", "safe hai", "asli", "nakli"),
    "why_flagged": ("why", "flagged", "why was this", "why is this", "kyun", "kyu "),
    "evidence": ("evidence", "what evidence", "caused the risk", "why risky", "risk factors"),
    "attacker_request": ("asking for", "attacker want", "what do they want", "requesting", "want from me"),
    "recommended_action": ("what should i do", "what do i do", "recommend", "advice", "next steps", "kya karu",
                           "kya karun", "kya karna", "help me"),
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
        token_list = ", ".join(f"'{display_token(t.token)}'" for t in top_tokens)
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


def _is_flagged(scan: AnalysisResult) -> bool:
    return str(getattr(scan.verdict, "value", scan.verdict)).lower() != "legitimate"


def _answer_already_acted(scan: AnalysisResult) -> CopilotAnswer:
    steps = [
        "Call 1930 (National Cyber Crime Helpline) right now. Reporting within the first hour gives the best chance of freezing the money.",
        "Call your bank using the number on the back of your card, not a number from the message, and block your card / UPI.",
        "If you shared an OTP or PIN or installed AnyDesk/TeamViewer: uninstall the app, change your UPI PIN and net-banking password, and log out of other devices.",
        "File a complaint at cybercrime.gov.in with screenshots, the sender's number, UTR/transaction IDs and the time.",
        "Do not pay anyone who calls offering to 'recover' the money; that is a second scam.",
    ]
    if not _is_flagged(scan):
        steps.insert(0, "ScamGuard did not flag this message, but if money left your account unexpectedly, treat it as fraud:")
    text = "Act quickly:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
    return CopilotAnswer(text, ("india_cybercrime_guidance",), "deterministic", "already_acted")


def _answer_report(scan: AnalysisResult) -> CopilotAnswer:
    text = (
        "Where to report in India:\n"
        "- Lost money: call 1930 immediately, then file at cybercrime.gov.in.\n"
        "- No money lost: report the number/message on Chakshu (sancharsaathi.gov.in/sfc) so it can be blocked.\n"
        "- Also tap 'Warn others' on this scan so other ScamGuard users see the number flagged.\n"
        "Use 'Complaint details, ready to paste' above to copy the message, numbers and links in one go."
    )
    return CopilotAnswer(text, ("india_reporting_channels",), "deterministic", "report")


def _answer_call_back(scan: AnalysisResult) -> CopilotAnswer:
    if _is_flagged(scan):
        text = (
            f"No. This message scored {scan.threat_score:.0%} scam likelihood. Replying or calling back tells the "
            "scammer your number is active and starts the pressure tactics. If it claims to be your bank or a "
            "company, contact them yourself using the number on their official website or the back of your card."
        )
    else:
        text = (
            "This message was not flagged, but if you are unsure, contact the sender through a number you already "
            "know (official website, saved contact), not one given in the message."
        )
    return CopilotAnswer(text, ("verdict",), "deterministic", "call_back")


def _answer_is_scam(scan: AnalysisResult) -> CopilotAnswer:
    if _is_flagged(scan):
        base = f"Yes, treat it as a scam: {scan.threat_score:.0%} scam likelihood"
        base += f" ({scan.scam_category.replace('_', ' ')})." if scan.scam_category else "."
        reasons = [reason for _, reason in _all_evidence_signals(scan)][:3]
        if reasons:
            base += " Main reasons: " + "; ".join(reasons)
        return CopilotAnswer(base, ("verdict", "evidence"), "deterministic", "is_scam")
    return CopilotAnswer(
        f"It looks legitimate ({scan.threat_score:.0%} scam likelihood). Still, never share an OTP, PIN or card "
        "details, and verify any payment request through an official channel.",
        ("verdict",), "deterministic", "is_scam",
    )


def answer_question(question: str, scan: AnalysisResult) -> CopilotAnswer:
    intent = classify_intent(question)
    handlers = {
        "already_acted": _answer_already_acted,
        "report": _answer_report,
        "call_back": _answer_call_back,
        "is_scam": _answer_is_scam,
        "why_flagged": _answer_why_flagged,
        "evidence": _answer_evidence,
        "attacker_request": _answer_attacker_request,
        "recommended_action": _answer_recommended_action,
        "suspicious_indicators": _answer_suspicious_indicators,
    }
    if intent not in handlers:
        return CopilotAnswer(
            "I couldn't match your question to one I can answer from this scan's evidence. Try, for example: 'is this a scam?', 'why was this flagged?', "
            "'what is the attacker asking for?', 'should I call back?', 'I already paid, what now?', "
            "'how do I report it?'. Hindi works too: 'kya ye scam hai?', 'ab kya karu?'.",
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
        lines.append("Top contributing tokens: " + ", ".join(display_token(t.token) for t in scan.top_contributing_tokens[:5]))
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
    except Exception:
        # A provider outage must never break the panel; the evidence-grounded
        # engine always has an answer.
        import logging
        logging.getLogger(__name__).warning("Copilot LLM provider failed; using deterministic answer", exc_info=True)
        return answer_question(question, scan)
