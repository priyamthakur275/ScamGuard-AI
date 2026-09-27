from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app_service.api.deps import get_current_user
from app_service.core.rate_limit import limiter
from app_service.db.postgres.models import User
from app_service.db.session import get_db
from app_service.schemas.analytics import AnalyticsSummary
from app_service.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
@limiter.limit("60/minute")
def get_analytics_summary(
    request: Request,
    range: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummary:
    service = AnalyticsService(db)
    return service.summary(current_user.id, range)
