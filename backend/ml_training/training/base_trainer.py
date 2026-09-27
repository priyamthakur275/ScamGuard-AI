"""Model trainer abstraction (Strategy pattern).

`TrainingPipeline` depends only on this interface, never on a concrete
scikit-learn estimator. This is what satisfies the Open/Closed Principle
called out in the approved architecture: a future LSTM or transformer
trainer (per the roadmap's Phase 5) can be added as a new class
implementing `BaseModelTrainer` without touching the pipeline, the
evaluator, or the registry.
"""
from abc import ABC, abstractmethod
from typing import Any

from scipy.sparse import csr_matrix


class BaseModelTrainer(ABC):
    """Contract every trainable model (classical or deep) must satisfy."""

    #: Stable identifier used as the model's registry name and in
    #: comparison reports. Must be unique across trainers.
    name: str = "base"

    @abstractmethod
    def fit(self, features: csr_matrix, labels: list[int]) -> None:
        """Fit the underlying estimator on TF-IDF features and binary
        labels (1 = scam/spam/phishing, 0 = legitimate).
        """
        raise NotImplementedError

    @abstractmethod
    def predict(self, features: csr_matrix) -> Any:
        """Return hard class predictions (0/1) for the given features."""
        raise NotImplementedError

    @abstractmethod
    def predict_proba(self, features: csr_matrix) -> Any:
        """Return the predicted probability of the positive (scam) class
        for each row in `features`.
        """
        raise NotImplementedError

    @abstractmethod
    def get_estimator(self) -> Any:
        """Return the underlying fitted estimator, for serialization."""
        raise NotImplementedError
