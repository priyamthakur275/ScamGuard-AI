"""Public endpoints for the cross-domain SMS spam study (no login, nothing stored)."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app_service.core.rate_limit import limiter
from app_service.services import spam_lab

router = APIRouter(prefix="/public/cross-domain", tags=["cross-domain study"])


class SpamCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    classifier: Literal["logistic_regression", "naive_bayes"] = "logistic_regression"
    version: Literal["baseline", "adapted40"] = "adapted40"


@router.post("/classify")
@limiter.limit("30/minute")
def classify(request: Request, payload: SpamCheckRequest) -> dict:
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Enter an SMS message.")
    return spam_lab.classify(payload.text, payload.classifier, payload.version)


@router.get("/results")
@limiter.limit("60/minute")
def results(request: Request) -> dict:
    return spam_lab.study_summary()
