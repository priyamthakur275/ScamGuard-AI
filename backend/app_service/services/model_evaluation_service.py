"""Admin Model Evaluation (Phase 15).

Reads exactly what's in the model registry (registry_index.json) -- the
same registry the inference service itself reads from to serve real
predictions. This module computes nothing new and invents nothing: every
number here was produced by ml_training/evaluation/evaluator.py during an
actual training run, using scikit-learn's real metric functions against a
real held-out test split.

Deliberately separate from app_service.schemas.message.AnalysisResult
(the user-facing prediction result) -- this is engineering/admin-only
data about the MODEL, never mixed into what an end user sees about their
own scan.
"""
from ml_service.core.config import get_settings
from app_service.schemas.model_evaluation import ConfusionMatrix, ModelEvaluationEntry
from ml_common.registry.model_registry import ModelRegistry

_SMALL_DATASET_THRESHOLD = 200


def _dataset_limitation_note(dataset_size: int) -> str | None:
    if dataset_size == 0:
        return "Dataset size not recorded for this entry (registered before dataset-size tracking was added)."
    if dataset_size < _SMALL_DATASET_THRESHOLD:
        return (
            f"This model was evaluated on only {dataset_size} labeled examples. Metrics from a "
            "sample this small are illustrative of the pipeline working end-to-end, not a "
            "reliable estimate of real-world accuracy -- treat them as a sanity check, not a "
            "production benchmark."
        )
    return None


def get_model_evaluations() -> list[ModelEvaluationEntry]:
    settings = get_settings()
    registry = ModelRegistry(root_dir=settings.ARTIFACTS_DIR)
    entries = []
    for info in registry.list_all():
        dataset_size = info.train_rows + info.test_rows
        entries.append(ModelEvaluationEntry(
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
            confusion_matrix=ConfusionMatrix(
                true_positives=info.metrics.true_positives,
                true_negatives=info.metrics.true_negatives,
                false_positives=info.metrics.false_positives,
                false_negatives=info.metrics.false_negatives,
            ),
            train_rows=info.train_rows,
            test_rows=info.test_rows,
            dataset_size=dataset_size,
            dataset_limitation_note=_dataset_limitation_note(dataset_size),
        ))
    return entries
