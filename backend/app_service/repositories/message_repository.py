import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from app_service.db.postgres.models import Message, Prediction
from app_service.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(db, Message)

    def create(self, user_id: uuid.UUID | None, text: str) -> Message:
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        message = Message(user_id=user_id, text=text, content_hash=content_hash)
        return super().create(message)


class PredictionRepository(BaseRepository[Prediction]):
    def __init__(self, db: Session):
        super().__init__(db, Prediction)

    def list_for_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50) -> list[Prediction]:
        stmt = (
            select(Prediction)
            .join(Message)
            # Load each prediction's message in the same query: without this,
            # reading prediction.message issued one extra query per row
            # (51 round trips for a 50-item history page).
            .options(contains_eager(Prediction.message))
            .where(Message.user_id == user_id)
            .order_by(Prediction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_for_user(self, prediction_id: uuid.UUID, user_id: uuid.UUID) -> Prediction | None:
        stmt = (
            select(Prediction)
            .join(Message)
            .options(contains_eager(Prediction.message))
            .where(Prediction.id == prediction_id, Message.user_id == user_id)
        )
        return self.db.scalars(stmt).first()
