"""The training pipeline orchestrator.

This is the Section 8 "Offline (training) pipeline" from the approved
architecture, implemented as a single composition root. Every dependency
(loader, validator, preprocessor, vectorizer, trainers, evaluator,
registry) is injected through the constructor rather than constructed
internally -- Dependency Injection -- so the pipeline itself contains no
business logic beyond sequencing, and every stage can be unit-tested or
swapped independently.
"""
import tempfile
from dataclasses import dataclass

import joblib
from sklearn.model_selection import train_test_split

from ml_common.domain.value_objects import ModelMetrics
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry
from ml_training.config import TrainingConfig
from ml_training.data.loader import DatasetLoader
from ml_training.data.validator import DatasetValidator
from ml_training.evaluation.evaluator import EvaluationCandidate, ModelEvaluator
from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_training.training.base_trainer import BaseModelTrainer
from ml_training.training.classical_trainers import (
    LogisticRegressionTrainer,
    NaiveBayesTrainer,
    RandomForestTrainer,
    SvmTrainer,
)


@dataclass(frozen=True)
class TrainingRunResult:
    """Summary of one completed training run, returned to the caller
    (CLI, CI job, or a future orchestration service) for logging/reporting.
    """

    version: str
    candidates: list[EvaluationCandidate]
    winner: EvaluationCandidate
    vocabulary_size: int
    train_rows: int
    test_rows: int


def default_trainers(config: TrainingConfig) -> list[BaseModelTrainer]:
    """Factory for the standard set of classical trainers compared on
    every run. Kept as a free function (not a hardcoded list inside the
    pipeline) so a caller can inject a different/extended trainer set --
    e.g. adding an LSTM trainer later -- without modifying the pipeline.
    """
    return [
        NaiveBayesTrainer(config.naive_bayes),
        LogisticRegressionTrainer(config.logistic_regression),
        RandomForestTrainer(config.random_forest),
        SvmTrainer(config.svm),
    ]


class TrainingPipeline:
    def __init__(
        self,
        config: TrainingConfig,
        loader: DatasetLoader,
        validator: DatasetValidator,
        preprocessor: TextPreprocessingPipeline,
        vectorizer: TfidfFeatureExtractor,
        trainers: list[BaseModelTrainer],
        evaluator: ModelEvaluator,
        registry: ModelRegistry,
    ):
        self._config = config
        self._loader = loader
        self._validator = validator
        self._preprocessor = preprocessor
        self._vectorizer = vectorizer
        self._trainers = trainers
        self._evaluator = evaluator
        self._registry = registry

    def run(self, version: str, promote_winner: bool = True) -> TrainingRunResult:
        # 1. Load
        dataset = self._loader.load()

        # 2. Validate
        self._validator.validate(dataset)

        # 3. Preprocess (identical pipeline object serving will use)
        processed_texts = self._preprocessor.process_batch(dataset["text"].tolist())
        binary_labels = [
            1 if label in self._config.positive_labels else 0 for label in dataset["label"]
        ]

        # 4. Split
        x_train, x_test, y_train, y_test = train_test_split(
            processed_texts,
            binary_labels,
            test_size=self._config.test_size,
            random_state=self._config.random_state,
            stratify=binary_labels,
        )

        # 5. Feature extraction — fit ONCE on training data only
        train_features = self._vectorizer.fit_transform(x_train)
        test_features = self._vectorizer.transform(x_test)

        # 6. Train + evaluate every candidate
        candidates: list[EvaluationCandidate] = []
        for trainer in self._trainers:
            trainer.fit(train_features, y_train)
            predictions = trainer.predict(test_features)
            probabilities = trainer.predict_proba(test_features)
            metrics = self._evaluator.evaluate(y_test, predictions, probabilities)
            candidates.append(EvaluationCandidate(model_name=trainer.name, metrics=metrics))

        # 7. Select winner
        winner = self._evaluator.select_best(candidates)
        winning_trainer = next(t for t in self._trainers if t.name == winner.model_name)

        # 8. Serialize + register
        self._register(winning_trainer, winner.metrics, version, train_rows=len(x_train), test_rows=len(x_test))
        if promote_winner:
            self._registry.promote(winner.model_name, version)

        return TrainingRunResult(
            version=version,
            candidates=candidates,
            winner=winner,
            vocabulary_size=self._vectorizer.vocabulary_size,
            train_rows=len(x_train),
            test_rows=len(x_test),
        )

    def _register(
        self, trainer: BaseModelTrainer, metrics: ModelMetrics, version: str, train_rows: int, test_rows: int
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = f"{tmp_dir}/model.joblib"
            vectorizer_path = f"{tmp_dir}/vectorizer.joblib"

            joblib.dump(trainer.get_estimator(), model_path)
            self._vectorizer.save(vectorizer_path)

            self._registry.register(
                model_name=trainer.name,
                version=version,
                local_model_path=model_path,
                local_vectorizer_path=vectorizer_path,
                metrics=metrics,
                train_rows=train_rows,
                test_rows=test_rows,
            )
