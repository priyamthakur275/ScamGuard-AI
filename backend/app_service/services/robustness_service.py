"""Adversarial/robustness testing orchestration (Phase 16).

INTERNAL ENGINEERING/EVALUATION TOOLING -- not part of the live user scan
flow, never persisted to user history (uses analyze_ephemeral, same
mechanism as Demo Mode), admin-only (see the API route).

Every comparison here is between two REAL outputs of the exact same
pipeline a genuine scan uses -- the base message's real prediction, and
the transformed variant's real prediction. Nothing is simulated, capped,
or adjusted after the fact. The stability classification is a fixed,
documented threshold on the actual observed probability delta -- it is
never tuned per-run and never suppresses an unfavorable result.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app_service.schemas.message import AnalysisResult
from app_service.services.extraction import ExtractionService
from app_service.services.message_service import MessageService
from ml_common.testing.robustness_transforms import apply_all_transforms

_SIGNIFICANT_DELTA = 0.15
_MODERATE_DELTA = 0.05

_SCAM_BASE_MESSAGES: tuple[tuple[str, str], ...] = (
    ("bank_otp", "URGENT: verify your bank account immediately, share the OTP now or it will be suspended"),
    ("phishing_url", "Your account needs verification, click http://arnazon-verify.tk/login now"),
)
_BENIGN_SCAM_VOCAB_MESSAGES: tuple[tuple[str, str], ...] = (
    ("benign_otp_mention", "I got my OTP for the banking app fine, no issues logging in today"),
    ("benign_investment_mention", "We're reviewing our investment portfolio with the financial advisor next week"),
    ("benign_urgent_word", "This is urgent -- can you send me the meeting notes before 5pm?"),
)


@dataclass(frozen=True)
class TransformResult:
    transform_code: str
    transform_label: str
    transformed_text: str
    base_verdict: str
    base_probability: float
    transformed_verdict: str
    transformed_probability: float
    verdict_changed: bool
    probability_delta: float
    stability: str

    def to_dict(self) -> dict:
        return {
            "transform_code": self.transform_code,
            "transform_label": self.transform_label,
            "transformed_text": self.transformed_text,
            "base_verdict": self.base_verdict,
            "base_probability": self.base_probability,
            "transformed_verdict": self.transformed_verdict,
            "transformed_probability": self.transformed_probability,
            "verdict_changed": self.verdict_changed,
            "probability_delta": self.probability_delta,
            "stability": self.stability,
        }


@dataclass(frozen=True)
class BaseMessageReport:
    message_id: str
    category: str
    base_text: str
    base_verdict: str
    base_probability: float
    transform_results: tuple[TransformResult, ...]

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "category": self.category,
            "base_text": self.base_text,
            "base_verdict": self.base_verdict,
            "base_probability": self.base_probability,
            "transform_results": [t.to_dict() for t in self.transform_results],
        }


def _classify_stability(delta: float) -> str:
    if delta >= _SIGNIFICANT_DELTA:
        return "significantly_changed"
    if delta >= _MODERATE_DELTA:
        return "changed"
    return "stable"


def _run_single(message_service: MessageService, text: str, input_type: str = "TEXT") -> AnalysisResult:
    extracted_text, metadata = ExtractionService.extract(None, text, input_type)
    return message_service.analyze_ephemeral(extracted_text, input_type, metadata)


def run_robustness_suite(db: Session) -> tuple[BaseMessageReport, ...]:
    message_service = MessageService(db)
    reports = []

    all_base_messages = (
        [(mid, "scam", text) for mid, text in _SCAM_BASE_MESSAGES]
        + [(mid, "benign_scam_vocab", text) for mid, text in _BENIGN_SCAM_VOCAB_MESSAGES]
    )

    for message_id, category, base_text in all_base_messages:
        base_result = _run_single(message_service, base_text)

        transform_results = []
        for transform in apply_all_transforms(base_text):
            if transform.transformed_text == base_text:
                transform_results.append(TransformResult(
                    transform_code=transform.code,
                    transform_label=transform.label,
                    transformed_text=transform.transformed_text,
                    base_verdict=base_result.verdict,
                    base_probability=base_result.scam_probability,
                    transformed_verdict=base_result.verdict,
                    transformed_probability=base_result.scam_probability,
                    verdict_changed=False,
                    probability_delta=0.0,
                    stability="not_applicable",
                ))
                continue

            transformed_result = _run_single(message_service, transform.transformed_text)
            delta = round(abs(transformed_result.scam_probability - base_result.scam_probability), 4)
            transform_results.append(TransformResult(
                transform_code=transform.code,
                transform_label=transform.label,
                transformed_text=transform.transformed_text,
                base_verdict=base_result.verdict,
                base_probability=base_result.scam_probability,
                transformed_verdict=transformed_result.verdict,
                transformed_probability=transformed_result.scam_probability,
                verdict_changed=transformed_result.verdict != base_result.verdict,
                probability_delta=delta,
                stability=_classify_stability(delta),
            ))

        reports.append(BaseMessageReport(
            message_id=message_id,
            category=category,
            base_text=base_text,
            base_verdict=base_result.verdict,
            base_probability=base_result.scam_probability,
            transform_results=tuple(transform_results),
        ))

    return tuple(reports)
