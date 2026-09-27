from fastapi import APIRouter

from app_service.api.v1 import analytics, auth, cases, demo, health, messages, model_evaluation, robustness, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(messages.router)
api_router.include_router(analytics.router)
api_router.include_router(cases.router)
api_router.include_router(demo.router)
api_router.include_router(model_evaluation.router)
api_router.include_router(robustness.router)
