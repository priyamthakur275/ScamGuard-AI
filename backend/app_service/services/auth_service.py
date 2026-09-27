from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app_service.core.config import get_settings
from app_service.core.exceptions import CaptchaRequiredError, ConflictError, InvalidCaptchaError, UnauthorizedError
from app_service.core.captcha import verify_answer
from app_service.core import login_attempts
from app_service.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_token,
    verify_password,
)
from app_service.db.postgres.models import RefreshToken, User, UserRole
from app_service.repositories.audit_repository import AuditRepository
from app_service.repositories.token_repository import TokenRepository
from app_service.repositories.user_repository import UserRepository
from app_service.schemas.auth import TokenPair

settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        self.audit = AuditRepository(db)

    def register(self, email: str, password: str, captcha_token: str, captcha_answer: str) -> User:
        if not verify_answer(captcha_token, captcha_answer, settings.SECRET_KEY):
            raise InvalidCaptchaError("CAPTCHA verification failed. Please try again.")

        normalized_email = email.lower()
        if self.users.email_exists(normalized_email):
            raise ConflictError("An account with this email already exists")

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role=UserRole.USER,
        )
        user = self.users.create(user)
        self.audit.record(actor_id=user.id, action="user_registered")
        return user

    def authenticate(
        self, email: str, password: str, captcha_token: str | None = None, captcha_answer: str | None = None
    ) -> User:
        normalized_email = email.lower()

        # Step-up CAPTCHA: only required after several recent failures for
        # this specific email, not on every ordinary login -- see
        # login_attempts.py for the (documented, in-process) tracking.
        if login_attempts.captcha_required(normalized_email):
            if not captcha_token or not captcha_answer:
                raise CaptchaRequiredError(
                    "Too many failed login attempts. Please complete the CAPTCHA challenge to continue."
                )
            if not verify_answer(captcha_token, captcha_answer, settings.SECRET_KEY):
                raise InvalidCaptchaError("CAPTCHA verification failed. Please try again.")

        user = self.users.get_by_email(normalized_email)
        if user is None or not verify_password(password, user.password_hash):
            login_attempts.record_failure(normalized_email)
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated")

        login_attempts.record_success(normalized_email)
        return user

    def issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(subject=str(user.id), role=user.role.value)
        raw_refresh_token = create_refresh_token_value()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=expires_at,
        )
        self.tokens.create(token_record)
        self.audit.record(actor_id=user.id, action="token_issued")

        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)

    def login(
        self, email: str, password: str, captcha_token: str | None = None, captcha_answer: str | None = None
    ) -> TokenPair:
        user = self.authenticate(email, password, captcha_token, captcha_answer)
        return self.issue_token_pair(user)

    def refresh_access_token(self, raw_refresh_token: str) -> TokenPair:
        """Validate + rotate a refresh token, returning a brand new pair.

        Rotation means the presented refresh token is revoked as soon as
        it is used, whether or not the caller successfully retrieves the
        new pair. This prevents a stolen refresh token from being replayed
        indefinitely.
        """
        token_hash = hash_token(raw_refresh_token)
        stored_token = self.tokens.get_by_hash(token_hash)

        if stored_token is None or not self.tokens.is_valid(stored_token):
            raise UnauthorizedError("Invalid or expired refresh token")

        user = self.users.get(stored_token.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid or expired refresh token")

        self.tokens.revoke(stored_token)
        return self.issue_token_pair(user)

    def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_token(raw_refresh_token)
        stored_token = self.tokens.get_by_hash(token_hash)
        if stored_token is not None:
            self.tokens.revoke(stored_token)
