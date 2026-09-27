from uuid import UUID

from sqlalchemy.orm import Session

from app_service.db.postgres.models import AuditLog
from app_service.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(db, AuditLog)

    def record(self, actor_id: UUID | None, action: str, metadata: dict | None = None) -> AuditLog:
        entry = AuditLog(actor_id=actor_id, action=action, log_metadata=metadata or {})
        return self.create(entry)
