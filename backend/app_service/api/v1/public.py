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
