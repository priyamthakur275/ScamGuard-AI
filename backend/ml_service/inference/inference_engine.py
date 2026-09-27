"""The raw prediction pipeline (step 16).

Deliberately narrow: this class's only job is "given raw text, return a
class probability" using the exact same preprocessing pipeline and frozen
vectorizer that training used. Confidence scoring, threat scoring, and
explainability are separate, independently-testable collaborators
(Single Responsibility) composed by the PredictionService layer above
this one -- not folded into this class.
"""
from dataclasses import dataclass

from ml_common.domain.value_objects import ModelVersionInfo
from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry


class InferenceEngineNotReadyError(Exception):
    pass


@dataclass(frozen=True)
class RawInferenceResult:
    """The unprocessed output of a single model prediction."""

    scam_probability: float
    predicted_class: int
    model_name: str
    model_version: str


class InferenceEngine:
    """Loads a production model + vectorizer from the registry and scores
    preprocessed text against it.

    The (model, vectorizer) pair is loaded once and cached in memory --
    reloaded only when `reload()` is called (e.g. after a new model is
    promoted) -- so a hot request path never touches disk.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        preprocessor: TextPreprocessingPipeline,
        model_name: str,
    ):
        self._registry = registry
        self._preprocessor = preprocessor
        self._model_name = model_name

        self._estimator = None
        self._vectorizer: TfidfFeatureExtractor | None = None
        self._version_info: ModelVersionInfo | None = None

    def load(self) -> None:
        """Loads (or reloads) the current production model + vectorizer.

        Called once at service startup, and again whenever an admin
        promotes a new model version -- this is the hook the approved
        architecture's "model rollout... registry flag flip" deployment
        strategy relies on: no container rebuild needed for a model update.
        """
        import joblib

        version_info = self._registry.get_production(self._model_name)
        model_path, vectorizer_path = self._registry.resolve_artifact_paths(version_info)

        self._estimator = joblib.load(model_path)
        self._vectorizer = TfidfFeatureExtractor.load(vectorizer_path)
        self._version_info = version_info

    def reload(self) -> None:
        self.load()

    @property
    def is_ready(self) -> bool:
        return self._estimator is not None and self._vectorizer is not None

    @property
    def version_info(self) -> ModelVersionInfo:
        self._require_ready()
        return self._version_info

    def predict(self, raw_text: str) -> RawInferenceResult:
        self._require_ready()

        processed = self._preprocessor.process(raw_text)
        features = self._vectorizer.transform([processed])

        probability = float(self._estimator.predict_proba(features)[0][1])
        predicted_class = int(probability >= 0.5)

        return RawInferenceResult(
            scam_probability=probability,
            predicted_class=predicted_class,
            model_name=self._version_info.model_name,
            model_version=self._version_info.version,
        )

    def transform(self, raw_text: str):
        """Returns (processed_tokens, tfidf_feature_vector) for the given
        raw text, using the exact loaded production vectorizer. Exposed
        so the service layer can drive explainability/threat-scoring
        without duplicating preprocessing logic or reaching past this
        engine into the vectorizer directly.
        """
        self._require_ready()
        tokens = self._preprocessor.process_to_tokens(raw_text)
        processed = self._preprocessor.process(raw_text)
        features = self._vectorizer.transform([processed])
        return tokens, features

    @property
    def estimator(self):
        self._require_ready()
        return self._estimator

    @property
    def feature_names(self) -> list[str]:
        self._require_ready()
        return self._vectorizer.get_feature_names()

    def _require_ready(self) -> None:
        if not self.is_ready:
            raise InferenceEngineNotReadyError(
                "InferenceEngine.load() must be called before predict()"
            )
