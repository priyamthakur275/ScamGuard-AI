from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app_service.db.postgres.models import RefreshToken
from app_service.repositories.base import BaseRepository


class TokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: Session):
        super().__init__(db, RefreshToken)

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.scalars(stmt).first()

    def revoke(self, token: RefreshToken) -> None:
        token.revoked = True
        self.save(token)

    def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
        )
        tokens = self.db.scalars(stmt).all()
        for token in tokens:
            token.revoked = True
        self.db.commit()

    @staticmethod
    def is_valid(token: RefreshToken) -> bool:
        if token.revoked:
            return False
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)
