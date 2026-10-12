"""Community scam reports (numbers, link domains, UPI IDs, emails)."""
from typing import Literal

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app_service.api.deps import get_current_user
from app_service.core.exceptions import ValidationAppError
from app_service.core.rate_limit import limiter
from app_service.db.session import get_db
from app_service.services import community

router = APIRouter(prefix="/community", tags=["community"])
IndicatorType = Literal["phone", "url", "upi", "email"]


class ReportIn(BaseModel):
    indicator_type: IndicatorType
    value: str = Field(min_length=3, max_length=500)
    category: str | None = Field(default=None, max_length=64)


@router.post("/reports", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_report(request: Request, payload: ReportIn, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    try:
        value, created = community.report(db, user.id, payload.indicator_type, payload.value, payload.category)
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc
    return {**community.lookup(db, payload.indicator_type, value), "created": created}


@router.get("/lookup")
@limiter.limit("60/minute")
def lookup(request: Request, indicator_type: IndicatorType, value: str, db: Session = Depends(get_db)) -> dict:
    return community.lookup(db, indicator_type, value)
