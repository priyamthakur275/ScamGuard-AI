"""Explainability: top contributing words/features (step 19).

Per the approved architecture's ML Pipeline design: "for linear models
(LR/SVM), surface top-weighted TF-IDF tokens... cheap, and satisfies the
report's 'suspicious keyword' output requirement without needing SHAP."
This module generalizes that idea to every model type the training
pipeline produces (Naive Bayes, tree ensembles included) via a small
per-estimator-type weight extraction strategy, so explainability is not
tied to whichever model happens to be promoted to production.
"""
from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC

from ml_common.domain.value_objects import FeatureContribution


class UnsupportedEstimatorError(Exception):
    pass


def _feature_weights_for(estimator) -> np.ndarray:
    """Returns a 1D array of per-feature weights indicating each
    feature's contribution toward the positive (scam) class. Positive
    values push toward "scam", negative (or near-zero) push toward
    "legitimate".
    """
    if isinstance(estimator, (LogisticRegression,)):
        return estimator.coef_[0]

    if isinstance(estimator, SVC) and estimator.kernel == "linear":
        return np.asarray(estimator.coef_.todense())[0] if hasattr(estimator.coef_, "todense") else estimator.coef_[0]

    if isinstance(estimator, MultinomialNB):
        # Log-likelihood ratio of each feature under class 1 vs class 0 --
        # the natural analogue of a linear coefficient for Naive Bayes.
        return estimator.feature_log_prob_[1] - estimator.feature_log_prob_[0]

    if isinstance(estimator, RandomForestClassifier):
        # Tree ensembles have no signed direction per feature, only
        # unsigned importance. We still surface the highest-importance
        # tokens present in the message; direction is implied by the
        # message having been classified as scam in the first place.
        return estimator.feature_importances_

    raise UnsupportedEstimatorError(
        f"No explainability strategy registered for estimator type {type(estimator).__name__}"
    )


@dataclass(frozen=True)
class ExplainerConfig:
    top_n: int = 5
    min_weight_threshold: float = 0.0


class PredictionExplainer:
    """Surfaces the top-N tokens (present in the scored message) that
    contributed most toward the model's verdict.
    """

    def __init__(self, config: ExplainerConfig | None = None):
        self._config = config or ExplainerConfig()

    def explain(
        self,
        estimator,
        feature_names: list[str],
        message_features: csr_matrix,
    ) -> list[FeatureContribution]:
        feature_weights = _feature_weights_for(estimator)

        row = message_features.tocoo()
        contributions: list[tuple[str, float]] = []

        for feature_index, tfidf_value in zip(row.col, row.data):
            weight = float(feature_weights[feature_index]) * float(tfidf_value)
            if weight > self._config.min_weight_threshold:
                contributions.append((feature_names[feature_index], weight))

        contributions.sort(key=lambda item: item[1], reverse=True)
        top = contributions[: self._config.top_n]

        return [FeatureContribution(token=token, weight=round(weight, 6)) for token, weight in top]
