from uuid import UUID

from sqlalchemy.orm import Session

from app_service.core.exceptions import NotFoundError
from app_service.db.postgres.models import User, UserRole
from app_service.repositories.audit_repository import AuditRepository
from app_service.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    def get_user(self, user_id: UUID) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def list_users(self, skip: int = 0, limit: int = 50) -> list[User]:
        return self.users.list(skip=skip, limit=limit)

    def update_role(self, actor_id: UUID, target_user_id: UUID, new_role: UserRole) -> User:
        user = self.get_user(target_user_id)
        old_role = user.role
        user.role = new_role
        user = self.users.save(user)
        self.audit.record(
            actor_id=actor_id,
            action="user_role_changed",
            metadata={
                "target_user_id": str(target_user_id),
                "old_role": old_role.value,
                "new_role": new_role.value,
            },
        )
        return user

    def deactivate_user(self, actor_id: UUID, target_user_id: UUID) -> User:
        user = self.get_user(target_user_id)
        user.is_active = False
        user = self.users.save(user)
        self.audit.record(
            actor_id=actor_id,
            action="user_deactivated",
            metadata={"target_user_id": str(target_user_id)},
        )
        return user
