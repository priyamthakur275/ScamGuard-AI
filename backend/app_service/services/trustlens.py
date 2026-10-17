"""TrustLens: an evidence-aware explanation of one analysis result.

TrustLens does NOT score anything. It reads what the existing pipeline already
produced -- the classifier probability, the fused threat score and verdict
(ThreatScorer), the Scam X-Ray phrase matches, the protective patterns and the
corrective-RAG retriever -- and turns them into:

  - evidence for and against the assessment, phrase by phrase,
  - the scam journey (hook, pressure, ask, cash-out) with only matched stages
    marked as detected,
  - safety recommendations chosen from the matched evidence,
  - a similar known pattern, only when the retriever's evaluator accepts it,
  - an uncertainty section: conflicts, missing context, why it may be wrong.

Retrieval stays separate from the verdict, as in the research pipeline: a
similar pattern is shown as context, never fed back into the score.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

STAGE_INFO = {
    "hook": ("Hook", "Gets your attention or trust"),
    "pressure": ("Pressure", "Urgency, threats, deadlines or secrecy"),
    "ask": ("Ask", "Requests sensitive details, an approval or an action"),
    "cashout": ("Cash-out", "Tries to get money, credentials or access"),
}

# intent -> safety action. Only actions whose evidence was matched are shown.
_ACTIONS: list[tuple[set[str], str, str]] = [
    ({"asks_for_secret"}, "secret",
     "Do not share OTPs, PINs, passwords or recovery codes with anyone, including people who say they are from your bank."),
    ({"asks_card_details"}, "card", "Do not send card numbers, expiry dates, CVV or account details by message or call."),
    ({"remote_access_app"}, "remote",
     "Do not install AnyDesk, TeamViewer or any app someone asks you to install; it can let them see your screen and OTPs."),
    ({"collect_request"}, "collect",
     "Do not approve UPI collect requests or enter your UPI PIN to receive money; the PIN only ever sends money out."),
    ({"move_money", "pay_to_receive"}, "money",
     "Do not transfer money to a 'safe account', a fee for a prize or job, or anyone you cannot verify independently."),
    ({"suspicious_link", "link_with_action", "deceptive_domain", "insecure_login_page", "page_collects_secrets",
      "page_posts_elsewhere", "page_impersonates_brand", "new_domain"}, "link",
     "Do not open the link or log in through it. Type the official website address yourself or use the official app."),
    ({"impersonation", "account_threat", "kyc_update_demand", "verify_account_demand"}, "verify",
     "Check any account warning in your bank's official app or on a number you find yourself (card back, official website), not one in the message."),
    ({"legal_threat"}, "legal",
     "Police, courts and agencies do not settle cases over calls or demand payment; 'digital arrest' is not a real procedure. Hang up."),
    ({"secrecy", "new_number_emergency"}, "talk",
     "Talk to a family member or friend before acting; call the person on the number you already have."),
    ({"harassment"}, "extortion", "Do not pay blackmailers; keep the messages as evidence and report them."),
    ({"task_scam", "too_good"}, "offer", "Treat guaranteed returns, prizes you never entered and paid online tasks as bait."),
]

# What a genuine message does instead of each scam tactic.
GENUINE_INSTEAD = {
    "asks_for_secret": "Genuine messages tell you never to share an OTP or PIN; they never ask you for one.",
    "asks_card_details": "Banks never ask for your card number, expiry date or CVV by message or call.",
    "verify_account_demand": "Real account checks happen inside the official app or at the branch, not through a link in a message.",
    "kyc_update_demand": "KYC is updated in the official app or at the branch; a genuine SMS never sends a KYC link.",
    "account_threat": "Genuine alerts report what already happened (amount, masked account) without threatening to block you.",
    "deadline": "Real notices give an ordinary due date, not 'today' or 'within 2 hours'.",
    "legal_threat": "Police and courts send written notices; they never demand money or keep you on a video call.",
    "secrecy": "No genuine bank, company or officer asks you to keep a payment secret from your family.",
    "impersonation": "Genuine bank SMS come from the bank's registered sender ID and don't need to convince you who they are.",
    "too_good": "Real prizes and returns don't arrive for contests or schemes you never joined.",
    "pay_to_receive": "Nobody genuine asks you to pay a fee before you receive a prize, refund, loan or job.",
    "move_money": "No bank or agency asks you to move money to a 'safe account'.",
    "collect_request": "To receive money you never approve a request or enter your PIN; genuine credits simply arrive.",
    "remote_access_app": "Banks never ask you to install screen-sharing apps such as AnyDesk.",
    "mistaken_transfer": "A genuine credit shows up in your bank app with a reference number and never comes with a request to send it back.",
    "task_scam": "Real jobs don't pay for likes or reviews and never ask you for a deposit.",
    "new_number_emergency": "A relative in trouble can be checked by calling the number you already have for them.",
    "suspicious_link": "Genuine messages point to the official app or a well-known official website, or carry no link at all.",
    "link_with_action": "Genuine messages point to the official app or a well-known official website, or carry no link at all.",
    "deceptive_domain": "Official websites use the brand's real domain, not a look-alike spelling.",
    "insecure_login_page": "Real login pages always use https://.",
    "page_collects_secrets": "Official pages never ask for your OTP on a page you reached from a message.",
    "page_posts_elsewhere": "Official forms send your details to the official site, not to another website.",
    "page_impersonates_brand": "Official pages live on the brand's own domain.",
    "new_domain": "Official websites have existed for years, not days.",
}

# Which genuine library format to show as the contrast example, by matched tactic.
_GENUINE_EXAMPLE = [
    ({"collect_request", "mistaken_transfer", "pay_to_receive"}, "gen-003"),
    ({"asks_for_secret", "asks_card_details", "remote_access_app"}, "gen-007"),
    ({"kyc_update_demand", "verify_account_demand", "account_threat", "move_money", "impersonation"}, "gen-002"),
]

REPORT_ACTION = ("If you shared details or lost money, call 1930 (National Cyber Crime Helpline) immediately and report at "
                 "cybercrime.gov.in. Report scam calls or messages on Chakshu at sancharsaathi.gov.in.")

DISCLAIMER = ("This is a risk assessment from a trained text classifier and rule-based evidence, not proof that the message is "
              "fraudulent or genuine. Similar known patterns are context, not evidence about this sender.")


def _protective_evidence(text: str) -> list[dict]:
    from ml_service.inference.scam_xray import PROTECTIVE_INFO
    from ml_service.inference.threat_scorer import _PROTECTIVE, ThreatScorer

    _found, protective = ThreatScorer.intents(text)
    flat = " ".join(text.split())
    out = []
    for name, _w, rx in _PROTECTIVE:
        if name not in protective:
            continue
        m = rx.search(flat)
        out.append({"pattern": name, "phrase": m.group(0).strip()[:120] if m else "",
                    "why": PROTECTIVE_INFO.get(name, "Points towards a genuine message.")})
    return out


def _similar_pattern(text: str, intents: set[str]) -> dict:
    """The retriever's verdict on similarity, following its own evaluator:
    a match is shown only when graded CORRECT; AMBIGUOUS and INCORRECT never
    produce a displayed match."""
    try:
        from app_service.rag.crag import CORRECT_MIN, grade_retrieval
        from app_service.rag.retriever import get_retriever

        retriever = get_retriever()
        grade, top, refined = grade_retrieval(retriever.search(text, intents, top_k=5))
        genuine = [r for r in retriever.search(text, intents, top_k=2, kind="genuine") if r.relevance >= CORRECT_MIN]
    except Exception:
        logger.warning("TrustLens retrieval unavailable", exc_info=True)
        return {"status": "unavailable", "match": None, "genuine_match": None}

    from ml_service.inference.scam_xray import INTENT_INFO

    def card(r) -> dict:
        e = r.entry
        return {"id": e.id, "kind": e.kind, "title": e.title, "scam_type": e.scam_type, "relevance": round(r.relevance, 3),
                "shared_tactics": list(r.shared_tactics),
                "shared_tactic_labels": [INTENT_INFO.get(t, ("", t.replace("_", " ")))[1] for t in r.shared_tactics],
                "what_happens_next": e.what_happens_next,
                "source_name": e.source_name, "source_url": e.source_url}

    status = {"CORRECT": "match", "AMBIGUOUS": "ambiguous", "INCORRECT": "none"}[grade]
    return {"status": status, "relevance": round(top, 3), "match": card(refined[0]) if grade == "CORRECT" and refined else None,
            "genuine_match": card(genuine[0]) if genuine else None}


def _genuine_contrast(suspicious: list[dict], text: str, intents: set[str]) -> dict | None:
    points, seen = [], set()
    for e in suspicious:
        instead = GENUINE_INSTEAD.get(e["intent"])
        if instead and instead not in seen:
            seen.add(instead)
            points.append({"label": e["label"], "scam_phrase": e["phrase"], "genuine": instead})
    if not points:
        return None
    example = None
    try:
        from app_service.rag.crag import AMBIGUOUS_MIN
        from app_service.rag.retriever import get_retriever

        retriever = get_retriever()
        by_id = {e.id: e for e in retriever.entries}
        lowered = text.lower()
        wanted = next((gid for trig, gid in _GENUINE_EXAMPLE if intents & trig), None)
        if any(w in lowered for w in ("electricity", "power cut", "bijli", "bill")):
            wanted = "gen-005"
        elif any(w in lowered for w in ("parcel", "courier", "delivery", "shipment")):
            wanted = "gen-008"
        entry = by_id.get(wanted) if wanted else None
        if entry is None:
            top = retriever.search(text, intents, top_k=1, kind="genuine")
            entry = top[0].entry if top and top[0].relevance >= AMBIGUOUS_MIN else None
        if entry is not None:
            example = {"id": entry.id, "title": entry.title, "text": entry.transcript_body,
                       "source_name": entry.source_name, "source_url": entry.source_url}
    except Exception:
        logger.warning("TrustLens genuine example unavailable", exc_info=True)
    return {"points": points[:6], "example": example}


def build_trustlens(*, text: str, verdict: str, scam_probability: float | None, threat_score: float | None,
                    risk_level: str | None, xray: dict | None) -> dict:
    """Assemble the TrustLens report from values the pipeline already computed."""
    from ml_service.inference.scam_xray import xray as run_xray
    from ml_service.inference.threat_scorer import ThreatScorer, is_genuine_transaction

    xr = xray if isinstance(xray, dict) and isinstance(xray.get("spans"), list) else run_xray(text)
    source = xr.get("text") or text
    suspicious: list[dict] = []
    for s in xr.get("spans", []):
        try:
            start, end = int(s["start"]), int(s["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= start < end <= len(source)) or s.get("stage") not in STAGE_INFO:
            continue
        suspicious.append({"phrase": source[start:end].strip()[:160], "intent": s.get("intent", ""), "label": s.get("label", ""),
                           "stage": s["stage"], "why": s.get("why", "")})

    protective = _protective_evidence(source)
    found, prot_weights = ThreatScorer.intents(source)
    genuine_txn = is_genuine_transaction(source, found, prot_weights)
    intents = {e["intent"] for e in suspicious} | set(found)

    journey = []
    for key, (name, meaning) in STAGE_INFO.items():
        items = [e for e in suspicious if e["stage"] == key]
        journey.append({"stage": key, "name": name, "meaning": meaning, "detected": bool(items), "evidence": items})

    is_scam = verdict != "legitimate"
    recommendations = []
    for trigger, key, action in _ACTIONS:
        if intents & trigger:
            recommendations.append({"id": key, "text": action})
    if is_scam:
        if not recommendations:
            recommendations.append({"id": "pause", "text": "Do not reply, click or pay until you have checked the sender through an official channel you find yourself."})
        recommendations.append({"id": "report", "text": REPORT_ACTION})
    elif genuine_txn:
        recommendations.append({"id": "genuine_txn", "text": "If you do not recognise this transaction, contact your bank through its official app or the number on your card."})

    # ---------------- uncertainty
    conflicts = bool(suspicious) and bool(protective)
    insufficient = not suspicious and not protective
    missing_context = ["Who actually sent the message (sender IDs and numbers can be spoofed)."]
    if any("link" in e["intent"] or e["intent"] in ("deceptive_domain", "new_domain") for e in suspicious):
        missing_context.append("Where the link really leads after any redirects.")
    if "impersonation" in intents or "account_threat" in intents:
        missing_context.append("Whether your account or service really has the problem described; only the official app or branch can confirm it.")
    if not is_scam:
        missing_context.append("Any earlier conversation: a harmless-looking message can be the first step of a longer scam.")

    may_be_wrong = []
    if insufficient:
        may_be_wrong.append("No known scam or protective phrase matched, so the verdict rests only on the classifier's word patterns.")
    if conflicts:
        may_be_wrong.append("The message mixes scam signs with reassuring phrases; scammers sometimes copy safety lines from real messages.")
    if scam_probability is not None and threat_score is not None and (scam_probability >= 0.5) != (threat_score >= 0.5):
        side = "flagged it" if scam_probability >= 0.5 else "did not flag it"
        may_be_wrong.append(f"The classifier on its own {side}, but the evidence-weighted risk score points the other way; the two disagree.")
    if len(source.split()) < 8:
        may_be_wrong.append("The message is very short, which leaves little to judge.")
    if is_scam and not suspicious:
        may_be_wrong.append("It was flagged without any specific scam phrase; treat it as a caution, not a finding.")
    if not may_be_wrong:
        may_be_wrong.append("Rule matches describe wording, not intent: a real message can use the same words, and a new scam can avoid them.")

    if insufficient:
        summary = "There is not enough specific evidence either way; the result comes from the classifier alone."
    elif conflicts:
        summary = "The evidence is mixed: it contains both scam signs and reassuring phrases."
    elif is_scam:
        summary = f"{len(suspicious)} scam sign{'s' if len(suspicious) != 1 else ''} matched across {sum(j['detected'] for j in journey)} stage(s) of a typical scam."
    elif genuine_txn:
        summary = "It reads like a genuine transaction alert: no request, no link and no number to call."
    elif protective:
        summary = "No scam signs were matched, and it contains reassuring phrases typical of genuine messages."
    else:
        summary = "No strong scam signs were matched."

    return {
        "version": 1,
        "verdict": verdict,
        "risk_level": risk_level,
        "classifier_probability": None if scam_probability is None else round(float(scam_probability), 4),
        "risk_score": None if threat_score is None else round(float(threat_score), 4),
        "summary": summary,
        "evidence_for": suspicious,
        "evidence_against": protective,
        "genuine_transaction": genuine_txn,
        "journey": journey,
        "recommendations": recommendations,
        "similar_pattern": _similar_pattern(source, intents),
        "genuine_contrast": _genuine_contrast(suspicious, source, intents) if is_scam else None,
        "uncertainty": {
            "conflicting": conflicts,
            "insufficient": insufficient,
            "missing_context": missing_context,
            "may_be_wrong": may_be_wrong,
        },
        "disclaimer": DISCLAIMER,
    }
