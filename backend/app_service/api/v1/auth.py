from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app_service.core.captcha import generate_challenge
from app_service.core.config import get_settings
from app_service.core.rate_limit import limiter
from app_service.db.session import get_db
from app_service.schemas.auth import CaptchaChallengeResponse, LoginRequest, LogoutRequest, RefreshRequest, TokenPair
from app_service.schemas.user import UserCreate, UserRead
from app_service.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.get("/captcha", response_model=CaptchaChallengeResponse)
@limiter.limit("30/minute")
def get_captcha(request: Request) -> CaptchaChallengeResponse:
    challenge = generate_challenge(settings.SECRET_KEY)
    return CaptchaChallengeResponse(question=challenge.question, token=challenge.token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    service = AuthService(db)
    user = service.register(payload.email, payload.password, payload.captcha_token, payload.captcha_answer)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    service = AuthService(db)
    return service.login(payload.email, payload.password, payload.captcha_token, payload.captcha_answer)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit("20/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    service = AuthService(db)
    return service.refresh_access_token(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def logout(request: Request, payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    service = AuthService(db)
    service.logout(payload.refresh_token)
