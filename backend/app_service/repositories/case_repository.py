import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app_service.db.postgres.models import Case, CaseScanLink, CaseTimelineEntry, Prediction, Message
from app_service.repositories.base import BaseRepository


class CaseRepository(BaseRepository[Case]):
    def __init__(self, db: Session):
        super().__init__(db, Case)

    def list_for_user(self, user_id: uuid.UUID, status: str | None = None) -> list[Case]:
        stmt = select(Case).where(Case.user_id == user_id).order_by(Case.updated_at.desc())
        if status:
            stmt = stmt.where(Case.status == status)
        return list(self.db.scalars(stmt).all())

    def get_for_user(self, case_id: uuid.UUID, user_id: uuid.UUID) -> Case | None:
        stmt = select(Case).where(Case.id == case_id, Case.user_id == user_id)
        return self.db.scalars(stmt).first()


class CaseScanLinkRepository(BaseRepository[CaseScanLink]):
    def __init__(self, db: Session):
        super().__init__(db, CaseScanLink)

    def exists(self, case_id: uuid.UUID, prediction_id: uuid.UUID) -> bool:
        stmt = select(CaseScanLink).where(
            CaseScanLink.case_id == case_id, CaseScanLink.prediction_id == prediction_id
        )
        return self.db.scalars(stmt).first() is not None

    def get(self, case_id: uuid.UUID, prediction_id: uuid.UUID) -> CaseScanLink | None:
        stmt = select(CaseScanLink).where(
            CaseScanLink.case_id == case_id, CaseScanLink.prediction_id == prediction_id
        )
        return self.db.scalars(stmt).first()

    def list_predictions_for_case(self, case_id: uuid.UUID) -> list[Prediction]:
        stmt = (
            select(Prediction)
            .join(CaseScanLink, CaseScanLink.prediction_id == Prediction.id)
            .where(CaseScanLink.case_id == case_id)
            .order_by(Prediction.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())


class CaseTimelineRepository(BaseRepository[CaseTimelineEntry]):
    def __init__(self, db: Session):
        super().__init__(db, CaseTimelineEntry)

    def list_for_case(self, case_id: uuid.UUID) -> list[CaseTimelineEntry]:
        stmt = (
            select(CaseTimelineEntry)
            .where(CaseTimelineEntry.case_id == case_id)
            .order_by(CaseTimelineEntry.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
