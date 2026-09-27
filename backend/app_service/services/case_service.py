import uuid

from sqlalchemy.orm import Session

from app_service.core.exceptions import NotFoundError, ValidationAppError
from app_service.db.postgres.models import (
    Case,
    CaseSeverity,
    CaseStatus,
    CaseTimelineEntry,
    CaseTimelineEntryType,
)
from app_service.repositories.case_repository import (
    CaseRepository,
    CaseScanLinkRepository,
    CaseTimelineRepository,
)
from app_service.repositories.message_repository import PredictionRepository
from app_service.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseNoteCreate,
    CaseSummary,
    CaseTimelineEntryRead,
    CaseUpdate,
)

_VALID_SEVERITIES = {s.value for s in CaseSeverity}
_VALID_STATUSES = {s.value for s in CaseStatus}


class CaseService:
    def __init__(self, db: Session):
        self.db = db
        self.cases = CaseRepository(db)
        self.scan_links = CaseScanLinkRepository(db)
        self.timeline = CaseTimelineRepository(db)
        self.predictions = PredictionRepository(db)

    def _add_timeline_entry(self, case_id: uuid.UUID, author_id: uuid.UUID, entry_type: CaseTimelineEntryType, content: str) -> None:
        entry = CaseTimelineEntry(case_id=case_id, author_id=author_id, entry_type=entry_type, content=content)
        self.db.add(entry)
        self.db.commit()

    def create(self, user_id: uuid.UUID, payload: CaseCreate) -> CaseSummary:
        if payload.severity not in _VALID_SEVERITIES:
            raise ValidationAppError(f"Invalid severity '{payload.severity}'. Must be one of: {', '.join(sorted(_VALID_SEVERITIES))}.")

        case = Case(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            status=CaseStatus.OPEN,
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)

        self._add_timeline_entry(case.id, user_id, CaseTimelineEntryType.CREATED, f"Case created: \"{case.title}\"")

        linked_count = 0
        for prediction_id in payload.scan_ids:
            # Reuses the SAME user-isolation check already enforced for
            # ordinary scan access -- a scan can only be linked to a case
            # by the user who owns that scan.
            prediction = self.predictions.get_for_user(prediction_id, user_id)
            if prediction is None:
                continue  # silently skip scans that don't belong to this user, rather than error the whole case creation
            self._link_scan_no_commit_guard(case.id, user_id, prediction_id)
            linked_count += 1

        return self._to_summary(case, linked_count)

    def _link_scan_no_commit_guard(self, case_id: uuid.UUID, user_id: uuid.UUID, prediction_id: uuid.UUID) -> None:
        if self.scan_links.exists(case_id, prediction_id):
            return
        from app_service.db.postgres.models import CaseScanLink
        link = CaseScanLink(case_id=case_id, prediction_id=prediction_id)
        self.db.add(link)
        self.db.commit()
        self._add_timeline_entry(case_id, user_id, CaseTimelineEntryType.SCAN_LINKED, f"Scan {prediction_id} linked to case")

    def list_cases(self, user_id: uuid.UUID, status: str | None = None) -> list[CaseSummary]:
        if status is not None and status not in _VALID_STATUSES:
            raise ValidationAppError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}.")
        cases = self.cases.list_for_user(user_id, status)
        return [self._to_summary(c, len(c.scan_links)) for c in cases]

    def get_detail(self, case_id: uuid.UUID, user_id: uuid.UUID) -> CaseDetail:
        case = self.cases.get_for_user(case_id, user_id)
        if case is None:
            raise NotFoundError("Case not found.")

        predictions = self.scan_links.list_predictions_for_case(case_id)
        from app_service.services.message_service import MessageService
        scans = [MessageService._to_result(p, p.message.text) for p in predictions]

        aggregated_entities: dict[str, list[str]] = {}
        for scan in scans:
            if not scan.highlighted_entities:
                continue
            for key, values in scan.highlighted_entities.items():
                if not values:
                    continue
                existing = aggregated_entities.setdefault(key, [])
                for v in values:
                    if v not in existing:
                        existing.append(v)

        timeline_entries = self.timeline.list_for_case(case_id)
        timeline = [CaseTimelineEntryRead.model_validate(e) for e in timeline_entries]

        return CaseDetail(
            id=case.id,
            title=case.title,
            description=case.description,
            severity=case.severity.value if hasattr(case.severity, "value") else case.severity,
            status=case.status.value if hasattr(case.status, "value") else case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
            scans=scans,
            aggregated_entities=aggregated_entities,
            timeline=timeline,
        )

    def update(self, case_id: uuid.UUID, user_id: uuid.UUID, payload: CaseUpdate) -> CaseSummary:
        case = self.cases.get_for_user(case_id, user_id)
        if case is None:
            raise NotFoundError("Case not found.")

        if payload.severity is not None:
            if payload.severity not in _VALID_SEVERITIES:
                raise ValidationAppError(f"Invalid severity '{payload.severity}'.")
            case.severity = payload.severity
        if payload.title is not None:
            case.title = payload.title
        if payload.description is not None:
            case.description = payload.description
        if payload.status is not None:
            if payload.status not in _VALID_STATUSES:
                raise ValidationAppError(f"Invalid status '{payload.status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}.")
            old_status = case.status.value if hasattr(case.status, "value") else case.status
            if old_status != payload.status:
                case.status = payload.status
                self.db.add(case)
                self.db.commit()
                self._add_timeline_entry(
                    case.id, user_id, CaseTimelineEntryType.STATUS_CHANGED,
                    f"Status changed from {old_status} to {payload.status}",
                )

        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return self._to_summary(case, len(case.scan_links))

    def link_scan(self, case_id: uuid.UUID, user_id: uuid.UUID, prediction_id: uuid.UUID) -> CaseSummary:
        case = self.cases.get_for_user(case_id, user_id)
        if case is None:
            raise NotFoundError("Case not found.")
        prediction = self.predictions.get_for_user(prediction_id, user_id)
        if prediction is None:
            raise NotFoundError("Scan not found.")
        self._link_scan_no_commit_guard(case_id, user_id, prediction_id)
        self.db.refresh(case)
        return self._to_summary(case, len(case.scan_links))

    def unlink_scan(self, case_id: uuid.UUID, user_id: uuid.UUID, prediction_id: uuid.UUID) -> CaseSummary:
        case = self.cases.get_for_user(case_id, user_id)
        if case is None:
            raise NotFoundError("Case not found.")
        link = self.scan_links.get(case_id, prediction_id)
        if link is None:
            raise NotFoundError("This scan is not linked to this case.")
        self.scan_links.delete(link)
        self._add_timeline_entry(case_id, user_id, CaseTimelineEntryType.SCAN_UNLINKED, f"Scan {prediction_id} unlinked from case")
        self.db.refresh(case)
        return self._to_summary(case, len(case.scan_links))

    def add_note(self, case_id: uuid.UUID, user_id: uuid.UUID, payload: CaseNoteCreate) -> CaseTimelineEntryRead:
        case = self.cases.get_for_user(case_id, user_id)
        if case is None:
            raise NotFoundError("Case not found.")
        entry = CaseTimelineEntry(
            case_id=case_id, author_id=user_id, entry_type=CaseTimelineEntryType.NOTE, content=payload.content
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return CaseTimelineEntryRead.model_validate(entry)

    @staticmethod
    def _to_summary(case: Case, scan_count: int) -> CaseSummary:
        return CaseSummary(
            id=case.id,
            title=case.title,
            description=case.description,
            severity=case.severity.value if hasattr(case.severity, "value") else case.severity,
            status=case.status.value if hasattr(case.status, "value") else case.status,
            scan_count=scan_count,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
