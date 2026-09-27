"""Concrete classical-ML trainers.

Each class adapts a scikit-learn estimator to the `BaseModelTrainer`
interface. Deliberately thin: all four follow the identical
fit/predict/predict_proba shape, so the only thing that varies between
them is which estimator is constructed and with which hyperparameters --
exactly the kind of variation the Strategy pattern is meant to isolate.

LSTM is intentionally NOT implemented here. Per the approved architecture
(Section 8, ML Pipeline Architecture): "LSTM is kept as a benchmark/
challenger model and only promoted if it clears a defined latency SLA."
Because `BaseModelTrainer` is the only contract `TrainingPipeline` depends
on, an `LstmModelTrainer` (backed by TensorFlow/Keras) can be added later
as a pure addition -- no change to this file, the pipeline, the
evaluator, or the registry is required.
"""
from typing import Any

from scipy.sparse import csr_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC

from ml_training.config import (
    LogisticRegressionHyperparameters,
    NaiveBayesHyperparameters,
    RandomForestHyperparameters,
    SvmHyperparameters,
)
from ml_training.training.base_trainer import BaseModelTrainer


class NaiveBayesTrainer(BaseModelTrainer):
    name = "naive_bayes"

    def __init__(self, hyperparameters: NaiveBayesHyperparameters):
        self._estimator = MultinomialNB(alpha=hyperparameters.alpha)

    def fit(self, features: csr_matrix, labels: list[int]) -> None:
        self._estimator.fit(features, labels)

    def predict(self, features: csr_matrix) -> Any:
        return self._estimator.predict(features)

    def predict_proba(self, features: csr_matrix) -> Any:
        return self._estimator.predict_proba(features)[:, 1]

    def get_estimator(self) -> Any:
        return self._estimator


class LogisticRegressionTrainer(BaseModelTrainer):
    name = "logistic_regression"

    def __init__(self, hyperparameters: LogisticRegressionHyperparameters):
        self._estimator = LogisticRegression(
            C=hyperparameters.C,
            max_iter=hyperparameters.max_iter,
            class_weight=hyperparameters.class_weight,
        )

    def fit(self, features: csr_matrix, labels: list[int]) -> None:
        self._estimator.fit(features, labels)

    def predict(self, features: csr_matrix) -> Any:
        return self._estimator.predict(features)

    def predict_proba(self, features: csr_matrix) -> Any:
        return self._estimator.predict_proba(features)[:, 1]

    def get_estimator(self) -> Any:
        return self._estimator


class RandomForestTrainer(BaseModelTrainer):
    name = "random_forest"

    def __init__(self, hyperparameters: RandomForestHyperparameters):
        self._estimator = RandomForestClassifier(
            n_estimators=hyperparameters.n_estimators,
            max_depth=hyperparameters.max_depth,
            min_samples_leaf=hyperparameters.min_samples_leaf,
            class_weight=hyperparameters.class_weight,
            random_state=hyperparameters.random_state,
        )

    def fit(self, features: csr_matrix, labels: list[int]) -> None:
        self._estimator.fit(features, labels)

    def predict(self, features: csr_matrix) -> Any:
        return self._estimator.predict(features)

    def predict_proba(self, features: csr_matrix) -> Any:
        return self._estimator.predict_proba(features)[:, 1]

    def get_estimator(self) -> Any:
        return self._estimator


class SvmTrainer(BaseModelTrainer):
    name = "svm"

    def __init__(self, hyperparameters: SvmHyperparameters):
        self._estimator = SVC(
            C=hyperparameters.C,
            kernel=hyperparameters.kernel,
            probability=hyperparameters.probability,
            class_weight=hyperparameters.class_weight,
            random_state=hyperparameters.random_state,
        )

    def fit(self, features: csr_matrix, labels: list[int]) -> None:
        self._estimator.fit(features, labels)

    def predict(self, features: csr_matrix) -> Any:
        return self._estimator.predict(features)

    def predict_proba(self, features: csr_matrix) -> Any:
        return self._estimator.predict_proba(features)[:, 1]

    def get_estimator(self) -> Any:
        return self._estimator
