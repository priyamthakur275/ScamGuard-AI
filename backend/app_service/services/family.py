"""Family Guardian mode.

Consent model: the protected person invites a guardian by email; nothing
is shared until that guardian (signed in with that exact email) accepts.
Either side can end it at any time. A guardian only ever sees high-risk
scans (final score >= 0.7) made after the link became active.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app_service.core.config import get_settings
from app_service.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app_service.db.postgres.models import GuardianLink, Message, Prediction, User

MAX_GUARDIANS = 5
ALERT_THRESHOLD = 0.7


def _is_demo(user: User) -> bool:
    return user.email.lower() == get_settings().DEMO_ACCOUNT_EMAIL.lower()


def _link_dict(link: GuardianLink, other: User | None, perspective: str) -> dict:
    return {
        "id": str(link.id),
        "status": link.status,
        "created_at": link.created_at.isoformat() if link.created_at else None,
        "email": link.guardian_email if perspective == "protected" else (other.email if other else None),
        "name": (other.full_name if other else None),
    }


def invite(db: Session, user: User, email: str) -> dict:
    email = (email or "").strip().lower()
    if _is_demo(user):
        raise ForbiddenError("The shared demo account can't add family members.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValidationAppError("Enter a valid email address.")
    if email == user.email.lower():
        raise ValidationAppError("You can't add yourself.")
    existing = db.scalars(select(GuardianLink).where(GuardianLink.protected_id == user.id)).all()
    if any(l.guardian_email == email and l.status != "declined" for l in existing):
        raise ConflictError("You've already invited this person.")
    if sum(1 for l in existing if l.status != "declined") >= MAX_GUARDIANS:
        raise ValidationAppError(f"You can add up to {MAX_GUARDIANS} family members.")
    declined = next((l for l in existing if l.guardian_email == email), None)
    if declined:
        declined.status, declined.guardian_id, declined.responded_at = "pending", None, None
        link = declined
    else:
        link = GuardianLink(protected_id=user.id, guardian_email=email, status="pending")
        db.add(link)
    db.commit()
    db.refresh(link)
    guardian = db.scalar(select(User).where(User.email == email))
    return _link_dict(link, guardian, "protected")


def my_guardians(db: Session, user: User) -> list[dict]:
    links = db.scalars(select(GuardianLink).where(GuardianLink.protected_id == user.id).order_by(GuardianLink.created_at)).all()
    out = []
    for l in links:
        g = db.get(User, l.guardian_id) if l.guardian_id else None
        out.append(_link_dict(l, g, "protected"))
    return out


def _links_for_guardian(db: Session, user: User, status: str | None = None) -> list[GuardianLink]:
    q = select(GuardianLink).where(GuardianLink.guardian_email == user.email.lower())
    if status:
        q = q.where(GuardianLink.status == status)
    return list(db.scalars(q.order_by(GuardianLink.created_at)).all())


def people_i_protect(db: Session, user: User) -> list[dict]:
    out = []
    for l in _links_for_guardian(db, user):
        if l.status == "declined":
            continue
        p = db.get(User, l.protected_id)
        d = _link_dict(l, p, "guardian")
        out.append(d)
    return out


def respond(db: Session, user: User, link_id: uuid.UUID, accept: bool) -> dict:
    link = db.get(GuardianLink, link_id)
    if not link or link.guardian_email != user.email.lower():
        raise NotFoundError("Invitation not found.")
    if accept and _is_demo(user):
        raise ForbiddenError("The shared demo account can't watch over other people.")
    link.status = "active" if accept else "declined"
    link.guardian_id = user.id if accept else None
    link.responded_at = datetime.now(timezone.utc)
    db.commit()
    return _link_dict(link, db.get(User, link.protected_id), "guardian")


def remove(db: Session, user: User, link_id: uuid.UUID) -> None:
    """Either side can end the link."""
    link = db.get(GuardianLink, link_id)
    if not link or (link.protected_id != user.id and link.guardian_email != user.email.lower()):
        raise NotFoundError("Family link not found.")
    db.delete(link)
    db.commit()


def _clean_preview(text: str) -> str:
    """The stored text carries analysis notes appended by the pipeline
    (URL/email/voice evidence, detected concepts); show only what was sent."""
    text = re.split(r"\n+\s*(?:Observed|Detected|Reason:)", text, maxsplit=1)[0]
    text = re.sub(r"^URL(?: Target)?(?: \(fetch blocked\))?:\s*", "", text.strip())
    return " ".join(text.split())[:200]


def alerts(db: Session, user: User, days: int = 30, limit: int = 50) -> list[dict]:
    active = _links_for_guardian(db, user, "active")
    if not active:
        return []
    since_floor = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []
    for link in active:
        start = link.responded_at or link.created_at
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        # A few seconds of grace: some databases store timestamps to the second.
        since = max(since_floor, start - timedelta(seconds=5)) if start else since_floor
        person = db.get(User, link.protected_id)
        rows = db.execute(
            select(Prediction, Message)
            .join(Message, Prediction.message_id == Message.id)
            .where(Message.user_id == link.protected_id)
            .where(Prediction.threat_score >= ALERT_THRESHOLD)
            .where(Prediction.created_at >= since)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
        ).all()
        for pred, msg in rows:
            out.append({
                "id": str(pred.id),
                "link_id": str(link.id),
                "person": (person.full_name or person.email) if person else "Family member",
                "person_email": person.email if person else None,
                "created_at": pred.created_at.isoformat() if pred.created_at else None,
                "threat_score": pred.threat_score,
                "scam_category": pred.scam_category,
                "input_type": pred.input_type,
                "preview": _clean_preview(msg.text or ""),
            })
    out.sort(key=lambda a: a["created_at"] or "", reverse=True)
    return out[:limit]


def summary(db: Session, user: User) -> dict:
    pending = len(_links_for_guardian(db, user, "pending"))
    day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    recent = sum(1 for a in alerts(db, user, days=1) if (a["created_at"] or "") >= day_ago[:19])
    return {"pending_invitations": pending, "recent_alerts": recent}
