"""Scam X-Ray: where exactly in the message the trap is.

Uses the same intent patterns as the risk engine (threat_scorer._INTENTS),
but returns character spans in the user's own text, each with a plain
explanation, grouped into the four stages most scams follow:

  hook      -> why you'd engage (prize, job, "officer", a lost-phone relative)
  pressure  -> why you'd hurry (deadline, block/arrest threat, secrecy)
  ask       -> what they want from you (OTP, PIN, card, KYC, AnyDesk)
  cashout   -> how the money or data leaves (pay a fee, transfer, a fake link)
"""

from __future__ import annotations

from ml_service.inference.threat_scorer import _INTENTS, _PROTECTIVE

STAGES = ("hook", "pressure", "ask", "cashout")

INTENT_INFO: dict[str, tuple[str, str, str]] = {
    # intent: (stage, short label, why it matters)
    "impersonation": ("hook", "Pretends to be an authority", "Scammers borrow the name of a bank, police, RBI or TRAI so you trust them."),
    "too_good": ("hook", "Too good to be true", "Prizes, guaranteed returns and lucky draws you never entered are bait."),
    "new_number_emergency": ("hook", "Unknown 'relative' in trouble", "A new number claiming to be family, asking for money, is a classic trick."),
    "mistaken_transfer": ("hook", "Fake 'sent by mistake'", "No money actually arrived; the 'refund' request makes you send money."),
    "task_scam": ("hook", "Paid tasks", "Earning by liking or reviewing is how task scams start before asking for deposits."),
    "deadline": ("pressure", "Artificial deadline", "Urgency stops you from checking with someone first."),
    "account_threat": ("pressure", "Threat to block or cut service", "Banks and utilities don't threaten disconnection by SMS from random numbers."),
    "legal_threat": ("pressure", "Arrest or legal threat", "Police and agencies never settle cases on a call; 'digital arrest' does not exist."),
    "secrecy": ("pressure", "Asks you to keep it secret", "Isolating you from family is a strong sign of fraud."),
    "asks_for_secret": ("ask", "Asks for OTP / PIN / password", "No genuine bank, company or officer will ever ask for these."),
    "asks_card_details": ("ask", "Asks for card or account details", "Card number, expiry and CVV are enough to steal money."),
    "verify_account_demand": ("ask", "'Verify your account'", "A classic phishing prompt that leads to a fake login page."),
    "kyc_update_demand": ("ask", "KYC / PAN / Aadhaar update demand", "KYC is done at the branch or official app, never through an SMS link."),
    "remote_access_app": ("ask", "Remote-access app", "AnyDesk/TeamViewer lets the caller see your screen, OTPs and banking apps."),
    "collect_request": ("ask", "'Approve the request'", "Approving a UPI request or entering your PIN sends money; you never need a PIN to receive."),
    "pay_to_receive": ("cashout", "Pay a fee to receive", "Real prizes, jobs and refunds never need an upfront fee."),
    "move_money": ("cashout", "Asks you to transfer money", "Money sent to a 'safe account' or unknown UPI is gone."),
    "suspicious_link": ("cashout", "Suspicious link", "Short links and cheap domains (.xyz, .top) hide where you'll land."),
    "link_with_action": ("cashout", "Link to act on", "Links that ask you to verify, pay or claim often lead to fake pages."),
    "deceptive_domain": ("cashout", "Look-alike website", "The domain imitates a brand but is not its official site."),
    "insecure_login_page": ("cashout", "Unencrypted login page", "A login page on plain http:// sends what you type in the clear."),
    "page_collects_secrets": ("cashout", "Page collects passwords/OTP", "The linked page has a form for sensitive details."),
    "page_posts_elsewhere": ("cashout", "Data sent to another site", "The form secretly submits to a different website."),
    "page_impersonates_brand": ("cashout", "Fake brand page", "The page shows a brand's name on a domain that isn't theirs."),
    "new_domain": ("cashout", "Brand-new website", "The site was registered recently; scam sites rarely live long."),
    "harassment": ("pressure", "Blackmail threat", "Threats to share your photos are extortion; report it, don't pay."),
}

PROTECTIVE_INFO = {
    "warns_not_to_share": "Tells you not to share your OTP — genuine messages do this.",
    "official_channel": "Points you to an official channel, not a number in the message.",
    "no_fee": "Says no fee is required.",
    "status_update": "Just confirms something that already happened.",
}


def xray(text: str, max_chars: int = 1500) -> dict:
    text = text[:max_chars]
    spans: list[dict] = []
    for name, _weight, rx in _INTENTS:
        info = INTENT_INFO.get(name)
        if not info:
            continue
        for m in rx.finditer(text):
            if m.end() - m.start() < 2:
                continue
            spans.append({"start": m.start(), "end": m.end(), "intent": name, "stage": info[0], "label": info[1], "why": info[2]})
    reassuring = [PROTECTIVE_INFO[n] for n, _w, rx in _PROTECTIVE if rx.search(text) and n in PROTECTIVE_INFO]

    # Keep spans non-overlapping: prefer earlier, then longer ones.
    spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    merged: list[dict] = []
    for s in spans:
        if merged and s["start"] < merged[-1]["end"]:
            continue
        merged.append(s)

    stages = {stage: [] for stage in STAGES}
    for s in merged:
        if s["label"] not in stages[s["stage"]]:
            stages[s["stage"]].append(s["label"])
    return {"text": text, "spans": merged, "stages": stages, "reassuring": reassuring}
