"""Dependency injection wiring for the ML service.

`InferenceEngine` is the one piece of state that must be a true
singleton (it holds a loaded model in memory); it is constructed once and
stored on `app.state` at startup (see main.py). Every other collaborator
here is cheap to construct and is created fresh per dependency call --
they are all stateless, so there's no correctness reason to share them,
only a minor allocation cost, which is negligible compared to inference
itself.
"""
from fastapi import Request

from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry
from ml_service.core.config import get_settings
from ml_service.core.exceptions import ModelUnavailableError
from ml_service.inference.confidence import ConfidenceCalculator
from ml_service.inference.explainer import PredictionExplainer
from ml_service.inference.inference_engine import InferenceEngine, InferenceEngineNotReadyError
from ml_service.inference.threat_scorer import ThreatScorer
from ml_service.services.prediction_service import PredictionService

settings = get_settings()


def get_model_registry() -> ModelRegistry:
    return ModelRegistry(root_dir=settings.ARTIFACTS_DIR)


def get_preprocessor() -> TextPreprocessingPipeline:
    return TextPreprocessingPipeline()


def build_inference_engine() -> InferenceEngine:
    """Constructs (but does not load) the InferenceEngine singleton.
    Called once at application startup; `load()` is called separately so
    a slow/failed model load surfaces as a clear readiness-probe failure
    rather than an import-time crash.
    """
    return InferenceEngine(
        registry=get_model_registry(),
        preprocessor=get_preprocessor(),
        model_name=settings.PRODUCTION_MODEL_NAME,
    )


def get_inference_engine(request: Request) -> InferenceEngine:
    engine: InferenceEngine | None = getattr(request.app.state, "inference_engine", None)
    if engine is None or not engine.is_ready:
        raise ModelUnavailableError(
            "No production model is currently loaded for inference"
        )
    return engine


def get_prediction_service(request: Request) -> PredictionService:
    try:
        engine = get_inference_engine(request)
    except InferenceEngineNotReadyError as exc:
        raise ModelUnavailableError(str(exc)) from exc

    return PredictionService(
        engine=engine,
        confidence_calculator=ConfidenceCalculator(),
        threat_scorer=ThreatScorer(),
        explainer=PredictionExplainer(),
    )
