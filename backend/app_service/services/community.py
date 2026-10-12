"""Community scam reports: normalisation, reporting and lookup."""

from __future__ import annotations

import re
import uuid
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app_service.db.postgres.models import CommunityReport
from app_service.services.phone_lookup import normalize_phone

INDICATOR_TYPES = ("phone", "url", "upi", "email")
# Entity keys produced by the analysis pipeline -> indicator type.
ENTITY_KEYS = {"phones": "phone", "urls": "url", "shortened_links": "url", "upi_ids": "upi", "emails": "email"}


def normalize(indicator_type: str, value: str) -> str:
    value = (value or "").strip()
    if indicator_type == "phone":
        return normalize_phone(value)
    if indicator_type == "url":
        candidate = value if "://" in value else f"http://{value}"
        host = (urlparse(candidate).hostname or "").lower()
        return host[4:] if host.startswith("www.") else host
    return value.lower()


def is_valid(indicator_type: str, value: str) -> bool:
    if indicator_type == "phone":
        return bool(re.fullmatch(r"\+91[6-9]\d{9}|\d{5,15}", value))
    if indicator_type == "url":
        return "." in value and len(value) <= 253
    if indicator_type == "upi":
        return bool(re.fullmatch(r"[a-z0-9.\-_]{2,256}@[a-z]{2,64}", value))
    if indicator_type == "email":
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))
    return False


def report(db: Session, user_id: uuid.UUID, indicator_type: str, raw_value: str, category: str | None = None) -> tuple[str, bool]:
    """Returns (normalised value, created). Reporting twice is a no-op."""
    value = normalize(indicator_type, raw_value)
    if not is_valid(indicator_type, value):
        raise ValueError(f"That does not look like a valid {indicator_type}.")
    exists = db.scalar(
        select(CommunityReport.id).where(
            CommunityReport.indicator_type == indicator_type,
            CommunityReport.indicator_value == value,
            CommunityReport.reporter_id == user_id,
        )
    )
    if exists:
        return value, False
    db.add(CommunityReport(indicator_type=indicator_type, indicator_value=value, reporter_id=user_id, category=category))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return value, False
    return value, True


def lookup(db: Session, indicator_type: str, raw_value: str) -> dict:
    value = normalize(indicator_type, raw_value)
    row = db.execute(
        select(func.count(CommunityReport.id), func.max(CommunityReport.created_at)).where(
            CommunityReport.indicator_type == indicator_type, CommunityReport.indicator_value == value
        )
    ).one()
    cats = db.execute(
        select(CommunityReport.category, func.count(CommunityReport.id))
        .where(CommunityReport.indicator_type == indicator_type, CommunityReport.indicator_value == value)
        .group_by(CommunityReport.category)
    ).all()
    return {
        "indicator_type": indicator_type,
        "indicator_value": value,
        "report_count": int(row[0] or 0),
        "last_reported_at": row[1].isoformat() if row[1] else None,
        "categories": {c or "unspecified": n for c, n in cats},
    }


def reports_for_entities(db: Session, entities: dict | None) -> list[dict]:
    """Community report counts for every number/link/UPI/email in a scan."""
    if not entities:
        return []
    wanted: dict[tuple[str, str], str] = {}
    for key, itype in ENTITY_KEYS.items():
        for raw in entities.get(key) or []:
            norm = normalize(itype, str(raw))
            if norm:
                wanted[(itype, norm)] = str(raw)
    if not wanted:
        return []
    rows = db.execute(
        select(CommunityReport.indicator_type, CommunityReport.indicator_value, func.count(CommunityReport.id))
        .where(CommunityReport.indicator_value.in_([v for _, v in wanted]))
        .group_by(CommunityReport.indicator_type, CommunityReport.indicator_value)
    ).all()
    return [
        {"indicator_type": t, "indicator_value": v, "display": wanted[(t, v)], "report_count": int(n)}
        for t, v, n in rows
        if (t, v) in wanted
    ]
