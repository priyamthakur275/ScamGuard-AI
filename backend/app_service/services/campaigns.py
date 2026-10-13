"""Scam campaign fingerprint.

Groups a scam into a named, recurring fraud campaign (for example "Fake SBI
YONO / KYC block") using transparent text patterns, and counts how many
scans across all ScamGuard users matched the same campaign in the last 30
days. Counts are anonymous: no message text or user leaves the server.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app_service.db.postgres.models import Message, Prediction

# id, display name, what the fraud wants, pattern (all must be specific enough
# that a genuine bank or delivery message does not match on its own).
CAMPAIGNS: tuple[tuple[str, str, str, re.Pattern], ...] = tuple(
    (cid, name, goal, re.compile(rx, re.I | re.S))
    for cid, name, goal, rx in (
        ("kyc_block", "Fake bank KYC / account-block", "Steals your OTP or net-banking login",
         r"(kyc|pan|aadhaar|yono|net ?banking).{0,120}(block|suspend|band|deactivat|expire)|(block|suspend|band|deactivat).{0,120}(kyc|pan|yono)"),
        ("digital_arrest", "\"Digital arrest\" / fake police", "Scares you into transferring money to a 'safe account'",
         r"digital arrest|cyber ?crime.{0,80}(arrest|parcel|drugs|warrant)|(cbi|police|narcotics|customs).{0,80}(arrest|parcel|drugs|warrant)"),
        ("task_job", "Paid tasks / work-from-home job", "Asks a registration fee or deposits before 'payouts'",
         r"(like|rate|review|subscribe).{0,60}(earn|per (like|task|review))|earn.{0,60}(lik(e|ing)|review|subscrib|task)|(part[- ]?time|work from home|data entry).{0,160}(fee|deposit|registration|pay)"),
        ("power_cut", "Electricity disconnection", "Pushes a fake bill payment link or remote-access app",
         r"(electricity|power|bescom|bill).{0,120}(disconnect|cut|tonight)"),
        ("courier_customs", "Courier / customs held parcel", "Collects a fake duty or redelivery fee",
         r"(parcel|courier|shipment|package|india ?post).{0,120}(customs|held|duty|redeliver|address)"),
        ("upi_refund", "UPI collect / 'sent by mistake'", "Tricks you into approving a payment request",
         r"(by mistake|galti se|wrong(ly)? (sent|transfer)).{0,120}(return|refund|wapas)|(approve|accept).{0,60}(collect )?request|upi pin.{0,40}receive"),
        ("investment_group", "Stock / crypto 'guaranteed returns' group", "Takes deposits into a fake trading app",
         r"(guaranteed|double your|assured).{0,80}(return|profit|money)|(trading|stock|crypto|forex) (group|tips|app)"),
        ("prize_lottery", "Lottery / KBC prize", "Charges a 'processing fee' to release a prize",
         r"(lottery|kbc|lucky draw|you (have )?won|prize).{0,160}(fee|claim|charge|tax|pay)"),
        ("fake_login_link", "Look-alike login page", "Captures passwords and OTPs on a fake site",
         r"https?://[^\s]*(paypa1|amaz0n|g00gle|-verify|-secure|-login|-kyc|verify-|secure-|login-)[^\s]*"),
    )
)

_CACHE: dict[str, tuple[float, int]] = {}
_TTL = 300  # seconds


def match(text: str) -> tuple[str, str, str] | None:
    for cid, name, goal, rx in CAMPAIGNS:
        if rx.search(text or ""):
            return cid, name, goal
    return None


def count_recent(db: Session, campaign_id: str, days: int = 30, limit: int = 3000) -> int:
    cached = _CACHE.get(campaign_id)
    if cached and time.monotonic() - cached[0] < _TTL:
        return cached[1]
    rx = next(c[3] for c in CAMPAIGNS if c[0] == campaign_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    texts = db.scalars(
        select(Message.text)
        .join(Prediction, Prediction.message_id == Message.id)
        .where(Prediction.created_at >= since, Prediction.threat_score >= 0.5)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
    ).all()
    n = sum(1 for t in texts if rx.search(t or ""))
    _CACHE[campaign_id] = (time.monotonic(), n)
    return n


def fingerprint(db: Session | None, text: str) -> dict | None:
    hit = match(text)
    if not hit:
        return None
    cid, name, goal = hit
    seen = 0
    if db is not None:
        try:
            seen = count_recent(db, cid)
        except Exception:
            seen = 0
    return {"id": cid, "name": name, "goal": goal, "seen_30d": seen}
