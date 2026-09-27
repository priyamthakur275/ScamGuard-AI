from uuid import UUID
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, Request, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from fastapi_cache.decorator import cache
except ImportError:
    def cache(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from app_service.api.deps import get_current_user, require_admin
from app_service.core.rate_limit import limiter
from app_service.db.postgres.models import User, Prediction, Message, RiskLevel
from app_service.db.session import get_db
from app_service.schemas.user import UserRead, UserUpdateRole, UserUpdate
from app_service.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
@limiter.limit("60/minute")
def read_current_user(request: Request, current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
@limiter.limit("30/minute")
def update_current_user(
    request: Request,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserRead:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.preferences is not None:
        current_user.preferences = payload.preferences
    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)

from app_service.schemas.user import UserUpdatePassword
from app_service.core.security import verify_password, hash_password
from app_service.core.exceptions import UnauthorizedError

@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def update_password(
    request: Request,
    payload: UserUpdatePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise UnauthorizedError("Incorrect current password")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def delete_current_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UserService(db)
    service.users.delete(current_user)

@router.get("/me/export")
@limiter.limit("10/minute")
def export_current_user_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime, timezone
    from app_service.services.message_service import MessageService
    msg_service = MessageService(db)
    history = msg_service.list_history(current_user.id, skip=0, limit=1000)
    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "preferences": current_user.preferences,
        },
        "history": [
            {
                "id": str(h.id),
                "text": h.text,
                "input_type": h.input_type,
                "verdict": h.verdict,
                "scam_probability": h.scam_probability,
                "risk_level": h.risk_level,
                "scam_category": h.scam_category,
                "confidence_score": h.confidence_score,
                "threat_score": h.threat_score,
                "ai_explanation": h.ai_explanation,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }



@router.post("/me/avatar")
@limiter.limit("10/minute")
def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    upload_dir = Path("uploads/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "png"
    file_path = upload_dir / f"{current_user.id}.{file_extension}"
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    avatar_url = f"/uploads/avatars/{current_user.id}.{file_extension}"
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)
    return {"avatar_url": avatar_url}


@router.get("/admin/stats")
@limiter.limit("30/minute")
@cache(expire=60)
def get_admin_stats(
    request: Request,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin)
):
    users_count = db.query(func.count(User.id)).scalar()
    scans_count = db.query(func.count(Prediction.id)).scalar()
    
    high_risk_count = db.query(func.count(Prediction.id)).filter(
        Prediction.risk_level == RiskLevel.HIGH
    ).scalar()
    
    medium_risk_count = db.query(func.count(Prediction.id)).filter(
        Prediction.risk_level == RiskLevel.MEDIUM
    ).scalar()
    
    low_risk_count = db.query(func.count(Prediction.id)).filter(
        Prediction.risk_level == RiskLevel.LOW
    ).scalar()

    return {
        "users_count": users_count or 0,
        "scans_count": scans_count or 0,
        "threat_counts": {
            "high": high_risk_count or 0,
            "medium": medium_risk_count or 0,
            "low": low_risk_count or 0
        }
    }


@router.get("", response_model=list[UserRead])
@limiter.limit("60/minute")
def list_users(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[UserRead]:
    service = UserService(db)
    users = service.list_users(skip=skip, limit=limit)
    return [UserRead.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserRead)
@limiter.limit("60/minute")
def get_user(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserRead:
    service = UserService(db)
    user = service.get_user(user_id)
    return UserRead.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserRead)
@limiter.limit("30/minute")
def update_user_role(
    request: Request,
    user_id: UUID,
    payload: UserUpdateRole,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    service = UserService(db)
    user = service.update_role(actor_id=admin.id, target_user_id=user_id, new_role=payload.role)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def deactivate_user(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    service = UserService(db)
    service.deactivate_user(actor_id=admin.id, target_user_id=user_id)
