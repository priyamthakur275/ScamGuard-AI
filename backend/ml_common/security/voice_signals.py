"""Voice/phone-call (vishing) scam signal detection.

Operates on a real transcript only -- either produced by the browser's own
Web Speech API (live, client-side, sent to the backend as plain text) or
by a configured server-side transcription provider (see
app_service/services/voice_transcription.py). This module never sees or
touches raw audio; it is pure text analysis, identical in spirit to
email_forensics.py's content-evidence detection, with a vocabulary tuned
to how scam phone calls are actually transcribed (an "impersonation"
opening line, a request to install remote-access software, etc.) rather
than email-specific patterns.

Same design principle as the other security modules: every signal is an
independent EvidenceSignal (code/severity/reason), never an aggregate
verdict. Aggregating into a verdict is the risk engine's job.
"""
from ml_common.security.url_intelligence import EvidenceSignal

_URGENCY_KEYWORDS = frozenset({
    "right now", "immediately", "before it's too late", "act now",
    "final warning", "last chance", "within the next", "urgent",
})
_IMPERSONATION_KEYWORDS = frozenset({
    "this is the bank", "calling from the bank", "calling from amazon",
    "calling from microsoft", "this is tech support", "calling from the irs",
    "calling from income tax", "this is your service provider",
    "calling on behalf of", "government office", "cyber cell", "cyber crime",
})
_AUTHORITY_IMPERSONATION_KEYWORDS = frozenset({
    "this is the police", "this is a police officer", "law enforcement",
    "this is a court official", "arrest warrant", "legal notice",
    "customs department", "income tax department", "reserve bank",
})
_OTP_REQUEST_KEYWORDS = frozenset({
    "tell me the otp", "share the otp", "read out the code", "one time password",
    "verification code", "the code we just sent", "confirm the code",
})
_CREDENTIAL_REQUEST_KEYWORDS = frozenset({
    "your password", "your pin", "your cvv", "card number", "account number",
    "login details", "internet banking password", "atm pin",
})
_PAYMENT_PRESSURE_KEYWORDS = frozenset({
    "pay a fine", "pay immediately", "processing fee", "refundable deposit",
    "gift card", "wire the money", "transfer the amount", "pay to release",
    "customs fee", "pending fine",
})
_REMOTE_ACCESS_KEYWORDS = frozenset({
    "anydesk", "teamviewer", "install this app", "download this application",
    "screen sharing", "remote access", "give me access to your screen",
    "quick support",
})
_THREAT_KEYWORDS = frozenset({
    "your account will be blocked", "legal action will be taken",
    "you will be arrested", "case will be filed", "service will be disconnected",
    "sim will be blocked", "electricity will be cut",
})

_KEYWORD_CATEGORIES: tuple[tuple[str, frozenset, str], ...] = (
    ("urgency_language", _URGENCY_KEYWORDS, "low"),
    ("impersonation", _IMPERSONATION_KEYWORDS, "medium"),
    ("authority_impersonation", _AUTHORITY_IMPERSONATION_KEYWORDS, "high"),
    ("otp_request", _OTP_REQUEST_KEYWORDS, "high"),
    ("credential_request", _CREDENTIAL_REQUEST_KEYWORDS, "high"),
    ("payment_pressure", _PAYMENT_PRESSURE_KEYWORDS, "medium"),
    ("remote_access_request", _REMOTE_ACCESS_KEYWORDS, "high"),
    ("threat_language", _THREAT_KEYWORDS, "medium"),
)


def analyze_voice_transcript(transcript: str) -> tuple[EvidenceSignal, ...]:
    """Pure, deterministic keyword matching over a real transcript.
    Returns an empty tuple for an empty/blank transcript rather than
    guessing -- no transcript means no evidence, not "clean".
    """
    if not transcript or not transcript.strip():
        return ()

    text_lower = transcript.lower()
    signals: list[EvidenceSignal] = []
    for code, keywords, severity in _KEYWORD_CATEGORIES:
        matched = sorted(kw for kw in keywords if kw in text_lower)
        if matched:
            signals.append(EvidenceSignal(
                code, severity,
                f"Transcript contains language commonly heard in {code.replace('_', ' ')} "
                f"phone scams: \"{matched[0]}\"" + (f" (+{len(matched) - 1} more)" if len(matched) > 1 else ""),
            ))
    return tuple(signals)
