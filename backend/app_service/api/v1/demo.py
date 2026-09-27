from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app_service.api.deps import get_current_user
from app_service.core.rate_limit import limiter
from app_service.db.postgres.models import User
from app_service.db.session import get_db
from app_service.schemas.message import AnalysisResult
from app_service.services.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/examples")
def list_demo_examples(
    request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[dict]:
    return DemoService(db).list_examples()


@router.post("/examples/{example_id}/run", response_model=AnalysisResult)
@limiter.limit("30/minute")
def run_demo_example(
    request: Request,
    example_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisResult:
    return DemoService(db).run_example(example_id)
