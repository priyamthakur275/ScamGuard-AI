"""Training-run configuration.

All hyperparameters and pipeline knobs live here, in one place, instead
of being scattered as magic numbers through the training modules. This is
what step 10 ("Hyperparameter configuration") in the approved plan refers
to: a single, explicit, versionable configuration object per training run.
"""
from dataclasses import dataclass, field

from ml_common.features.tfidf_vectorizer import TfidfConfig


@dataclass(frozen=True)
class NaiveBayesHyperparameters:
    alpha: float = 1.0


@dataclass(frozen=True)
class LogisticRegressionHyperparameters:
    C: float = 1.0
    max_iter: int = 1000
    class_weight: str | None = "balanced"


@dataclass(frozen=True)
class RandomForestHyperparameters:
    n_estimators: int = 200
    max_depth: int | None = 20
    min_samples_leaf: int = 2
    class_weight: str | None = "balanced"
    random_state: int = 42


@dataclass(frozen=True)
class SvmHyperparameters:
    C: float = 1.0
    kernel: str = "linear"
    probability: bool = True
    class_weight: str | None = "balanced"
    random_state: int = 42


@dataclass(frozen=True)
class TrainingConfig:
    """Top-level configuration for one full training run."""

    test_size: float = 0.2
    random_state: int = 42
    positive_labels: frozenset[str] = field(
        default_factory=lambda: frozenset({"scam", "phishing", "spam"})
    )

    tfidf: TfidfConfig = field(default_factory=TfidfConfig)
    naive_bayes: NaiveBayesHyperparameters = field(default_factory=NaiveBayesHyperparameters)
    logistic_regression: LogisticRegressionHyperparameters = field(
        default_factory=LogisticRegressionHyperparameters
    )
    random_forest: RandomForestHyperparameters = field(default_factory=RandomForestHyperparameters)
    svm: SvmHyperparameters = field(default_factory=SvmHyperparameters)

    artifacts_dir: str = "artifacts"
