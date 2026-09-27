"""Internal inference service (step 20).

This is the orchestration layer the approved architecture calls the
"Internal (not public)" prediction path -- app_service calls into this,
never directly into the inference engine or its collaborators. Every
collaborator is constructor-injected, so this class contains no ML logic
of its own, only sequencing -- easy to unit test with fakes for each
collaborator.
"""
import time
from dataclasses import dataclass

from ml_common.domain.value_objects import PredictionResult
from ml_service.inference.confidence import ConfidenceCalculator
from ml_service.inference.explainer import PredictionExplainer
from ml_service.inference.inference_engine import InferenceEngine
from ml_service.inference.threat_scorer import ThreatScorer
from ml_service.services.explainable_ai import ExplainableAIService

_explainable_ai = ExplainableAIService()


class EmptyMessageError(Exception):
    pass


@dataclass(frozen=True)
class PredictionRequest:
    text: str
    input_type: str = "TEXT"
    metadata: dict | None = None


class PredictionService:
    """The single entrypoint for scoring a message end to end."""

    def __init__(
        self,
        engine: InferenceEngine,
        confidence_calculator: ConfidenceCalculator,
        threat_scorer: ThreatScorer,
        explainer: PredictionExplainer,
    ):
        self._engine = engine
        self._confidence_calculator = confidence_calculator
        self._threat_scorer = threat_scorer
        self._explainer = explainer

    def predict(self, request: PredictionRequest) -> PredictionResult:
        if not request.text or not request.text.strip():
            raise EmptyMessageError("Message text must not be empty")

        start = time.perf_counter()

        raw_result = self._engine.predict(request.text)
        tokens, features = self._engine.transform(request.text)

        threat = self._threat_scorer.assess(raw_result.scam_probability, tokens, request.text)

        # scam_probability is always the model's own, real, unmodified
        # output. threat_score (from the risk engine above) is a distinct,
        # separately-reported number that may incorporate keyword-signal
        # boosting -- it is never used to overwrite what the model itself
        # said. confidence is likewise computed from the model's real
        # probability, not from the risk engine's adjusted score.
        confidence = self._confidence_calculator.calculate(raw_result.scam_probability)

        top_tokens = self._explainer.explain(
            estimator=self._engine.estimator,
            feature_names=self._engine.feature_names,
            message_features=features,
        )

        # The verdict is the risk engine's determination (threat_score),
        # not the raw model probability alone -- that's the reason a risk
        # engine exists on top of the model at all (e.g. a message with
        # multiple strong keyword signals but a middling raw probability
        # should still surface as a scam). scam_probability reported below
        # is unaffected either way.
        verdict = self._classify_verdict(threat.threat_score, threat.scam_category)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        result = PredictionResult(
            verdict=verdict,
            scam_probability=round(raw_result.scam_probability, 4),
            risk_level=threat.risk_level,
            scam_category=threat.scam_category,
            confidence_score=confidence,
            threat_score=threat.threat_score,
            top_contributing_tokens=top_tokens,
            model_name=raw_result.model_name,
            model_version=raw_result.model_version,
            latency_ms=latency_ms,
        )
        
        result = _explainable_ai.enrich(result, request.text, request.input_type, request.metadata)
        return result

    @staticmethod
    def _classify_verdict(threat_score: float, scam_category: str | None) -> str:
        if threat_score < 0.5:
            return "legitimate"
        return "scam"
