from ml_common.domain.value_objects import ModelMetrics
from ml_training.evaluation.evaluator import EvaluationCandidate, ModelEvaluator


class TestModelEvaluator:
    def test_perfect_predictions_yield_perfect_metrics(self):
        evaluator = ModelEvaluator()
        y_true = [0, 0, 1, 1]
        y_pred = [0, 0, 1, 1]
        y_proba = [0.1, 0.2, 0.9, 0.95]

        metrics = evaluator.evaluate(y_true, y_pred, y_proba)

        assert metrics.accuracy == 1.0
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0
        assert metrics.false_positive_rate == 0.0

    def test_all_wrong_predictions_yield_zero_metrics(self):
        evaluator = ModelEvaluator()
        y_true = [0, 0, 1, 1]
        y_pred = [1, 1, 0, 0]
        y_proba = [0.9, 0.8, 0.1, 0.2]

        metrics = evaluator.evaluate(y_true, y_pred, y_proba)

        assert metrics.accuracy == 0.0
        assert metrics.recall == 0.0

    def test_false_positive_rate_computed_correctly(self):
        evaluator = ModelEvaluator()
        # 2 true negatives, 2 false positives -> FPR = 2/4 = 0.5
        y_true = [0, 0, 0, 0]
        y_pred = [0, 0, 1, 1]
        y_proba = [0.1, 0.2, 0.6, 0.7]

        metrics = evaluator.evaluate(y_true, y_pred, y_proba)

        assert metrics.false_positive_rate == 0.5
        assert metrics.true_negatives == 2
        assert metrics.false_positives == 2

    def test_confusion_matrix_counts_are_exposed_and_sum_to_total(self):
        evaluator = ModelEvaluator()
        y_true = [0, 0, 1, 1, 1, 0]
        y_pred = [0, 1, 1, 0, 1, 0]
        y_proba = [0.1, 0.6, 0.9, 0.4, 0.8, 0.2]

        metrics = evaluator.evaluate(y_true, y_pred, y_proba)

        total = (
            metrics.true_positives
            + metrics.true_negatives
            + metrics.false_positives
            + metrics.false_negatives
        )
        assert total == len(y_true)
        assert metrics.true_positives == 2
        assert metrics.true_negatives == 2
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 1

    def test_metrics_round_trip_through_to_dict_and_from_dict(self):
        evaluator = ModelEvaluator()
        y_true = [0, 0, 1, 1]
        y_pred = [0, 1, 1, 1]
        y_proba = [0.1, 0.6, 0.7, 0.9]

        original = evaluator.evaluate(y_true, y_pred, y_proba)
        restored = ModelMetrics.from_dict(original.to_dict())

        assert restored == original

    def test_single_class_ground_truth_does_not_raise(self):
        evaluator = ModelEvaluator()
        y_true = [0, 0, 0, 0]
        y_pred = [0, 0, 0, 1]
        y_proba = [0.1, 0.1, 0.2, 0.3]

        metrics = evaluator.evaluate(y_true, y_pred, y_proba)

        # roc_auc_score is undefined with a single class present; the
        # evaluator must fall back gracefully rather than raising.
        assert metrics.roc_auc == 0.5

    def test_select_best_picks_highest_f1(self):
        low = EvaluationCandidate(
            model_name="low",
            metrics=ModelMetrics(0.6, 0.5, 0.5, 0.5, 0.6, 0.1),
        )
        high = EvaluationCandidate(
            model_name="high",
            metrics=ModelMetrics(0.9, 0.9, 0.9, 0.9, 0.95, 0.05),
        )

        winner = ModelEvaluator.select_best([low, high])

        assert winner.model_name == "high"

    def test_select_best_breaks_ties_with_lower_false_positive_rate(self):
        candidate_a = EvaluationCandidate(
            model_name="a",
            metrics=ModelMetrics(0.9, 0.9, 0.9, 0.9, 0.9, 0.10),
        )
        candidate_b = EvaluationCandidate(
            model_name="b",
            metrics=ModelMetrics(0.9, 0.9, 0.9, 0.9, 0.9, 0.02),
        )

        winner = ModelEvaluator.select_best([candidate_a, candidate_b])

        assert winner.model_name == "b"

    def test_select_best_on_empty_list_raises(self):
        import pytest

        with pytest.raises(ValueError):
            ModelEvaluator.select_best([])
