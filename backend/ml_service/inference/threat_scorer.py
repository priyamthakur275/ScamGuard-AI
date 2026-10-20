"""Threat score and scam-category inference (step 18).

The classical TF-IDF models output a single scalar: P(scam). They do not
natively output a scam *category* (OTP scam, banking, lottery, ...) or a
discrete risk level. This module derives both from the raw probability
plus a small, explicit, versioned keyword-signal taxonomy -- the same
"urgency indicators, fake rewards, malicious links" signal groups named
in the report's Proposed System section. This keeps category inference
transparent and auditable, rather than another opaque model.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ThreatScoreConfig:
    low_risk_ceiling: float = 0.4
    medium_risk_ceiling: float = 0.7


# Each category maps to a set of *stemmed* signal tokens (matching the
# same stemming rules ml_common.preprocessing.tokenizer applies), so
# category inference runs on the identically-preprocessed token list the
# model itself scored.
_CATEGORY_SIGNALS: dict[str, frozenset[str]] = {
    "phishing": frozenset({"__url__", "click", "login", "secure", "link", "verify", "password", "credential"}),
    "investment_scam": frozenset({"invest", "profit", "return", "stock", "trading", "forex", "double", "guaranteed"}),
    "job_scam": frozenset({"job", "hiring", "salary", "work", "earn", "income", "vacancy", "recruitment"}),
    "lottery_scam": frozenset({"win", "won", "prize", "lottery", "gift", "reward", "claim", "congratulations"}),
    "upi_scam": frozenset({"upi", "gpay", "phonepe", "paytm", "scan", "qr", "collect", "request"}),
    "banking_fraud": frozenset({"bank", "account", "payment", "transaction", "fund", "loan", "credit", "debit"}),
    "identity_theft": frozenset({"aadhaar", "pan", "kyc", "identity", "verification", "document", "ssn", "passport"}),
    "romance_scam": frozenset({"love", "darling", "heart", "relationship", "lonely", "marry", "beautiful"}),
    "crypto_scam": frozenset({"crypto", "bitcoin", "ethereum", "wallet", "blockchain", "token", "nft", "mining"}),
    "fake_delivery": frozenset({"delivery", "package", "shipment", "tracking", "parcel", "courier", "order", "dispatch"}),
    "subscription_scam": frozenset({"subscription", "renew", "expire", "membership", "cancel", "auto", "charge", "billing"}),
    "government_scam": frozenset({"government", "tax", "refund", "irs", "customs", "penalty", "compliance", "notice"}),
    "loan_scam": frozenset({"loan", "emi", "interest", "approved", "disburse", "repay", "borrow", "mortgage"}),
}

_URGENCY_SIGNALS: frozenset[str] = frozenset(
    {"urgent", "immediate", "immediately", "now", "today", "final", "expire", "suspend", "block"}
)


@dataclass(frozen=True)
class ThreatAssessment:
    """The risk engine's own output layer -- explicitly separate from, and
    never a replacement for, the model's raw scam_probability. threat_score
    is a transparent, configurable combination of the model's probability
    plus the keyword-signal taxonomy above; it is allowed to disagree with
    the raw probability (that's the point of having a risk engine at all),
    but it must never be mislabeled as a "calibrated" version of the
    model's own probability -- there is no genuine statistical calibration
    (e.g. Platt scaling fit against held-out labeled data) happening here.
    """
    threat_score: float
    risk_level: str
    scam_category: str | None
    matched_signal_count: int
    intents: tuple[str, ...] = ()
    genuine_transaction: bool = False


# ---------------------------------------------------------------------------
# Intent signals. Topic words ("bank", "OTP", "account") appear in genuine
# messages just as often as in scams, so they no longer move the score on
# their own. What separates a scam is what the message asks you to DO:
# reveal a secret, pay to receive, act within minutes, keep it secret, open
# a disguised link, move money. Each pattern below is a documented,
# weighted piece of evidence; protective phrasing ("never share your OTP",
# "no fee is required") counts as evidence the other way.
# ---------------------------------------------------------------------------
import math
import re

_SECRET = r"(otp|o\.t\.p|one[ -]?time[ -]?password|pin|cvv|password|passcode|verification code|security code|\d[ -]?digit code|code|card (number|details)|card ke peeche|net ?banking credentials|credentials|upi pin)"
_NEG = r"(never|do not|don't|dont|not to|nahi|mat|no one|anyone)"

_INTENTS: tuple[tuple[str, float, re.Pattern[str]], ...] = tuple(
    (name, weight, re.compile(rx, re.I))
    for name, weight, rx in [
        ("asks_for_secret", 0.55, rf"\b(share|tell|send|give|provide|confirm|read out|reply with|enter|fill(?: in)?|submit|type|key in|login with|batao|batayiye|bhej|forward|replying with)\b[^.?!]{{0,40}}\b{_SECRET}\b"),
        ("asks_for_secret", 0.55, rf"\b{_SECRET}\b[^.?!]{{0,30}}\b(batao|batayiye|bhej do|bhejo|share karo|send (it|me)|to (our|the) (executive|officer|agent))"),
        # "I have sent a 6-digit code ... please read it to me": the secret is
        # named first and requested by pronoun in the next clause.
        ("asks_for_secret", 0.55, rf"\b(sent|received|get|got)\b[^?!]{{0,30}}\b{_SECRET}\b[^?!]{{0,80}}\b(read|tell|share|give|say|send|forward)\s+(it|that|this|the same)\b"),
        ("remote_access_app", 0.6, r"\b(anydesk|any desk|teamviewer|quick ?support|rustdesk|screen[ -]?shar\w*)"),
        ("pay_to_receive", 0.45, r"\b(registration|processing|joining|security|onboarding|clearance|delivery|redelivery|customs|exam|activation|gate pass)\s+(fee|charge|charges|deposit|amount|duty)\b"),
        ("pay_to_receive", 0.45, r"\b(pay|deposit|recharge|transfer|bhej\w*)\b[^.?!]{0,50}\b(to|for|then)\s+(claim|receive|release|withdraw|unlock|activate|confirm|book|get)\b"),
        ("pay_to_receive", 0.35, r"\bdeposit\b[^.?!]{0,40}\b(unlock|withdraw|bigger tasks|commission)"),
        ("account_threat", 0.2, r"\b(block(ed)?|suspend(ed)?|freez\w*|frozen|deactivat\w*|disconnect\w*|be cut|cut today|band ho|kat jayega|lapse\w*|banned|on hold|locked|stopped|terminated|ends? in)\b"),
        ("legal_threat", 0.45, r"\b(digital arrest|under arrest|avoid arrest|legal action|fir (is )?(registered|filed)|court case|warrant|money laundering|drug(s)? (parcel|case)|illegal (items|activity|messages)|police (action|case|complaint)|case will be (filed|registered|booked)|(arrest|jail) you|sent to jail)"),
        ("deadline", 0.15, r"\b(today|tonight|immediately|right now|within \d+\s*(hours?|hrs?|minutes?|mins?)|in \d+\s*(hours?|hrs?|minutes?)|urgent\w*|turant|abhi|jaldi|final (notice|reminder)|last chance|expires? today|at midnight)\b"),
        ("suspicious_link", 0.4, r"(bit\.ly|tinyurl|rb\.gy|t\.co/|is\.gd|cutt\.ly|\.(xyz|top|online|click|site|icu|buzz|live|rest|in\.net|tk|ml|ga|cf|gq|zip|work|loan|country|cam)\b|-(verify|kyc|update|refund|claim|billing|help)\w*\.(com|in|net|org))"),
        ("link_with_action", 0.25, r"(https?://|www\.|\b(click|tap|open|visit)\b[^.?!]{0,20}\b(link|here)\b)[^.]{0,80}|\b(link|page|form)\b[^.?!]{0,40}\b(verify|update|claim|pay|renew|redeem|unlock|credentials|details)"),
        ("move_money", 0.45, r"\b(transfer|send|bhej\w*)\b[^.?!]{0,40}\b(safe account|rbi account|this (account|upi|number)|to the officer|officer's account|my account|apne account)"),
        ("move_money", 0.35, r"\b(transfer|send)\s+(rs\.?\s*)?[\d,]{3,}\b[^.?!]{0,30}\b(urgent\w*|immediately|now|account|upi)"),
        ("too_good", 0.4, r"(double your money|guaranteed\s+\d+%|\d+\s*%\s*(daily|per day|weekly)|assured (daily )?(profit|returns?)|daily profit|lucky draw|lottery|you (have )?won|jeet\w*|mubarak ho|selected for (a )?(lucky|prize)|kbc|cashback of)"),
        ("secrecy", 0.4, r"(do not|don't|dont) (tell|inform) (anyone|your family|anybody)|kisi ko (mat|na) bata|stay on (the )?(video )?call|do not disconnect|don't disconnect"),
        ("task_scam", 0.4, r"\b(like|rate|review|subscribe)\w*\b[^.?!]{0,40}\b(earn|per like|per review|rupees per|rs\.?\s*\d+ per)|\bprepaid task\b|\btask (job|account)\b"),
        ("mistaken_transfer", 0.45, r"(by mistake|galti se|wrong(ly)? (transfer|sent)|sent (you )?.{0,20}by mistake)[\s\S]{0,120}?(return|wapas|approve|request|refund)"),
        ("collect_request", 0.4, r"\b(accept|approve)\b[^.?!]{0,30}\b(collect )?request\b[^.?!]{0,40}\b(receive|money|back|cashback|refund)|enter (your )?(upi )?pin to receive"),
        ("new_number_emergency", 0.4, r"(new number|lost my phone|phone (broke|is broken)|friend'?s (phone|number)|met with an accident|stuck at (the )?(airport|customs))"),
        ("impersonation", 0.15, r"\b(rbi|reserve bank|cbi|cyber ?(crime|cell)|police|trai|telecom regulator|customs (officer|department)|narcotics|income tax department|ed officer|enforcement directorate|head office|kyc officer)\b"),
        ("asks_card_details", 0.5, r"\b(card number|expiry|cvv|card details|bank account number)\b[^.?!]{0,40}\b(share|confirm|enter|send|provide|batayiye)|\b(share|confirm|enter|send|provide)\b[^.?!]{0,30}\b(card number|expiry|cvv|card details|bank account number)"),
        ("kyc_update_demand", 0.35, r"\b(update|link|verify|complete|re-?kyc)\b[^.?!]{0,25}\b(kyc|pan|aadhaar)\b[^.?!]{0,60}\b(else|otherwise|or (your|it|the)|will be|to avoid|within|today|immediately|link|click)"),
        ("verify_account_demand", 0.3, r"\b(verify|confirm|validate|reactivate|unlock|secure)\b[^.?!]{0,15}\byour (account|identity|details|wallet|card|profile)\b"),
        ("deceptive_domain", 0.35, r"https?://[^/\s]*\b[a-z0-9]*[-.]?(verify|secure|login|signin|account|update|kyc|wallet|support|billing|refund)[-.][^/\s]*|https?://[^/\s]*(arnaz0n|amaz0n|paypa1|g00gle|faceb00k|micr0soft|app1e|netf1ix|sbi-?online-|hdfc-?bank-|icici-?bank-)"),
        ("insecure_login_page", 0.2, r"http://[^\s]+/(login|signin|verify|account|secure|update|kyc|payment)\b"),
        ("page_collects_secrets", 0.55, r"page inspection: the page collects [^.]*(password|otp|pin|cvv|card number)"),
        ("page_posts_elsewhere", 0.35, r"page inspection: form submits to another site"),
        ("page_impersonates_brand", 0.45, r"page inspection: impersonates "),
        ("new_domain", 0.35, r"domain was registered \d+ days ago"),
        ("harassment", 0.4, r"send your (photos|pictures) to (all )?your contacts|morphed"),
    ]
)

_PROTECTIVE: tuple[tuple[str, float, re.Pattern[str]], ...] = tuple(
    (name, weight, re.compile(rx, re.I))
    for name, weight, rx in [
        ("warns_not_to_share", 0.6, rf"\b{_NEG}\b[^.?!]{{0,25}}\b(share|disclose|tell|give)\b|\bnever (asks?|call\w*)\b[^.?!]{{0,30}}\b{_SECRET}\b"
         # Hinglish puts the negation after the verb: "OTP kisi ke saath share na karein",
         # "bank kabhi bhi OTP nahi maangta".
         rf"|\b(share|bata\w*|bhej\w*)\s+(na|mat|nahi)\b|\b{_SECRET}\b[^.?!]{{0,25}}\bnahi\s+maang\w*"),
        ("official_channel", 0.35, r"\b(not (you|done by you)|if this was(n't| not) you)\b[^.?!]{0,40}\b(call|contact)\b[^.?!]{0,40}\b(official|helpline|back of your card|branch)\b|\b(official (app|website|portal|helpline))\b"),
        # Public awareness messages describe a scam instead of running one.
        ("awareness_warning", 0.6, r"\bbeware of\b|\b(is|are) (a |an )?(common )?(scam|fraud)s?\b|\b(police|banks?|rbi|officers?)\b[^.?!]{0,30}\bnever (ask|arrest|call|demand)\w*\b"),
        ("no_fee", 0.4, r"\bno (fee|charges?|payment) (is )?(required|needed)|\bthere is no fee\b|\bfree of cost\b"),
        # A bank alert that names only the masked account ("A/c XX4821") and the
        # amount is how genuine debit/credit SMS look; scam texts that copy it
        # still carry their own ask (sent-by-mistake, collect request, OTP).
        ("transaction_alert", 0.4, r"\b(debited|credited|withdrawn|spent)\b[^.?!]{0,40}\b(a/?c|acct|account|card)\s*(no\.?\s*)?(x+|\*+)\d{3,4}\b"
         r"|\b(a/?c|acct|account|card)\s*(no\.?\s*)?(x+|\*+)\d{3,4}\b[^.?!]{0,40}\b(debited|credited)\b"),
        ("status_update", 0.3, r"\b(has been|have been|is|are|was|were|will be|got) (successfully )?(credited|processed|delivered|confirmed|received|resolved|verified|generated|shipped|completed|booked|matured|granted|dispatched|published|cleared|ported|renewed|updated|approved|scheduled|settled)\b|\bsuccessful(ly)?\b|\bpayment (status:?\s*)?(received|successful|confirmed)\b"),
        # Genuine service notices tell you how to REPORT spam or fraud to the
        # official channels (TRAI DND 1909, cyber helpline 1930, Chakshu).
        ("official_report_channel", 0.6, r"\b(complain\w*|report\w*|register (a )?complaint|activate dnd|dnd|unwanted (sms|calls?))\b[^.?!]{0,90}\b(1909|1930|155260|cybercrime\.gov\.in|sancharsaathi(\.gov\.in)?|chakshu)\b"
         r"|\b(1909|1930|155260|cybercrime\.gov\.in|sancharsaathi(\.gov\.in)?|chakshu)\b[^.?!]{0,60}\b(complain\w*|report\w*|dnd|fraud)\b"),
        # Delivery and ride OTPs are meant to be shared, in person, only at
        # handover ("share OTP 4821 with the delivery agent only at delivery").
        ("delivery_otp", 0.5, r"\b(otp|code|pin)\b[^.?!]{0,60}\b(delivery (agent|partner|executive|boy|person)|driver|rider|captain)\b[^.?!]{0,40}\bonly\b"
         r"|\b(share|give|tell)\b[^.?!]{0,40}\b(otp|code|pin)\b[^.?!]{0,60}\bonly (at the time of|on|upon|after) (delivery|handover)\b"
         r"|\b(otp|code|pin)\b[^?!]{0,70}\b(driver|rider|captain|delivery (agent|partner|executive))\b[^.?!]{0,20}\bonly (when|at|on|upon|after)\b"
         r"|\b(otp|code|pin)\b[^?!]{0,70}\bonly when you (start|begin|board) (the|your) (trip|ride|journey)\b"),
        # Pointing you to the official app or portal rather than a link or number.
        # Banks tell you how to block your own card: "Not you? SMS BLOCK to 56161600".
        ("block_instruction", 0.4, r"\b(sms|send|text)\s+['\"]?block\b[^.?!]{0,30}\bto\s+\d{5,8}\b|\bnot you\?[^.?!]{0,40}\bblock\b"),
        ("official_app", 0.35, r"\b(on|in|via|through|using|from) the (official )?[a-z][\w-]*( [a-z][\w-]*){0,2} (app|portal|website)\b|\bvia netbanking\b|\bnetbanking or\b"),
    ]
)


_ALERT_OVERRIDES = frozenset({
    "mistaken_transfer", "collect_request", "asks_for_secret", "asks_card_details", "move_money",
    "pay_to_receive", "suspicious_link", "link_with_action", "remote_access_app", "verify_account_demand",
})


# Genuine transaction guard. The TF-IDF model is overconfident on Indian
# bank alerts (a salary credit SMS scores about 0.96) because the public
# training data has few of them. A message that only reports money moving on
# a masked account, carries no request, no link, no mobile number to call and
# no app to install cannot be used to steal anything, so its final score is
# capped. Any scam intent, or any of the blockers below, disables the guard.
_MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
_TXN_FORM = re.compile(
    r"\b(debited|credited|withdrawn|spent|deposited|received)\b[^.?!]{0,60}\b(a/?c|acct|account|card)\s*(no\.?\s*)?(x+|\*+)\d{3,4}\b"
    r"|\b(a/?c|acct|account|card)\s*(no\.?\s*)?(x+|\*+)\d{3,4}\b[^.?!]{0,60}\b(debited|credited|deposited)\b"
    r"|\b(debited|spent|used)\b[^.?!]{0,60}\b(card|a/?c|account)\s+ending\s+(in\s+)?\d{4}\b"
    r"|\bsalary\b[^.?!]{0,60}\b(credited|deposited|processed|paid)\b|\b(credited|deposited)\b[^.?!]{0,60}\bsalary\b"
    r"|\b(emi|bill|premium|instal+ment)\b[^.?!]{0,60}\b(is due|due on|due date)\b"
    rf"|\bsalary for (the month of )?{_MONTHS}\b",
    re.I,
)
_TXN_ANCHOR = re.compile(
    r"\b(a/?c|acct|account|card)\s*(no\.?\s*)?(x+|\*+)\d{3,4}\b|\b(card|a/?c|account)\s+ending\s+(in\s+)?\d{4}\b|\bavl\.? ?bal|\bavailable balance\b|\b(upi )?ref(erence)?\.? ?(no\.?)?:? ?\d{6,}|\butr\b",
    re.I,
)
_TXN_BLOCKERS = re.compile(
    r"https?://|www\.|\b[a-z0-9-]+\.(xyz|top|link|online|site|live|shop|info|click)\b|bit\.ly"
    r"|\b(install|download|apk|anydesk|teamviewer|quicksupport|click|tap here)\b"
    r"|\b(by mistake|galti|wrongly|return (it|the|money|amount)|send (it|money|back)|refund it)\b"
    r"|\b(kyc|pan card|aadhaar|update your|verify your|blocked|suspend\w*|expire\w*)\b"
    r"|\b(pay|paying)\s+(rs\.?|inr|₹|\d|now|a|the|fee|charges?)\b|\b(fee|charges? of|processing|claim|lottery|prize|reward)\b"
    r"|(?<!\d)(\+?91[\s-]?)?[6-9]\d{9}(?!\d)",
    re.I,
)
_OTP_WORD = re.compile(r"\b(otp|pin|cvv|password)\b", re.I)


def is_genuine_transaction(text: str, found: dict[str, float], protective: dict[str, float]) -> bool:
    if found:
        return False
    flat = " ".join(text.split())
    if not (_TXN_FORM.search(flat) and _TXN_ANCHOR.search(flat)):
        return False
    if _TXN_BLOCKERS.search(flat):
        return False
    if _OTP_WORD.search(flat) and "warns_not_to_share" not in protective:
        return False
    return True


GENUINE_TRANSACTION_CAP = 0.15

# Genuine notice guard: the same idea for service notices (passport granted,
# EPF credited, number ported, report spam to 1909, data usage). The model is
# overconfident on them because its public training data is UK spam, where
# "call", "send SMS to" and links were mostly spam. A notice that reports
# something or points to an official channel, with no request for money,
# details, an install or a call to a mobile number, and no unofficial link,
# cannot be used to steal anything.
_OFFICIAL_DOMAIN = re.compile(
    r"^([\w-]+\.)*(gov\.in|nic\.in|airtel\.in|jio\.com|amazon\.in|flipkart\.com|sbi\.co\.in|onlinesbi\.sbi|hdfcbank\.com|icicibank\.com|"
    r"axisbank\.com|irctc\.co\.in|paytm\.com|phonepe\.com|myntra\.com|swiggy\.com|zomato\.com|npci\.org\.in|rbi\.org\.in)$",
    re.I,
)
_ANY_LINK = re.compile(r"(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:/\S*)?", re.I)
_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd", "i.airtel.in"}
_NOTICE_BLOCKERS = re.compile(
    r"\b(install|download|apk|anydesk|teamviewer|quicksupport|click|tap here)\b"
    r"|\b(by mistake|galti|wrongly|return (it|the|money|amount)|send (it|money|back)|refund it)\b"
    r"|\b(update your|verify your|link your|re-?kyc|kyc (update|pending|expired)|blocked|suspend\w*|deactivat\w*|disconnect\w*)\b"
    r"|\b(pay|paying)\s+(rs\.?|inr|₹|\d|now|a|the|fee|charges?)\b|\b(fee|charges? of|processing fee|claim|lottery|prize|reward|won|winner)\b"
    r"|(?<!\d)(\+?91[\s-]?)?[6-9]\d{9}(?!\d)|(?<!\d)0\d{9,11}(?!\d)|\+\d{1,3}[\s-]?\d{6,}"
    # offers and calls to action are not notices
    r"|\bfree\b|\b(to|and) (activate|claim|redeem|unlock|collect)\b|\b(call|text|sms|reply|dial)\s+(now|back|\w+\s+to\s+\d{4,})\b|\bcall\s+\d{6,}"
    r"|\b(congratulations|congrats|selected|winner|cash|bonus|offer expires|limited time)\b",
    re.I,
)
_NOTICE_SIGNALS = {"block_instruction", "status_update", "official_report_channel", "official_app", "official_channel", "delivery_otp", "warns_not_to_share"}


def _links_are_safe(text: str, report_notice: bool) -> bool:
    for m in _ANY_LINK.finditer(text):
        host = m.group(1).lower()
        if "." not in host or host.replace(".", "").isdigit() or re.fullmatch(r"[\d.,]+", host):
            continue
        if host.split(".")[-1] in {"rs", "inr"}:
            continue
        if _OFFICIAL_DOMAIN.match(host):
            continue
        if host in _SHORTENERS and report_notice:
            continue  # official "report spam" notices use short links to their own apps
        return False
    return True


# A completed event reported in plain words ("has been recharged", "has
# been topped up"). Used only inside the notice guard, never as evidence
# on its own, because "has been blocked" is a scam threat (blockers catch it).
_COMPLETED_EVENT = re.compile(r"\b(has|have) been (successfully )?[a-z]+(ed|en)\b|\b(has|have) been (successfully )?[a-z]+ up\b", re.I)
_OFFER_OR_CHAT = re.compile(
    r"\b(txt|text|sms|reply|ansr|chat|date|dating|singles|quiz|win|won|prize|deals?|coupon|off on|discount|offer|compt?\w*|"
    r"join|contact|whatsapp|telegram|invest|deposit|apply|register|visit|login|enter|share|verify|update|activate|call|dial|press|scan|approve)\b|!",
    re.I,
)


def is_genuine_notice(text: str, found: dict[str, float], protective: dict[str, float]) -> bool:
    flat = " ".join(text.split())
    if not (_NOTICE_SIGNALS & protective.keys()):
        # No reassuring signal: only a plain report of a completed event
        # qualifies, with no scam intent, offer, chat line or request.
        if found or not _COMPLETED_EVENT.search(flat) or _OFFER_OR_CHAT.search(flat):
            return False
    report_notice = "official_report_channel" in protective
    allowed = {"impersonation", "deadline"} | ({"suspicious_link", "link_with_action"} if report_notice else set())
    if set(found) - allowed:
        return False
    if _NOTICE_BLOCKERS.search(flat) or not _links_are_safe(flat, report_notice):
        return False
    if _OTP_WORD.search(flat) and not ({"warns_not_to_share", "delivery_otp"} & protective.keys()):
        return False
    return True


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


class ThreatScorer:
    """Final risk engine: fuses the model's probability with intent
    evidence in log-odds space, so the result behaves like a probability:

        logit(final) = logit(model_p) + evidence_for - evidence_against

    A message the model is unsure about (p = 0.3) but that asks for an OTP
    and sets a deadline ends up near 0.9; a genuine "never share your OTP"
    bank SMS the model mis-scored at 0.6 is pulled back below 0.3. The
    model's own probability is still reported untouched alongside it.
    """

    _GAIN = 5.0  # log-odds per unit of intent weight
    _MODEL_LOGIT_CAP = 4.0  # TF-IDF models are overconfident at the extremes

    def __init__(self, config: ThreatScoreConfig | None = None):
        self._config = config or ThreatScoreConfig()

    @staticmethod
    def intents(raw_text: str) -> tuple[dict[str, float], dict[str, float]]:
        text = " ".join(raw_text.split())
        found: dict[str, float] = {}
        for name, weight, rx in _INTENTS:
            if rx.search(text):
                found[name] = max(found.get(name, 0.0), weight)
        protective: dict[str, float] = {}
        for name, weight, rx in _PROTECTIVE:
            if rx.search(text):
                protective[name] = weight
        # "Do not share your OTP" also matches the share-a-secret pattern;
        # the warning wins when it is the only thing asking about secrets.
        if "warns_not_to_share" in protective or "delivery_otp" in protective:
            found.pop("asks_for_secret", None)
        if "block_instruction" in protective:
            found.pop("account_threat", None)
        # A copied bank-alert format is no comfort when the text also asks for
        # something (fake "credited by mistake" or refund SMS).
        if found.keys() & _ALERT_OVERRIDES or _TXN_BLOCKERS.search(text):
            protective.pop("transaction_alert", None)
        return found, protective

    def assess(self, scam_probability: float, tokens: list[str], raw_text: str = "", ignore_intents: tuple[str, ...] = ()) -> ThreatAssessment:
        text = raw_text or " ".join(tokens)
        text_lower = text.lower()
        token_set = set(tokens)

        found, protective = self.intents(text)
        for name in ignore_intents:
            found.pop(name, None)
        evidence_for = sum(found.values())
        # Weak context signals only count once a real intent is present.
        if set(found) <= {"deadline", "impersonation", "account_threat", "link_with_action"}:
            evidence_for *= 0.5
        evidence_against = sum(protective.values()) if evidence_for < 0.5 else 0.5 * sum(protective.values())

        model_logit = max(-self._MODEL_LOGIT_CAP, min(self._MODEL_LOGIT_CAP, _logit(scam_probability)))
        logit = model_logit + self._GAIN * (evidence_for - evidence_against)
        threat_score = 1 / (1 + math.exp(-logit))
        genuine_transaction = is_genuine_transaction(text, found, protective) or is_genuine_notice(text, found, protective)
        if genuine_transaction:
            threat_score = min(threat_score, GENUINE_TRANSACTION_CAP)

        category_scores: dict[str, int] = {}
        for category, signals in _CATEGORY_SIGNALS.items():
            hits = len(token_set & signals) + sum(1 for sig in signals if sig in text_lower)
            category_scores[category] = hits
        best_category, best_count = max(category_scores.items(), key=lambda item: item[1])
        chosen_category = None
        if threat_score >= 0.5:
            chosen_category = self._category_from_intents(found, text, category_scores)
            if chosen_category is None:
                if best_count > 0:
                    chosen_category = best_category
                elif "suspicious_link" in found or "link_with_action" in found:
                    chosen_category = "phishing"

        urgency_hits = len(token_set & _URGENCY_SIGNALS)
        return ThreatAssessment(
            threat_score=round(threat_score, 4),
            risk_level=self._risk_level_for(threat_score),
            scam_category=chosen_category,
            matched_signal_count=len(found) + urgency_hits,
            intents=tuple(sorted(found)),
            genuine_transaction=genuine_transaction,
        )

    def _risk_level_for(self, threat_score: float) -> str:
        if threat_score < self._config.low_risk_ceiling:
            return "low"
        if threat_score < self._config.medium_risk_ceiling:
            return "medium"
        return "high"

    @staticmethod
    def _category_from_intents(found: dict[str, float], text: str, category_scores: dict[str, int]) -> str | None:
        """Name the scam by what it asks for when that is unambiguous.

        Keyword counts alone mislabel some scams: a "digital arrest" call that
        mentions an RBI account counts as banking, and a bare link to a fake
        "reward points" site counts as a lottery. The intents say what the
        message actually wants, so they take priority when they are decisive.
        """
        if "legal_threat" in found:
            return "government_scam"  # fake police / CBI / customs, "digital arrest"
        if "task_scam" in found:
            return "job_scam"
        if "collect_request" in found or "mistaken_transfer" in found:
            return "upi_scam"
        # The message itself, without the evidence notes the pipeline appends.
        core = re.split(r"\n\s*(Detected language/concepts|Observed URL signals|Observed email signals)", text)[0]
        core = re.sub(r"^\s*URL Target:\s*", "", core)
        without_links = re.sub(r"(https?://|www\.)\S+", " ", core, flags=re.I)
        if len(re.sub(r"\W+", "", without_links)) < 12 and re.search(r"(https?://|www\.)\S+", core, flags=re.I):
            return "phishing"  # the input is essentially just a link
        if ("asks_for_secret" in found or "asks_card_details" in found) and category_scores.get("banking_fraud", 0) > 0:
            return "banking_fraud"  # OTP / PIN / card details for a bank account
        return None

    @staticmethod
    def _best_category(category_scores: dict[str, int]) -> str | None:
        best_category, best_count = max(category_scores.items(), key=lambda item: item[1])
        return best_category if best_count > 0 else None
