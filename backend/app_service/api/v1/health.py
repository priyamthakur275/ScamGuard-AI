import asyncio
from fastapi import APIRouter, BackgroundTasks
import httpx

from app_service.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["system"])


async def _wake_ml_service():
    """Fire-and-forget background ping to wake or keep warm the ML inference service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(f"{settings.ML_SERVICE_URL}/api/v1/health")
    except Exception:
        pass


@router.get("/health")
def health(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_wake_ml_service)
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    return {"status": "ready"}
