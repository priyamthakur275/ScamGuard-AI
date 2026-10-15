"""Public safety tools: QR payment check, pay-safe check, attachment check and
the "what makes it a scam" counterfactual. Rate limited; nothing is stored."""

import io

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app_service.core.rate_limit import limiter
from app_service.db.session import get_db
from app_service.services import safety_tools as st

router = APIRouter(prefix="/tools", tags=["tools"])


async def _read(file: UploadFile, limit: int) -> bytes:
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"File too large (max {limit // (1024 * 1024)} MB).")
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")
    return data


@router.post("/qr")
@limiter.limit("15/minute")
async def qr_check(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    data = await _read(file, 8 * 1024 * 1024)
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode

        found = decode(Image.open(io.BytesIO(data)))
    except Exception:
        raise HTTPException(status_code=400, detail="That image could not be read. Upload a clear photo or screenshot of the QR code.")
    if not found:
        raise HTTPException(status_code=422, detail="No QR code found. Crop the image closer to the code and try again.")
    content = found[0].data.decode("utf-8", errors="ignore").strip()
    upi = st.parse_upi_uri(content)
    if upi:
        result = st.analyze_upi(upi["vpa"], upi["payee_name"], upi["amount"], upi["note"], source="qr").to_dict()
        if upi["mode"] == "mandate":
            result["flags"].insert(0, {"level": "warning", "title": "This is an AutoPay mandate",
                                       "detail": "It sets up repeated payments from your account, not a one-time payment."})
        return {"kind": "upi", "content": content, **result}
    from app_service.services.message_service import MessageService

    analysis = MessageService(db).analyze_ephemeral(content[:2000], "TEXT", {"source": "qr"}) if len(content) >= 3 else None
    return {"kind": "url" if content.lower().startswith(("http://", "https://", "www.")) else "text", "content": content,
            "analysis": analysis.model_dump(mode="json") if analysis else None}


class PayCheckRequest(BaseModel):
    upi_id: str = Field(default="", max_length=256)
    payee_name: str = Field(default="", max_length=120)
    expected_name: str = Field(default="", max_length=120)
    amount: str = Field(default="", max_length=20)
    reason: str = Field(default="other", max_length=30)


@router.post("/pay-check")
@limiter.limit("30/minute")
def pay_check(request: Request, payload: PayCheckRequest) -> dict:
    if not (payload.upi_id or payload.payee_name or payload.reason):
        raise HTTPException(status_code=422, detail="Enter the UPI ID or choose why you are paying.")
    return st.analyze_upi(payload.upi_id, payload.payee_name, payload.amount, "", payload.reason, payload.expected_name).to_dict()


@router.get("/pay-reasons")
def pay_reasons() -> list[dict]:
    return [{"id": k, "label": v[1]} for k, v in st.REASONS.items()]


@router.post("/file")
@limiter.limit("15/minute")
async def file_check(request: Request, file: UploadFile = File(...)) -> dict:
    data = await _read(file, st.MAX_FILE_BYTES)
    return st.check_file(file.filename or "file", data).to_dict()


class WhatIfRequest(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


@router.post("/what-if")
@limiter.limit("15/minute")
def what_if(request: Request, payload: WhatIfRequest) -> dict:
    return st.what_if(payload.text)
