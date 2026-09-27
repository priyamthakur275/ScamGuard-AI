import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app_service.api.deps import get_current_user
from app_service.core.rate_limit import limiter
from app_service.db.postgres.models import User
from app_service.db.session import get_db
from app_service.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseNoteCreate,
    CaseScanLinkCreate,
    CaseSummary,
    CaseTimelineEntryRead,
    CaseUpdate,
)
from app_service.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseSummary, status_code=201)
@limiter.limit("30/minute")
def create_case(
    request: Request, payload: CaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CaseSummary:
    return CaseService(db).create(current_user.id, payload)


@router.get("", response_model=list[CaseSummary])
def list_cases(
    request: Request,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CaseSummary]:
    return CaseService(db).list_cases(current_user.id, status)


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    request: Request, case_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CaseDetail:
    return CaseService(db).get_detail(case_id, current_user.id)


@router.patch("/{case_id}", response_model=CaseSummary)
def update_case(
    request: Request,
    case_id: uuid.UUID,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseSummary:
    return CaseService(db).update(case_id, current_user.id, payload)


@router.post("/{case_id}/scans", response_model=CaseSummary)
def link_scan(
    request: Request,
    case_id: uuid.UUID,
    payload: CaseScanLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseSummary:
    return CaseService(db).link_scan(case_id, current_user.id, payload.prediction_id)


@router.delete("/{case_id}/scans/{prediction_id}", response_model=CaseSummary)
def unlink_scan(
    request: Request,
    case_id: uuid.UUID,
    prediction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseSummary:
    return CaseService(db).unlink_scan(case_id, current_user.id, prediction_id)


@router.post("/{case_id}/notes", response_model=CaseTimelineEntryRead, status_code=201)
def add_note(
    request: Request,
    case_id: uuid.UUID,
    payload: CaseNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseTimelineEntryRead:
    return CaseService(db).add_note(case_id, current_user.id, payload)


@router.get("/{case_id}/report")
@limiter.limit("20/minute")
def export_case_report(
    request: Request,
    case_id: uuid.UUID,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import Response
    from app_service.core.exceptions import ValidationAppError
    from app_service.services.report_builder import (
        build_case_report_data, build_scan_report_data, to_json_bytes, to_csv_bytes, to_pdf_bytes,
    )

    detail = CaseService(db).get_detail(case_id, current_user.id)
    scan_reports = [build_scan_report_data(s) for s in detail.scans]
    report_data = {
        "case_id": str(detail.id),
        "case_title": detail.title,
        "case_status": detail.status,
        "scan_count": len(scan_reports),
        "scans": scan_reports,
    }

    if format == "json":
        return Response(
            content=to_json_bytes(report_data), media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="scamguard-case-{case_id}.json"'},
        )
    if format == "csv":
        return Response(
            content=to_csv_bytes(scan_reports), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="scamguard-case-{case_id}.csv"'},
        )
    if format == "pdf":
        pdf_bytes = to_pdf_bytes(scan_reports, f"ScamGuard Case Report - {detail.title}")
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="scamguard-case-{case_id}.pdf"'},
        )
    raise ValidationAppError(f"Unsupported report format '{format}'. Must be one of: json, csv, pdf.")
