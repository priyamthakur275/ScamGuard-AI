"""Shared, read-mostly demo account for reviews and first-time visitors.

The account is created on startup (and again on demand if it was removed)
and filled with a handful of sample scans run through the *real* analysis
pipeline, so the dashboard, history and analytics pages are never empty in a demo. Nothing here fabricates a
result: every stored verdict is produced by MessageService.analyze.
"""
import logging
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app_service.core.config import get_settings
from app_service.core.security import hash_password
from app_service.db.postgres.models import Message, User, UserRole
from app_service.services.extraction import ExtractionService
from app_service.services.message_service import MessageService

logger = logging.getLogger("app_service.demo_account")

# Sample inputs only -- the verdicts come from the live pipeline.
_SAMPLE_SCANS: tuple[tuple[str, str], ...] = (
    ("TEXT", "URGENT: Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-verify.xyz and share the OTP sent to your phone. Call +91 9876543210."),
    ("TEXT", "Congratulations! You have been selected for a work-from-home data entry job paying Rs. 45,000 per month. Pay a refundable registration fee of Rs. 1500 via UPI within 2 hours to confirm."),
    ("TEXT", "Dear Customer, your electricity connection will be disconnected tonight at 9:30 PM. Pay the pending bill immediately: http://bescom-billpay.top or call 8123456789."),
    ("TEXT", "Aapka SBI khata aaj band ho jayega. Turant KYC update karo aur jo OTP aaya hai woh is number pe bhejo: 9876543210"),
    ("TEXT", "Double your money in 7 days! Join our stock trading group with guaranteed 300% returns. Limited slots, invest now before the offer closes tonight."),
    ("URL", "http://paypa1-secure-login.verify-account.top/signin"),
    ("TEXT", "Your parcel is held at customs due to unpaid duty of Rs. 350. Pay at http://indiapost-redelivery.xyz/pay within 24 hours or it will be returned."),
    ("TEXT", "Hi, are you still free to grab lunch tomorrow around 1pm? Let me know."),
    ("TEXT", "Reminder: your dentist appointment is at 10am tomorrow at Bright Smile Clinic."),
)


def is_demo_user(user: User) -> bool:
    settings = get_settings()
    return settings.DEMO_ACCOUNT_ENABLED and user.email.lower() == settings.DEMO_ACCOUNT_EMAIL.lower()


def ensure_demo_account(db: Session) -> User:
    """Return the demo user, creating it (and its sample data) if needed."""
    settings = get_settings()
    email = settings.DEMO_ACCOUNT_EMAIL.lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        user = User(
            email=email,
            # Random, never disclosed: the account is reachable only via
            # POST /auth/demo-login, never by password.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.USER,
            full_name="Demo Reviewer",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.is_active:
        user.is_active = True
        db.commit()

    has_scans = db.scalar(select(func.count()).select_from(Message).where(Message.user_id == user.id))
    if not has_scans:
        _seed(db, user)
    return user


def seed_sample_scans(db: Session) -> int:
    """Add the 15 sample scans to the demo account and to each account in
    SAMPLE_SCAN_EMAILS, once.

    Each case runs through the real pipeline (extraction, model, intent
    engine). A case is skipped if that history already holds it (stored text
    starts with the same extracted text), so restarts never duplicate it.
    Accounts that do not exist yet are skipped. Returns how many were added.
    """
    from app_service.services.sample_scans import CASES, extract_case

    users = [ensure_demo_account(db)]
    for email in (e.strip().lower() for e in get_settings().SAMPLE_SCAN_EMAILS.split(",")):
        if email:
            u = db.scalar(select(User).where(func.lower(User.email) == email))
            if u is not None:
                users.append(u)
    extracted = []
    for case in CASES:
        try:
            extracted.append((case, *extract_case(case)))
        except Exception:
            logger.warning("Sample scan %s could not be extracted.", case.id, exc_info=True)
    messages = MessageService(db)
    added = 0
    for user in users:
        existing = list(db.scalars(select(Message.text).where(Message.user_id == user.id)).all())
        for case, text, metadata in extracted:
            if any(e.startswith(text[:300]) for e in existing):
                continue
            try:
                messages.analyze(user.id, text, case.input_type, {**(metadata or {}), "sample_case": case.id})
                existing.append(text)
                added += 1
            except Exception:
                logger.warning("Sample scan %s could not be added for a user.", case.id, exc_info=True)
    return added


def _seed(db: Session, user: User) -> None:
    messages = MessageService(db)
    for input_type, raw in _SAMPLE_SCANS:
        try:
            text, metadata = ExtractionService.extract(None, raw, input_type)
            messages.analyze(user.id, text, input_type, metadata)
        except Exception:
            logger.warning("Demo sample scan failed; continuing with the rest.", exc_info=True)

