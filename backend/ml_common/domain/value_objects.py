"""Shared, framework-agnostic domain value objects.

Neither ml_training nor ml_service imports FROM the other -- both only
depend on ml_common. This one-directional dependency graph (Dependency
Inversion Principle) is what allows the training pipeline and the serving
process to be deployed, scaled, and released completely independently, as
called out in the approved architecture's deployment section.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class ModelMetrics:
    """Evaluation metrics for a single trained model."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    false_positive_rate: float
    # Raw confusion matrix counts on the evaluation split. Optional
    # (default 0) so existing positional-argument call sites -- including
    # tests that predate this field -- keep working unchanged.
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    def to_dict(self) -> dict:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "false_positive_rate": self.false_positive_rate,
            "confusion_matrix": {
                "true_positives": self.true_positives,
                "true_negatives": self.true_negatives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMetrics":
        cm = data.get("confusion_matrix", {})
        return cls(
            accuracy=data["accuracy"],
            precision=data["precision"],
            recall=data["recall"],
            f1=data["f1"],
            roc_auc=data["roc_auc"],
            false_positive_rate=data["false_positive_rate"],
            true_positives=cm.get("true_positives", 0),
            true_negatives=cm.get("true_negatives", 0),
            false_positives=cm.get("false_positives", 0),
            false_negatives=cm.get("false_negatives", 0),
        )


@dataclass(frozen=True)
class ModelVersionInfo:
    """Metadata describing one registered, versioned model artifact."""

    model_name: str
    version: str
    metrics: ModelMetrics
    is_production: bool
    trained_at: str
    artifact_path: str
    vectorizer_path: str
    # Real dataset size at training time -- 0 for entries registered
    # before this field existed (old registrations), never backfilled
    # with a guess. See Phase 15: dataset size must be shown honestly,
    # including "not available for this older entry" rather than invented.
    train_rows: int = 0
    test_rows: int = 0

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "version": self.version,
            "metrics": self.metrics.to_dict(),
            "is_production": self.is_production,
            "trained_at": self.trained_at,
            "artifact_path": self.artifact_path,
            "vectorizer_path": self.vectorizer_path,
            "train_rows": self.train_rows,
            "test_rows": self.test_rows,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelVersionInfo":
        return cls(
            model_name=data["model_name"],
            version=data["version"],
            metrics=ModelMetrics.from_dict(data["metrics"]),
            is_production=data["is_production"],
            trained_at=data["trained_at"],
            artifact_path=data["artifact_path"],
            vectorizer_path=data["vectorizer_path"],
            train_rows=data.get("train_rows", 0),
            test_rows=data.get("test_rows", 0),
        )


@dataclass(frozen=True)
class FeatureContribution:
    """A single token's contribution to a prediction, used for
    explainability output ("suspicious keywords" in the approved design).
    """

    token: str
    weight: float


@dataclass(frozen=True)
class PredictionResult:
    """The complete result of scoring one message, independent of any
    web framework -- this is what the inference engine returns, and what
    the FastAPI layer serializes into an HTTP response.
    """

    verdict: str
    scam_probability: float
    risk_level: str
    scam_category: str | None
    confidence_score: float
    threat_score: float
    top_contributing_tokens: list[FeatureContribution] = field(default_factory=list)
    model_name: str = ""
    model_version: str = ""
    latency_ms: float = 0.0
    scored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ai_explanation: str | None = None
    executive_summary: str | None = None
    technical_explanation: str | None = None
    threat_level: str | None = None
    risk_breakdown: dict | None = None
    recommended_actions: list | None = None
    highlighted_entities: dict | None = None
    similar_patterns: list | None = None
