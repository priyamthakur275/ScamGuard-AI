import os
import asyncio
from fastapi import APIRouter, BackgroundTasks
import httpx

from app_service.core.config import get_settings

settings = get_settings()
from app_service.core.rate_limit import limiter

router = APIRouter(tags=["system"])


async def _wake_ml_service():
    """Fire-and-forget background ping to wake or keep warm the ML inference service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(f"{settings.ML_SERVICE_URL}/api/v1/health")
    except Exception:
        pass


@router.get("/health")
@limiter.exempt
def health(background_tasks: BackgroundTasks) -> dict:
    if settings.ML_SERVICE_URL:
        background_tasks.add_task(_wake_ml_service)
    if os.environ.get("SCAMGUARD_DB_FALLBACK") == "1":
        # Running on the temporary SQLite fallback (see start_app_service.sh).
        return {"status": "ok", "database": "temporary-fallback"}
    return {"status": "ok"}


@router.get("/ready")
@limiter.exempt
def ready() -> dict:
    return {"status": "ready"}
