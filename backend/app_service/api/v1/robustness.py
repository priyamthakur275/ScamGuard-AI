from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app_service.api.deps import require_admin
from app_service.db.postgres.models import User
from app_service.db.session import get_db
from app_service.services.robustness_service import run_robustness_suite

router = APIRouter(prefix="/admin/robustness-test", tags=["admin"])


@router.post("")
def run_robustness_test(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> list[dict]:
    reports = run_robustness_suite(db)
    return [r.to_dict() for r in reports]
