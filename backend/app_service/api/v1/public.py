"""No-login quick check for the landing page.

Text only, rate limited, never stored: it runs the same pipeline as a
saved scan (MessageService.analyze_ephemeral) but writes nothing to the
database. Anything beyond a quick text check (files, cases, history,
reports) still needs an account.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app_service.core.rate_limit import limiter
from app_service.db.session import get_db
from app_service.schemas.message import AnalysisResult
from app_service.services.extraction import ExtractionService
from app_service.services.message_service import MessageService

router = APIRouter(prefix="/public", tags=["public"])


class QuickCheckRequest(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


@router.post("/quick-check", response_model=AnalysisResult)
@limiter.limit("10/minute")
def quick_check(request: Request, payload: QuickCheckRequest, db: Session = Depends(get_db)) -> AnalysisResult:
    text, metadata = ExtractionService.extract(None, payload.text, "TEXT")
    metadata = {**(metadata or {}), "is_quick_check": True}
    return MessageService(db).analyze_ephemeral(text, "TEXT", metadata)


# --------------------------------------------------------------------------
# Public scam trends: anonymous aggregates only (counts by category, input
# type and day). No message text, numbers, links or user data ever leave
# this endpoint. The shared demo account's seeded scans are excluded so the
# numbers reflect real usage.
# --------------------------------------------------------------------------
import time as _time
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app_service.core.config import get_settings
from app_service.db.postgres.models import Message, Prediction, User

_TRENDS_CACHE: dict[int, tuple[float, dict]] = {}


def _verdict_value(v) -> str:
    return str(getattr(v, "value", v)).lower()


def compute_trends(db: Session, days: int) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    demo_email = get_settings().DEMO_ACCOUNT_EMAIL
    rows = db.execute(
        select(Prediction.verdict, Prediction.scam_category, Prediction.input_type, Prediction.created_at)
        .join(Message, Prediction.message_id == Message.id)
        .outerjoin(User, Message.user_id == User.id)
        .where(Prediction.created_at >= since)
        .where((User.email.is_(None)) | (User.email != demo_email))
    ).all()

    flagged_rows = [r for r in rows if _verdict_value(r.verdict) != "legitimate"]
    categories = Counter((r.scam_category or "uncategorised") for r in flagged_rows)
    channels = Counter((r.input_type or "TEXT").upper() for r in flagged_rows)
    daily_total: Counter[str] = Counter()
    daily_flagged: Counter[str] = Counter()
    for r in rows:
        created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
        day = created.astimezone(timezone(timedelta(hours=5, minutes=30))).date().isoformat()
        daily_total[day] += 1
        if _verdict_value(r.verdict) != "legitimate":
            daily_flagged[day] += 1
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    series = []
    for i in range(min(days, 30) - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        series.append({"date": d, "total": daily_total[d], "flagged": daily_flagged[d]})

    return {
        "days": days,
        "total_scans": len(rows),
        "flagged_scans": len(flagged_rows),
        "flagged_rate": round(len(flagged_rows) / len(rows), 4) if rows else 0.0,
        "top_categories": [{"category": c, "count": n} for c, n in categories.most_common(8)],
        "channels": [{"input_type": c, "count": n} for c, n in channels.most_common()],
        "daily": series,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/trends")
@limiter.limit("60/minute")
def trends(request: Request, days: int = 30, db: Session = Depends(get_db)) -> dict:
    days = 7 if days <= 7 else 30
    cached = _TRENDS_CACHE.get(days)
    if cached and _time.monotonic() - cached[0] < 300:
        return cached[1]
    data = compute_trends(db, days)
    _TRENDS_CACHE[days] = (_time.monotonic(), data)
    return data

