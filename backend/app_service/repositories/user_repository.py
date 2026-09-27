from sqlalchemy import select
from sqlalchemy.orm import Session

from app_service.db.postgres.models import User
from app_service.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalars(stmt).first()

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None
