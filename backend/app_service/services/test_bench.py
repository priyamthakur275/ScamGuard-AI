"""Public test bench: 15 fixed inputs (7 scams, 8 genuine) across every channel.

Every result is produced live by the same extraction + model + intent engine
that serves real scans (MessageService.analyze_ephemeral), so the page shows
what the deployed system does today, not a stored claim. Results are cached
for a few minutes to keep the free server responsive.
"""
from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app_service.services.extraction import ExtractionService
from app_service.services.message_service import MessageService

logger = logging.getLogger("app_service.test_bench")

FIXTURES = Path(__file__).resolve().parent.parent / "test_bench"

EMAIL_SCAM = """From: HDFC Bank Alerts <alerts@hdfcbank-secure-verify.com>
Reply-To: support.hdfc.kyc@gmail.com
Subject: URGENT: Your NetBanking access will be suspended today
Authentication-Results: spf=fail dkim=fail

Dear Customer, your HDFC NetBanking account will be suspended within 24 hours due to incomplete KYC. Click http://hdfc-netbanking-kyc.top/verify and enter your customer ID, password and the OTP to keep your account active."""

EMAIL_LEGIT = """From: Swiggy <noreply@swiggy.in>
Subject: Your Swiggy order receipt #458213906
Authentication-Results: spf=pass dkim=pass

Hi Priyam, thanks for ordering with Swiggy. Your order from Meghana Foods has been delivered. Order total: Rs 412.00, paid using UPI. You can view your order details anytime in the Swiggy app. For help, visit the Help section in the app."""


@dataclass(frozen=True)
class BenchCase:
    id: int
    input_type: str  # TEXT, URL, EMAIL, IMAGE, PDF, QR, VOICE
    expected: str  # "scam" | "legitimate"
    title: str
    text: str | None = None
    file: str | None = None


CASES: tuple[BenchCase, ...] = (
    BenchCase(1, "TEXT", "scam", "SBI KYC / OTP SMS", text="Dear SBI customer, your YONO account will be blocked today due to pending KYC. Share the OTP sent to your mobile and update PAN at http://sbi-yono-kyc.xyz or call 9812345670."),
    BenchCase(2, "URL", "scam", "Look-alike PayPal login link", text="http://paypa1-secure-login.verify-account.top/signin"),
    BenchCase(3, "EMAIL", "scam", "Fake HDFC suspension email (SPF/DKIM fail)", text=EMAIL_SCAM),
    BenchCase(4, "IMAGE", "scam", "WhatsApp task-job scam asking a fee", file="chat_scam.png"),
    BenchCase(5, "PDF", "scam", "Fake Amazon offer letter with a deposit", file="offer_scam.pdf"),
    BenchCase(6, "QR", "scam", "QR code to a fake 'SBI reward points' site", file="qr_scam.png"),
    BenchCase(7, "VOICE", "scam", "'Digital arrest' call transcript (Hinglish)", text="Hello, main Mumbai Cyber Crime se Inspector Sharma bol raha hoon. Aapke Aadhaar se ek parcel mein drugs mile hain. Aap digital arrest mein hain, video call disconnect mat karna aur kisi ko mat batana. Case close karne ke liye abhi 50,000 rupaye RBI safe account mein transfer kariye."),
    BenchCase(8, "TEXT", "legitimate", "Genuine bank debit alert", text="Rs. 2,450.00 debited from A/c XX4821 on 12-10-26 to AMAZON PAY. Avl bal Rs. 18,302.55. Not you? Call 1800-1234 (official helpline). Never share your OTP with anyone."),
    BenchCase(9, "TEXT", "legitimate", "Genuine OTP message (Hinglish warning)", text="123456 is your OTP for login to the IRCTC app. Valid for 10 minutes. OTP kisi ke saath share na karein. - IRCTC"),
    BenchCase(10, "TEXT", "legitimate", "Delivery update", text="Your Amazon order #405-1182 with 'boAt Airdopes 141' has been delivered. Thank you for shopping with us."),
    BenchCase(11, "URL", "legitimate", "Official IRCTC website", text="https://www.irctc.co.in/nget/train-search"),
    BenchCase(12, "EMAIL", "legitimate", "Swiggy order receipt (SPF/DKIM pass)", text=EMAIL_LEGIT),
    BenchCase(13, "IMAGE", "legitimate", "Family WhatsApp chat", file="chat_legit.png"),
    BenchCase(14, "PDF", "legitimate", "College circular", file="circular_legit.pdf"),
    BenchCase(15, "VOICE", "legitimate", "Normal family call transcript", text="Hi beta, main office se nikal gaya hoon, around seven baje tak ghar pahunch jaunga. Dinner pe wait karna, aur kal subah tumhari college fees online bhar denge."),
)


class _FixtureUpload:
    """Minimal stand-in for an UploadFile backed by a fixture on disk."""

    def __init__(self, name: str):
        self.filename = name
        self.content_type = "application/pdf" if name.endswith(".pdf") else "image/png"
        self.file = io.BytesIO((FIXTURES / name).read_bytes())


def extract_case(case: BenchCase) -> tuple[str, dict]:
    upload = _FixtureUpload(case.file) if case.file else None
    return ExtractionService.extract(upload, case.text, case.input_type)


def _verdict(v) -> str:
    return str(getattr(v, "value", v)).lower()


def run_case(db: Session, case: BenchCase) -> dict:
    row = {
        "id": case.id,
        "input_type": case.input_type,
        "expected": case.expected,
        "title": case.title,
        "input_text": case.text,
        "input_file": case.file,
    }
    started = time.perf_counter()
    try:
        text, metadata = extract_case(case)
        result = MessageService(db).analyze_ephemeral(text, case.input_type, metadata)
        verdict = _verdict(result.verdict)
        row.update(
            extracted_text=text[:600],
            verdict=verdict,
            scam_likelihood=round(float(result.threat_score), 4),
            model_probability=round(float(result.scam_probability), 4),
            confidence=round(float(result.confidence_score), 4),
            risk_level=str(result.risk_level),
            scam_category=result.scam_category,
            model=f"{result.model_name} {result.model_version}",
            correct=verdict == case.expected,
        )
    except Exception as exc:  # report, never hide, a failing case
        logger.warning("Test bench case %s failed", case.id, exc_info=True)
        row.update(verdict="error", error=str(exc)[:300], correct=False)
    row["seconds"] = round(time.perf_counter() - started, 2)
    return row


_CACHE: dict[str, tuple[float, dict]] = {}
_TTL_SECONDS = 600


def run_all(db: Session, fresh: bool = False) -> dict:
    cached = _CACHE.get("all")
    if cached and not fresh and time.monotonic() - cached[0] < _TTL_SECONDS:
        return cached[1]
    rows = [run_case(db, c) for c in CASES]
    tp = sum(r["expected"] == "scam" and r["verdict"] == "scam" for r in rows)
    tn = sum(r["expected"] == "legitimate" and r["verdict"] == "legitimate" for r in rows)
    fp = sum(r["expected"] == "legitimate" and r["verdict"] == "scam" for r in rows)
    fn = sum(r["expected"] == "scam" and r["verdict"] != "scam" for r in rows)
    n = len(rows)
    data = {
        "cases": rows,
        "summary": {
            "total": n,
            "correct": tp + tn,
            "accuracy": round((tp + tn) / n, 4),
            "precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
            "recall": round(tp / (tp + fn), 4) if tp + fn else 0.0,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        },
        "model": next((r["model"] for r in rows if r.get("model")), None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _CACHE["all"] = (time.monotonic(), data)
    return data
