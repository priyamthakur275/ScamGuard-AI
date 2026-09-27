import sys
from pathlib import Path

# Ensure backend root is always present in sys.path for unpickling ml_common artifacts
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
_ROOT_DIR = _BACKEND_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

import uuid

import httpx
from sqlalchemy.orm import Session

from app_service.core.config import get_settings
from app_service.core.exceptions import NotFoundError, ValidationAppError
from app_service.db.postgres.models import Prediction
from app_service.repositories.message_repository import MessageRepository, PredictionRepository
from app_service.schemas.message import AnalysisResult

settings = get_settings()


class MlServiceUnavailableError(ValidationAppError):
    status_code = 503
    error_code = "MODEL_UNAVAILABLE"


import threading
import logging

logger = logging.getLogger("app_service.ml_client")

_in_process_svc = None
_in_process_lock = threading.Lock()


def get_in_process_prediction_service():
    """Lazily instantiate the genuine in-process ML inference pipeline.
    Ensures zero downtime and complete functionality even if the separate
    ML microservice container is sleeping or temporarily unreachable.
    """
    global _in_process_svc
    if _in_process_svc is None:
        with _in_process_lock:
            if _in_process_svc is None:
                from ml_service.api.deps import build_inference_engine
                from ml_service.services.prediction_service import PredictionService
                from ml_service.inference.confidence import ConfidenceCalculator
                from ml_service.inference.threat_scorer import ThreatScorer
                from ml_service.inference.explainer import PredictionExplainer

                engine = build_inference_engine()
                engine.load()
                _in_process_svc = PredictionService(
                    engine=engine,
                    confidence_calculator=ConfidenceCalculator(),
                    threat_scorer=ThreatScorer(),
                    explainer=PredictionExplainer(),
                )
    return _in_process_svc


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.messages = MessageRepository(db)
        self.predictions = PredictionRepository(db)

    def _run_pipeline(self, text: str, input_type: str, metadata: dict | None) -> tuple[dict, str, dict]:
        """The real ML/XAI pipeline call, extracted so both analyze()
        (persists a Message+Prediction) and analyze_ephemeral() (Phase 13
        demo mode -- runs the exact same real pipeline but never writes to
        the database) share one implementation instead of duplicating it.
        Returns (data, normalized_text, metadata).
        """
        if text is None or not text.strip():
            raise ValidationAppError("Message text must not be empty.")

        # English/Hindi/Hinglish preprocessing (Phase 7): appends an
        # English-language summary of detected Indian scam concepts
        # (OTP/UPI/KYC/etc.) so the existing English-only model has
        # recognizable tokens even when the message itself is in Hindi or
        # Hinglish. Never modifies the original text -- only appends, same
        # convention as the URL/email/voice evidence blocks elsewhere in
        # this pipeline. Applied once here, centrally, so every input
        # modality (text/URL/email/image OCR/PDF/voice) benefits from it
        # without duplicating this call in each extractor.
        from ml_common.preprocessing.multilingual import analyze_multilingual, normalize_for_analysis
        multilingual = analyze_multilingual(text)
        text = normalize_for_analysis(text)
        if metadata is None:
            metadata = {}
        metadata = {**metadata, "multilingual": multilingual.to_dict()}

        # Clamp text to 4000 characters to strictly respect database and ML schema constraints
        if len(text) > 4000:
            text = text[:4000]

        data = None
        # 1. First: Try remote ML microservice if configured (with quick 1.5s timeout)
        if settings.ML_SERVICE_URL:
            try:
                response = httpx.post(
                    f"{settings.ML_SERVICE_URL}/api/v1/internal/predict",
                    json={"text": text, "input_type": input_type, "metadata": metadata},
                    timeout=1.5,
                )
                if response.status_code == 200:
                    data = response.json()
            except Exception as remote_exc:
                logger.info("Remote ML service unreachable (%s). Using high-speed in-process ML pipeline...", remote_exc)

        # 2. Second: High-speed In-Process ML Pipeline (sub-millisecond genuine ML inference)
        if data is None:
            try:
                svc = get_in_process_prediction_service()
                from ml_service.services.prediction_service import PredictionRequest
                res = svc.predict(PredictionRequest(text=text, input_type=input_type, metadata=metadata))
                data = {
                    "verdict": res.verdict,
                    "scam_probability": res.scam_probability,
                    "risk_level": res.risk_level,
                    "scam_category": res.scam_category,
                    "confidence_score": res.confidence_score,
                    "threat_score": res.threat_score,
                    "top_contributing_tokens": [
                        {"token": t.token, "weight": t.weight}
                        for t in res.top_contributing_tokens
                    ],
                    "model_name": res.model_name,
                    "model_version": res.model_version,
                    "latency_ms": res.latency_ms,
                    "ai_explanation": res.ai_explanation,
                    "executive_summary": res.executive_summary,
                    "technical_explanation": res.technical_explanation,
                    "threat_level": res.threat_level,
                    "risk_breakdown": res.risk_breakdown,
                    "recommended_actions": res.recommended_actions,
                    "highlighted_entities": res.highlighted_entities,
                    "similar_patterns": res.similar_patterns,
                }
            except Exception as in_proc_exc:
                logger.error("In-process ML pipeline failed: %s", in_proc_exc)

        # There is no third tier. A keyword-only heuristic used to run here,
        # presenting itself as a model (fixed 92% "confidence", a fabricated
        # model_name, a probability derived from ThreatScorer.assess(0.50, ...)
        # with no real model in the loop at all). That fallback has been
        # removed entirely: if neither the remote ML service nor the real
        # in-process model produced a result, we tell the caller the truth
        # -- the model is unavailable -- rather than manufacture a
        # convincing-looking fake prediction.
        if data is None:
            raise MlServiceUnavailableError(
                "The scam-detection model is temporarily unavailable. Please try again shortly."
            )

        return data, text, metadata

    def analyze(self, user_id: uuid.UUID | None, text: str, input_type: str = "TEXT", metadata: dict | None = None) -> AnalysisResult:
        data, text, metadata = self._run_pipeline(text, input_type, metadata)

        message = self.messages.create(user_id, text)
        prediction = Prediction(
            message_id=message.id,
            model_name=data["model_name"],
            model_version=data["model_version"],
            verdict=data["verdict"],
            scam_probability=data["scam_probability"],
            risk_level=data["risk_level"],
            scam_category=data.get("scam_category"),
            confidence_score=data["confidence_score"],
            threat_score=data["threat_score"],
            top_tokens=data["top_contributing_tokens"],
            latency_ms=int(data["latency_ms"]),
            ai_explanation=data.get("ai_explanation"),
            executive_summary=data.get("executive_summary"),
            technical_explanation=data.get("technical_explanation"),
            threat_level=data.get("threat_level"),
            risk_breakdown=data.get("risk_breakdown"),
            recommended_actions=data.get("recommended_actions"),
            highlighted_entities=data.get("highlighted_entities"),
            similar_patterns=data.get("similar_patterns"),
            input_type=input_type,
            metadata_=metadata,
        )
        prediction = self.predictions.create(prediction)

        # Phase 14: correlate this scan's own real domain/entities/category
        # against this same user's own past scans -- never external
        # threat-intel, purely "have you seen this before" recurrence.
        if user_id is not None:
            from app_service.services.correlation_service import correlate
            url_intel = (metadata or {}).get("url_intelligence") or {}
            correlation_signals = correlate(
                self.db,
                user_id,
                prediction.id,
                current_entities=data.get("highlighted_entities"),
                current_domain=url_intel.get("registrable_domain"),
                current_lookalike_brand=url_intel.get("lookalike_of"),
                current_category=data.get("scam_category"),
            )
            if correlation_signals:
                prediction.metadata_ = {
                    **(prediction.metadata_ or {}),
                    "correlation": [
                        {"code": s.code, "severity": s.severity, "reason": s.reason} for s in correlation_signals
                    ],
                }
                prediction = self.predictions.save(prediction)

        return self._to_result(prediction, text)

    def analyze_ephemeral(self, text: str, input_type: str = "TEXT", metadata: dict | None = None) -> AnalysisResult:
        """Phase 13 demo mode: runs the SAME real pipeline as analyze()
        (same ML inference, same threat scoring, same XAI -- no
        duplicated/simplified logic) but writes NOTHING to the database.
        This is the mechanism that keeps demo runs completely separate
        from a user's real scan history -- not a filter applied after the
        fact, but a genuine guarantee that no Message/Prediction row is
        ever created for a demo run.
        """
        data, text, metadata = self._run_pipeline(text, input_type, metadata)
        import uuid as uuid_module
        from datetime import datetime, timezone
        from app_service.schemas.message import TokenContribution

        return AnalysisResult(
            id=uuid_module.uuid4(),
            text=text,
            input_type=input_type,
            metadata=metadata,
            verdict=data["verdict"],
            scam_probability=data["scam_probability"],
            risk_level=data["risk_level"],
            scam_category=data.get("scam_category"),
            confidence_score=data["confidence_score"],
            threat_score=data["threat_score"],
            top_contributing_tokens=[TokenContribution(**t) for t in data["top_contributing_tokens"]],
            model_name=data["model_name"],
            model_version=data["model_version"],
            latency_ms=data["latency_ms"],
            user_feedback=None,
            ai_explanation=data.get("ai_explanation"),
            executive_summary=data.get("executive_summary"),
            technical_explanation=data.get("technical_explanation"),
            threat_level=data.get("threat_level"),
            risk_breakdown=data.get("risk_breakdown"),
            recommended_actions=data.get("recommended_actions"),
            highlighted_entities=data.get("highlighted_entities"),
            similar_patterns=data.get("similar_patterns"),
            created_at=datetime.now(timezone.utc),
        )

    def list_history(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50) -> list[AnalysisResult]:
        predictions = self.predictions.list_for_user(user_id, skip=skip, limit=limit)
        return [self._to_result(p, p.message.text) for p in predictions]

    def record_feedback(self, user_id: uuid.UUID, prediction_id: uuid.UUID, is_accurate: bool) -> AnalysisResult:
        prediction = self.predictions.get_for_user(prediction_id, user_id)
        if prediction is None:
            raise NotFoundError("Prediction not found")
        prediction.user_feedback = is_accurate
        prediction = self.predictions.save(prediction)
        return self._to_result(prediction, prediction.message.text)

    def get_result_for_user(self, user_id: uuid.UUID, prediction_id: uuid.UUID) -> AnalysisResult:
        prediction = self.predictions.get_for_user(prediction_id, user_id)
        if prediction is None:
            raise NotFoundError("Prediction not found")
        return self._to_result(prediction, prediction.message.text)

    def clear_history(self, user_id: uuid.UUID) -> None:
        while predictions := self.predictions.list_for_user(user_id, skip=0, limit=500):
            for prediction in predictions:
                self.messages.delete(prediction.message)

    def delete_prediction(self, user_id: uuid.UUID, prediction_id: uuid.UUID) -> None:
        prediction = self.predictions.get_for_user(prediction_id, user_id)
        if prediction is None:
            raise NotFoundError("Prediction not found")
        self.messages.delete(prediction.message)

    @staticmethod
    def _to_result(prediction: Prediction, text: str) -> AnalysisResult:
        return AnalysisResult(
            id=prediction.id,
            text=text,
            input_type=prediction.input_type,
            metadata=prediction.metadata_,
            verdict=prediction.verdict.value,
            scam_probability=prediction.scam_probability,
            risk_level=prediction.risk_level.value,
            scam_category=prediction.scam_category,
            confidence_score=prediction.confidence_score,
            threat_score=prediction.threat_score,
            top_contributing_tokens=prediction.top_tokens,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            latency_ms=prediction.latency_ms,
            user_feedback=prediction.user_feedback,
            ai_explanation=prediction.ai_explanation,
            executive_summary=prediction.executive_summary,
            technical_explanation=prediction.technical_explanation,
            threat_level=prediction.threat_level,
            risk_breakdown=prediction.risk_breakdown,
            recommended_actions=prediction.recommended_actions,
            highlighted_entities=prediction.highlighted_entities,
            similar_patterns=prediction.similar_patterns,
            created_at=prediction.created_at,
        )
