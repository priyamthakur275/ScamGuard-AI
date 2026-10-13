"""15 sample inputs (7 scams, 8 genuine) across every channel.

Used to fill the demo account's history. Each one is analysed by the real
pipeline (extraction, model and intent engine) when it is added; nothing
here stores a pre-written verdict.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

from app_service.services.extraction import ExtractionService

logger = logging.getLogger("app_service.sample_scans")

FIXTURES = Path(__file__).resolve().parent.parent / "sample_scans"

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
class SampleCase:
    id: int
    input_type: str  # TEXT, URL, EMAIL, IMAGE, PDF, QR, VOICE
    expected: str  # "scam" | "legitimate"
    title: str
    text: str | None = None
    file: str | None = None


CASES: tuple[SampleCase, ...] = (
    SampleCase(1, "TEXT", "scam", "SBI KYC / OTP SMS", text="Dear SBI customer, your YONO account will be blocked today due to pending KYC. Share the OTP sent to your mobile and update PAN at http://sbi-yono-kyc.xyz or call 9812345670."),
    SampleCase(2, "URL", "scam", "Look-alike PayPal login link", text="http://paypa1-secure-login.verify-account.top/signin"),
    SampleCase(3, "EMAIL", "scam", "Fake HDFC suspension email (SPF/DKIM fail)", text=EMAIL_SCAM),
    SampleCase(4, "IMAGE", "scam", "WhatsApp task-job scam asking a fee", file="chat_scam.png"),
    SampleCase(5, "PDF", "scam", "Fake Amazon offer letter with a deposit", file="offer_scam.pdf"),
    SampleCase(6, "QR", "scam", "QR code to a fake 'SBI reward points' site", file="qr_scam.png"),
    SampleCase(7, "VOICE", "scam", "'Digital arrest' call transcript (Hinglish)", text="Hello, main Mumbai Cyber Crime se Inspector Sharma bol raha hoon. Aapke Aadhaar se ek parcel mein drugs mile hain. Aap digital arrest mein hain, video call disconnect mat karna aur kisi ko mat batana. Case close karne ke liye abhi 50,000 rupaye RBI safe account mein transfer kariye."),
    SampleCase(8, "TEXT", "legitimate", "Genuine bank debit alert", text="Rs. 2,450.00 debited from A/c XX4821 on 12-10-26 to AMAZON PAY. Avl bal Rs. 18,302.55. Not you? Call 1800-1234 (official helpline). Never share your OTP with anyone."),
    SampleCase(9, "TEXT", "legitimate", "Genuine OTP message (Hinglish warning)", text="123456 is your OTP for login to the IRCTC app. Valid for 10 minutes. OTP kisi ke saath share na karein. - IRCTC"),
    SampleCase(10, "TEXT", "legitimate", "Delivery update", text="Your Amazon order #405-1182 with 'boAt Airdopes 141' has been delivered. Thank you for shopping with us."),
    SampleCase(11, "URL", "legitimate", "Official IRCTC website", text="https://www.irctc.co.in/nget/train-search"),
    SampleCase(12, "EMAIL", "legitimate", "Swiggy order receipt (SPF/DKIM pass)", text=EMAIL_LEGIT),
    SampleCase(13, "IMAGE", "legitimate", "Family WhatsApp chat", file="chat_legit.png"),
    SampleCase(14, "PDF", "legitimate", "College circular", file="circular_legit.pdf"),
    SampleCase(15, "VOICE", "legitimate", "Normal family call transcript", text="Hi beta, main office se nikal gaya hoon, around seven baje tak ghar pahunch jaunga. Dinner pe wait karna, aur kal subah tumhari college fees online bhar denge."),
)


class _FixtureUpload:
    """Minimal stand-in for an UploadFile backed by a fixture on disk."""

    def __init__(self, name: str):
        self.filename = name
        self.content_type = "application/pdf" if name.endswith(".pdf") else "image/png"
        self.file = io.BytesIO((FIXTURES / name).read_bytes())


def extract_case(case: SampleCase) -> tuple[str, dict]:
    upload = _FixtureUpload(case.file) if case.file else None
    return ExtractionService.extract(upload, case.text, case.input_type)
