"""English / Hindi / Hinglish preprocessing for Indian scam terminology.

HONESTY NOTE: the underlying ML model (naive_bayes, TF-IDF) is trained on
English text only -- this module does NOT retrain it, does not claim any
multilingual accuracy, and does not invent a "language detection model".
`detect_language()` is a lightweight, deterministic heuristic (Devanagari
script ratio + a short list of common transliterated-Hindi markers), not a
statistically validated classifier -- it is labeled as a heuristic
throughout, including in its own docstring and test names.

What this module actually does: recognizes common Indian scam concepts
(OTP, UPI, KYC, bank, payment, cashback, lottery, job, investment, loan,
courier, police, income tax, Aadhaar, PAN) whether they appear in English,
Devanagari Hindi, or Hinglish transliteration, and produces a short,
English-language summary of what it found. That summary is APPENDED to
the original text (same convention as url_intelligence/email_forensics/
voice_signals evidence blocks elsewhere in this codebase) so the existing
English TF-IDF model has recognizable tokens to work with even when the
original message is in Hindi or Hinglish -- it never replaces, translates,
or removes the original text. "Preserve original input" is enforced by
construction: normalize_for_analysis() only ever appends.
"""
import re
from dataclasses import dataclass

from ml_common.security.url_intelligence import EvidenceSignal

_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

# A short, common set of transliterated Hindi words/particles that show up
# in Hinglish text (Hindi written in Latin script). Deliberately small and
# explicit -- not a claim of a comprehensive Hinglish dictionary.
_HINGLISH_MARKERS = frozenset({
    "hai", "hain", "kar", "karo", "kijiye", "kijiyega", "turant", "jaldi",
    "paisa", "paise", "rupaye", "rupya", "khata", "khaata", "sampark",
    "band", "bhejo", "bhejiye", "milega", "aayega", "aapka", "aapke",
    "kripya", "dhyan", "abhi", "turnt",
})

# Canonical concept -> surface forms across English, Devanagari Hindi, and
# common Hinglish transliteration. Substring-matched, case-insensitive.
_CONCEPT_SURFACE_FORMS: dict[str, frozenset[str]] = {
    "otp": frozenset({"otp", "ओटीपी", "one time password", "one-time password"}),
    "upi": frozenset({"upi", "यूपीआई", "google pay", "phonepe", "paytm", "bhim"}),
    "kyc": frozenset({"kyc", "केवाईसी", "know your customer"}),
    "bank": frozenset({"bank", "बैंक", "khata", "khaata", "bank account"}),
    "payment": frozenset({"payment", "भुगतान", "paisa", "paise", "rupaye", "rupya", "rupees"}),
    "cashback": frozenset({"cashback", "कैशबैक", "reward points", "bonus amount"}),
    "lottery": frozenset({"lottery", "लॉटरी", "inaam", "lucky draw", "jeeta hai", "prize money"}),
    "job": frozenset({"job offer", "नौकरी", "naukri", "part time job", "work from home", "vacancy"}),
    "investment": frozenset({"investment", "निवेश", "trading tips", "double your money", "stock tip", "mutual fund"}),
    "loan": frozenset({"loan", "ऋण", "loan approved", "instant loan", "loan disbursed"}),
    "courier": frozenset({"courier", "कूरियर", "parcel held", "customs department", "shipment on hold"}),
    "police": frozenset({"police", "पुलिस", "cyber cell", "cyber crime branch", "fir registered"}),
    "income_tax": frozenset({"income tax", "आयकर", "it department", "tax refund", "income tax department"}),
    "aadhaar": frozenset({"aadhaar", "aadhar", "आधार", "aadhaar card", "aadhaar number"}),
    "pan": frozenset({"pan card", "pan number", "पैन कार्ड"}),
}

# A few common Hinglish urgency/threat phrasings, analogous to the
# English urgency/threat keyword categories already used for email/voice.
_HINGLISH_URGENCY_PHRASES = frozenset({
    "turant paisa bhejo", "abhi paisa bhejo", "jaldi karo", "turant sampark karo",
    "aapka khata band ho jayega", "aapka account band ho jayega",
    "abhi verify karo", "turant verify kijiye",
})


@dataclass(frozen=True)
class MultilingualAnalysis:
    detected_language: str  # "english" | "hindi" | "hinglish" | "mixed" -- heuristic, not a verified classification
    devanagari_ratio: float
    detected_concepts: tuple[str, ...]
    evidence: tuple[EvidenceSignal, ...]

    def to_dict(self) -> dict:
        return {
            "detected_language": self.detected_language,
            "devanagari_ratio": self.devanagari_ratio,
            "detected_concepts": list(self.detected_concepts),
            "evidence": [{"code": e.code, "severity": e.severity, "reason": e.reason} for e in self.evidence],
        }


def detect_language(text: str) -> tuple[str, float]:
    """Returns (language, devanagari_ratio). This is a lightweight,
    deterministic HEURISTIC (script ratio + a small marker word list) --
    not a trained/validated language identification model. Good enough to
    route which concept-matching applies; not claimed to be more than that.
    """
    if not text or not text.strip():
        return "english", 0.0

    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "english", 0.0

    devanagari_count = sum(1 for c in letters if _DEVANAGARI_PATTERN.match(c))
    ratio = round(devanagari_count / len(letters), 4)

    if ratio > 0.6:
        return "hindi", ratio
    if ratio > 0.05:
        return "mixed", ratio

    text_lower = text.lower()
    words = set(re.findall(r"[a-z]+", text_lower))
    hinglish_hits = words & _HINGLISH_MARKERS
    if len(hinglish_hits) >= 2:
        return "hinglish", ratio

    return "english", ratio


def detect_concepts(text: str) -> tuple[str, ...]:
    """Case-insensitive substring match against known surface forms.
    Returns canonical concept names actually found in the text -- never a
    guess, never a partial/fuzzy match that could misfire.
    """
    if not text:
        return ()
    text_lower = text.lower()
    found = [
        concept for concept, forms in _CONCEPT_SURFACE_FORMS.items()
        if any(form in text_lower for form in forms)
    ]
    return tuple(sorted(found))


def _detect_hinglish_urgency(text: str) -> tuple[EvidenceSignal, ...]:
    text_lower = text.lower()
    matched = sorted(p for p in _HINGLISH_URGENCY_PHRASES if p in text_lower)
    if not matched:
        return ()
    return (EvidenceSignal(
        "hinglish_urgency_language", "low",
        f"Message contains Hinglish urgency phrasing commonly seen in Indian scam "
        f"messages: \"{matched[0]}\"" + (f" (+{len(matched) - 1} more)" if len(matched) > 1 else ""),
    ),)


def analyze_multilingual(text: str) -> MultilingualAnalysis:
    language, ratio = detect_language(text)
    concepts = detect_concepts(text)
    evidence = _detect_hinglish_urgency(text)
    return MultilingualAnalysis(
        detected_language=language,
        devanagari_ratio=ratio,
        detected_concepts=concepts,
        evidence=evidence,
    )


def normalize_for_analysis(text: str) -> str:
    """Returns text with an APPENDED, English-language summary of detected
    concepts/signals -- the original text is never modified, translated,
    or removed. This is what lets the existing English-only model pick up
    on concepts like OTP/UPI/KYC even when the surrounding message is in
    Hindi or Hinglish: the concept names themselves are appended in
    English, in addition to (never instead of) the original text.
    """
    analysis = analyze_multilingual(text)
    lines = []
    if analysis.detected_concepts:
        readable = [c.replace("_", " ").upper() if c in ("otp", "upi", "kyc", "pan") else c.replace("_", " ") for c in analysis.detected_concepts]
        lines.append(f"Detected concepts: {', '.join(readable)}.")
    for signal in analysis.evidence:
        lines.append(f"- {signal.reason}")

    if not lines:
        return text
    return text + "\n\nDetected language/concepts (heuristic):\n" + "\n".join(lines)
