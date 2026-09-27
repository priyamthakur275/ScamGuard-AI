from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app_service.core.exceptions import ForbiddenError, UnauthorizedError
from app_service.core.security import TokenError, decode_access_token
from app_service.db.postgres.models import User, UserRole
from app_service.db.session import get_db
from app_service.repositories.user_repository import UserRepository


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token payload")

    try:
        user = UserRepository(db).get(UUID(user_id))
    except ValueError as exc:
        raise UnauthorizedError("Invalid token payload") from exc

    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def get_optional_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id:
            user = UserRepository(db).get(UUID(user_id))
            if user and user.is_active:
                return user
    except Exception:
        pass
    return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Administrator privileges are required for this action")
    return current_user


def require_roles(*allowed_roles: UserRole):
    """Factory for a dependency that only allows the given roles through."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("You do not have permission to perform this action")
        return current_user

    return dependency
