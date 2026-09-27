from uuid import UUID

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, status, Query
from sqlalchemy.orm import Session

from app_service.api.deps import get_current_user
from app_service.core.rate_limit import limiter
from app_service.db.postgres.models import User
from app_service.db.session import get_db
from app_service.schemas.message import AnalysisResult, AnalyzeRequest, FeedbackRequest
from app_service.schemas.copilot import CopilotQuestionRequest, CopilotAnswerResponse
from app_service.services.message_service import MessageService
from app_service.services.extraction import ExtractionService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/analyze", response_model=AnalysisResult)
@limiter.limit("30/minute")
def analyze_message(
    request: Request,
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisResult:
    service = MessageService(db)
    return service.analyze(current_user.id, payload.text, payload.input_type)

@router.post("/scan", response_model=AnalysisResult)
@limiter.limit("30/minute")
def scan_message(
    request: Request,
    file: UploadFile = File(None),
    text: str = Form(None),
    input_type: str = Form("TEXT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisResult:
    try:
        extracted_text, metadata = ExtractionService.extract(file, text, input_type)
    except ValueError as e:
        from app_service.core.exceptions import ValidationAppError
        raise ValidationAppError(str(e)) from e

    if not extracted_text or not extracted_text.strip():
        from app_service.core.exceptions import ValidationAppError
        raise ValidationAppError("No text could be extracted from the provided input.")

    service = MessageService(db)
    return service.analyze(current_user.id, extracted_text, input_type, metadata)


@router.get("/history", response_model=list[AnalysisResult])
@limiter.limit("60/minute")
def get_history(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnalysisResult]:
    service = MessageService(db)
    return service.list_history(current_user.id, skip=skip, limit=limit)


@router.patch("/{prediction_id}/feedback", response_model=AnalysisResult)
@limiter.limit("30/minute")
def submit_feedback(
    request: Request,
    prediction_id: UUID,
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisResult:
    service = MessageService(db)
    return service.record_feedback(current_user.id, prediction_id, payload.is_accurate)

@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def clear_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = MessageService(db)
    service.clear_history(current_user.id)

@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_prediction(
    request: Request,
    prediction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = MessageService(db)
    service.delete_prediction(current_user.id, prediction_id)


@router.post("/{prediction_id}/copilot")
@limiter.limit("30/minute")
def ask_copilot(
    request: Request,
    prediction_id: UUID,
    payload: CopilotQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopilotAnswerResponse:
    from app_service.services.copilot_service import get_answer

    service = MessageService(db)
    scan = service.get_result_for_user(current_user.id, prediction_id)
    result = get_answer(payload.question, scan)
    return CopilotAnswerResponse(
        answer=result.answer, grounded_in=list(result.grounded_in), source=result.source, intent=result.intent
    )


@router.get("/{prediction_id}/report")
@limiter.limit("20/minute")
def export_scan_report(
    request: Request,
    prediction_id: UUID,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import Response
    from app_service.core.exceptions import ValidationAppError
    from app_service.services.report_builder import (
        build_scan_report_data, to_json_bytes, to_csv_bytes, to_pdf_bytes,
    )

    service = MessageService(db)
    scan = service.get_result_for_user(current_user.id, prediction_id)
    report_data = build_scan_report_data(scan)

    if format == "json":
        return Response(
            content=to_json_bytes(report_data), media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="scamguard-scan-{prediction_id}.json"'},
        )
    if format == "csv":
        return Response(
            content=to_csv_bytes([report_data]), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="scamguard-scan-{prediction_id}.csv"'},
        )
    if format == "pdf":
        pdf_bytes = to_pdf_bytes([report_data], f"ScamGuard Report - Scan {prediction_id}")
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="scamguard-scan-{prediction_id}.pdf"'},
        )
    raise ValidationAppError(f"Unsupported report format '{format}'. Must be one of: json, csv, pdf.")

