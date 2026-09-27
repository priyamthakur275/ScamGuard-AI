"""Model evaluation and metrics.

False Positive Rate is computed explicitly and separately from the other
four required metrics because, as the approved architecture states, "in
fraud detection a false positive... has a real UX cost" -- it is the
metric most directly tied to the report's own non-functional requirement
of minimizing false positives.
"""
from dataclasses import dataclass

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ml_common.domain.value_objects import ModelMetrics


@dataclass(frozen=True)
class EvaluationCandidate:
    """One trained model paired with its computed metrics, ready to be
    ranked against other candidates from the same training run.
    """

    model_name: str
    metrics: ModelMetrics


class ModelEvaluator:
    """Computes standard classification metrics and selects a winner."""

    def evaluate(self, y_true: list[int], y_pred: list[int], y_proba: list[float]) -> ModelMetrics:
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        if len(set(y_true)) < 2:
            # roc_auc_score is mathematically undefined with only one
            # class present in the evaluation split (can happen on a
            # tiny or heavily imbalanced test set). Depending on the
            # scikit-learn version this either raises ValueError or
            # returns nan with a warning -- handle both explicitly rather
            # than letting an undefined metric abort the whole run.
            roc_auc = 0.5
        else:
            try:
                roc_auc = roc_auc_score(y_true, y_proba)
                if roc_auc != roc_auc:  # NaN check without importing math/numpy here
                    roc_auc = 0.5
            except ValueError:
                roc_auc = 0.5

        false_positive_rate, cm_counts = self._confusion_counts(y_true, y_pred)

        return ModelMetrics(
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1=float(f1),
            roc_auc=float(roc_auc),
            false_positive_rate=float(false_positive_rate),
            true_positives=cm_counts["true_positives"],
            true_negatives=cm_counts["true_negatives"],
            false_positives=cm_counts["false_positives"],
            false_negatives=cm_counts["false_negatives"],
        )

    @staticmethod
    def _confusion_counts(y_true: list[int], y_pred: list[int]) -> tuple[float, dict[str, int]]:
        matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
        true_negative, false_positive = matrix[0][0], matrix[0][1]
        false_negative, true_positive = matrix[1][0], matrix[1][1]
        denominator = false_positive + true_negative
        fpr = false_positive / denominator if denominator else 0.0
        return fpr, {
            "true_positives": int(true_positive),
            "true_negatives": int(true_negative),
            "false_positives": int(false_positive),
            "false_negatives": int(false_negative),
        }

    @staticmethod
    def select_best(
        candidates: list[EvaluationCandidate],
        primary_metric: str = "f1",
    ) -> EvaluationCandidate:
        """Selects the production-default candidate by F1 score, per the
        approved architecture's stated model-selection rule (F1/latency
        tradeoff, classical model as default). Ties are broken by the
        lower false-positive rate.
        """
        if not candidates:
            raise ValueError("Cannot select a best candidate from an empty list")

        return max(
            candidates,
            key=lambda c: (getattr(c.metrics, primary_metric), -c.metrics.false_positive_rate),
        )
