"""Threat-intelligence correlation (Phase 14).

Every signal this module produces is derived by comparing the CURRENT
scan's own already-computed, real data (entities, registrable domain,
category) against the SAME user's own PAST scans -- already stored,
already real. This is not a threat-intelligence feed, a blocklist, or any
external reputation source: there is no claim here about a domain being
"known malicious" or "on a watchlist" anywhere on the internet. It only
answers one honest question: "has ScamGuard seen this specific
domain/entity/pattern before, in messages YOU submitted?"

Wording discipline: recurrence is evidence worth surfacing, not proof.
Every signal here uses "Suspicious signal detected" phrasing rather than
a definitive claim, and severities stay low/medium -- correlation alone
never justifies "high".
"""
import uuid
from collections import Counter

from sqlalchemy.orm import Session

from app_service.db.postgres.models import Prediction
from app_service.repositories.message_repository import PredictionRepository
from ml_common.security.url_intelligence import EvidenceSignal

# How far back to look for correlation. A real, bounded query -- not
# "all scans ever" -- to keep this a fast, in-process comparison rather
# than an unbounded scan. Sized generously for typical usage.
_CORRELATION_LOOKBACK = 200

_ENTITY_KEYS = ("phones", "emails", "upi_ids", "crypto_wallets", "bank_references")


def _registrable_domain_of(prediction: Prediction) -> str | None:
    metadata = prediction.metadata_ or {}
    url_intel = metadata.get("url_intelligence")
    if not url_intel:
        return None
    return url_intel.get("registrable_domain") or None


def _lookalike_brand_of(prediction: Prediction) -> str | None:
    metadata = prediction.metadata_ or {}
    url_intel = metadata.get("url_intelligence")
    if not url_intel:
        return None
    return url_intel.get("lookalike_of") or None


def correlate(
    db: Session,
    user_id: uuid.UUID,
    current_prediction_id: uuid.UUID | None,
    current_entities: dict | None,
    current_domain: str | None,
    current_lookalike_brand: str | None,
    current_category: str | None,
) -> tuple[EvidenceSignal, ...]:
    """Compares the CURRENT scan's own real data against this same user's
    past scans. Returns () when there's nothing genuinely recurring --
    correlation evidence is never manufactured to fill space.
    """
    past_predictions = [
        p for p in PredictionRepository(db).list_for_user(user_id, skip=0, limit=_CORRELATION_LOOKBACK)
        if p.id != current_prediction_id
    ]
    if not past_predictions:
        return ()

    signals: list[EvidenceSignal] = []

    # 1. Domain recurrence: has this exact registrable domain appeared in
    # any of this user's other scans?
    if current_domain:
        domain_matches = sum(1 for p in past_predictions if _registrable_domain_of(p) == current_domain)
        if domain_matches:
            signals.append(EvidenceSignal(
                "recurring_domain", "medium",
                f"Suspicious signal detected: the domain '{current_domain}' has appeared in "
                f"{domain_matches} of your previous scan{'s' if domain_matches != 1 else ''}. "
                "Repeated appearance alone doesn't confirm anything malicious, but it's worth noting.",
            ))

    # 2. Brand-impersonation recurrence: have OTHER scans also looked like
    # they were impersonating the SAME brand?
    if current_lookalike_brand:
        brand_matches = sum(1 for p in past_predictions if _lookalike_brand_of(p) == current_lookalike_brand)
        if brand_matches:
            signals.append(EvidenceSignal(
                "recurring_brand_impersonation", "medium",
                f"Suspicious signal detected: {brand_matches} of your previous scans also appeared "
                f"to impersonate '{current_lookalike_brand}'. This may indicate a targeted campaign.",
            ))

    # 3. Entity recurrence: has this exact phone/email/UPI ID/wallet/bank
    # reference shown up in any other scan?
    if current_entities:
        for key in _ENTITY_KEYS:
            for value in current_entities.get(key, []) or []:
                match_count = 0
                for p in past_predictions:
                    past_entities = p.highlighted_entities or {}
                    if value in (past_entities.get(key) or []):
                        match_count += 1
                if match_count:
                    signals.append(EvidenceSignal(
                        "recurring_entity", "medium",
                        f"Suspicious signal detected: '{value}' has appeared in {match_count} of your "
                        f"previous scans. Repeated use of the same contact/payment detail across "
                        "unrelated messages is a common scam pattern.",
                    ))

    # 4. Category recurrence: is this the Nth message in this category
    # you've submitted? Weak, informational signal only -- a high count
    # could just mean you use ScamGuard on a lot of similar spam.
    if current_category:
        category_matches = sum(1 for p in past_predictions if p.scam_category == current_category)
        if category_matches >= 3:
            signals.append(EvidenceSignal(
                "recurring_category_pattern", "low",
                f"You've submitted {category_matches} other messages ScamGuard classified as "
                f"'{current_category.replace('_', ' ')}'. This is informational, not itself evidence "
                "about this specific message.",
            ))

    return tuple(signals)


def find_similar_scan_ids(
    db: Session,
    user_id: uuid.UUID,
    current_prediction_id: uuid.UUID,
    current_domain: str | None,
    current_entities: dict | None,
) -> list[str]:
    """Returns the ids of past scans that share a matched domain or
    entity with the current one -- real prediction ids the frontend can
    link to, never a description of an unlinked match.
    """
    past_predictions = PredictionRepository(db).list_for_user(user_id, skip=0, limit=_CORRELATION_LOOKBACK)
    matching_ids: list[str] = []

    current_values = set()
    if current_entities:
        for key in _ENTITY_KEYS:
            current_values.update(current_entities.get(key, []) or [])

    for p in past_predictions:
        if p.id == current_prediction_id:
            continue
        matched = False
        if current_domain and _registrable_domain_of(p) == current_domain:
            matched = True
        if not matched and current_values:
            past_entities = p.highlighted_entities or {}
            for key in _ENTITY_KEYS:
                if current_values & set(past_entities.get(key, []) or []):
                    matched = True
                    break
        if matched:
            matching_ids.append(str(p.id))

    return matching_ids
