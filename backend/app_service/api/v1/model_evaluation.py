from fastapi import APIRouter, Depends

from app_service.api.deps import require_admin
from app_service.db.postgres.models import User
from app_service.schemas.model_evaluation import ModelEvaluationEntry
from app_service.services.model_evaluation_service import get_model_evaluations

router = APIRouter(prefix="/admin/model-evaluation", tags=["admin"])


@router.get("", response_model=list[ModelEvaluationEntry])
def list_model_evaluations(_admin: User = Depends(require_admin)) -> list[ModelEvaluationEntry]:
    return get_model_evaluations()
