"""Look up a phone number in the current user's own saved scans.

Deliberately scoped to the user's own history (the same rule as the
correlation feature): ScamGuard has no external phone-reputation source,
so it reports only what this user has actually seen, plus whether the
number is a well-formed Indian mobile number.
"""
import re
import uuid

from sqlalchemy.orm import Session

from app_service.repositories.message_repository import PredictionRepository

_INDIAN_MOBILE = re.compile(r"^\+91[6-9]\d{9}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return f"+91{digits}" if len(digits) == 10 else digits


def lookup_phone(db: Session, user_id: uuid.UUID, raw_number: str, max_scans: int = 1000) -> dict:
    number = normalize_phone(raw_number)
    matches = []
    for prediction in PredictionRepository(db).list_for_user(user_id, limit=max_scans):
        phones = (prediction.highlighted_entities or {}).get("phones") or []
        if number in phones:
            matches.append(prediction)
    matches.sort(key=lambda p: p.created_at)
    flagged = [p for p in matches if p.verdict != "legitimate"]
    return {
        "number": number,
        "is_valid_indian_mobile": bool(_INDIAN_MOBILE.match(number)),
        "seen_count": len(matches),
        "flagged_count": len(flagged),
        "first_seen": matches[0].created_at.isoformat() if matches else None,
        "last_seen": matches[-1].created_at.isoformat() if matches else None,
        "scans": [
            {
                "id": str(p.id),
                "verdict": getattr(p.verdict, "value", p.verdict),
                "threat_level": p.threat_level,
                "scam_category": p.scam_category,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "preview": (p.message.text[:120] if p.message else ""),
            }
            for p in reversed(matches[-5:])
        ],
    }
