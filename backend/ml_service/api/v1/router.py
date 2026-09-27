from fastapi import APIRouter

from ml_service.api.v1 import health, predict

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(predict.router)
