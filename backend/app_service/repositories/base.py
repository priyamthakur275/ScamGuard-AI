from typing import Generic, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app_service.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Thin data-access wrapper around a single SQLAlchemy model.

    Keeps raw SQLAlchemy usage out of the service layer so services can be
    unit tested against a repository interface if needed.
    """

    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def get(self, id_: UUID) -> ModelType | None:
        return self.db.get(self.model, id_)

    def list(self, skip: int = 0, limit: int = 50) -> list[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def save(self, obj: ModelType) -> ModelType:
        """Persist changes made to an already-tracked or new instance."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()
