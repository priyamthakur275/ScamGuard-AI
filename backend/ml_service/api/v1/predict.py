from fastapi import APIRouter, Depends, Request

from ml_service.api.deps import get_model_registry, get_prediction_service
from ml_service.core.config import get_settings
from ml_service.core.exceptions import InferenceFailedError, InvalidRequestError
from ml_service.core.rate_limit import limiter
from ml_service.inference.inference_engine import InferenceEngineNotReadyError
from ml_common.registry.model_registry import ModelNotFoundError, ModelRegistry
from ml_service.schemas.prediction import (
    FeatureContributionResponse,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
)
from ml_service.services.prediction_service import (
    EmptyMessageError,
    PredictionRequest,
    PredictionService,
)

settings = get_settings()

router = APIRouter(prefix="/internal", tags=["inference"])


@router.post("/predict", response_model=PredictResponse)
@limiter.limit(settings.RATE_LIMIT_PREDICT)
def predict(
    request: Request,
    payload: PredictRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictResponse:
    try:
        result = service.predict(PredictionRequest(text=payload.text, input_type=payload.input_type, metadata=payload.metadata))
    except EmptyMessageError as exc:
        raise InvalidRequestError(str(exc)) from exc
    except InferenceEngineNotReadyError as exc:
        raise InferenceFailedError(str(exc)) from exc

    return PredictResponse(
        verdict=result.verdict,
        input_type=payload.input_type,
        metadata=payload.metadata,
        scam_probability=result.scam_probability,
        risk_level=result.risk_level,
        scam_category=result.scam_category,
        confidence_score=result.confidence_score,
        threat_score=result.threat_score,
        top_contributing_tokens=[
            FeatureContributionResponse(token=t.token, weight=t.weight)
            for t in result.top_contributing_tokens
        ],
        model_name=result.model_name,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        ai_explanation=result.ai_explanation,
        executive_summary=result.executive_summary,
        technical_explanation=result.technical_explanation,
        threat_level=result.threat_level,
        risk_breakdown=result.risk_breakdown,
        recommended_actions=result.recommended_actions,
        highlighted_entities=result.highlighted_entities,
        similar_patterns=result.similar_patterns,
    )


@router.get("/models/{model_name}/production", response_model=ModelInfoResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_production_model_info(
    request: Request,
    model_name: str,
    registry: ModelRegistry = Depends(get_model_registry),
) -> ModelInfoResponse:
    try:
        info = registry.get_production(model_name)
    except ModelNotFoundError as exc:
        raise InvalidRequestError(str(exc)) from exc

    return ModelInfoResponse(
        model_name=info.model_name,
        version=info.version,
        is_production=info.is_production,
        trained_at=info.trained_at,
        accuracy=info.metrics.accuracy,
        precision=info.metrics.precision,
        recall=info.metrics.recall,
        f1=info.metrics.f1,
        roc_auc=info.metrics.roc_auc,
        false_positive_rate=info.metrics.false_positive_rate,
    )
