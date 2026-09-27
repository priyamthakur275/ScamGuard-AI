import pytest

from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_training.config import (
    LogisticRegressionHyperparameters,
    NaiveBayesHyperparameters,
    RandomForestHyperparameters,
    SvmHyperparameters,
)
from ml_training.training.classical_trainers import (
    LogisticRegressionTrainer,
    NaiveBayesTrainer,
    RandomForestTrainer,
    SvmTrainer,
)

TEXTS = [
    "urgent verify account now",
    "win free prize click now",
    "otp code required immediately",
    "hello how are you today",
    "lunch meeting scheduled tomorrow",
    "thanks for the document review",
] * 4
LABELS = [1, 1, 1, 0, 0, 0] * 4


@pytest.fixture()
def fitted_features():
    extractor = TfidfFeatureExtractor()
    matrix = extractor.fit_transform(TEXTS)
    return matrix, LABELS


TRAINER_FACTORIES = {
    "naive_bayes": lambda: NaiveBayesTrainer(NaiveBayesHyperparameters()),
    "logistic_regression": lambda: LogisticRegressionTrainer(LogisticRegressionHyperparameters()),
    "random_forest": lambda: RandomForestTrainer(RandomForestHyperparameters(n_estimators=20)),
    "svm": lambda: SvmTrainer(SvmHyperparameters()),
}


@pytest.mark.parametrize("trainer_name", list(TRAINER_FACTORIES.keys()))
class TestClassicalTrainers:
    def test_fit_does_not_raise(self, trainer_name, fitted_features):
        features, labels = fitted_features
        trainer = TRAINER_FACTORIES[trainer_name]()
        trainer.fit(features, labels)

    def test_predict_returns_correct_length(self, trainer_name, fitted_features):
        features, labels = fitted_features
        trainer = TRAINER_FACTORIES[trainer_name]()
        trainer.fit(features, labels)
        predictions = trainer.predict(features)
        assert len(predictions) == len(labels)

    def test_predict_proba_values_are_in_unit_interval(self, trainer_name, fitted_features):
        features, labels = fitted_features
        trainer = TRAINER_FACTORIES[trainer_name]()
        trainer.fit(features, labels)
        probabilities = trainer.predict_proba(features)
        assert all(0.0 <= p <= 1.0 for p in probabilities)

    def test_get_estimator_returns_fitted_object(self, trainer_name, fitted_features):
        features, labels = fitted_features
        trainer = TRAINER_FACTORIES[trainer_name]()
        trainer.fit(features, labels)
        estimator = trainer.get_estimator()
        assert estimator is not None
        assert hasattr(estimator, "predict")

    def test_name_is_set(self, trainer_name, fitted_features):
        trainer = TRAINER_FACTORIES[trainer_name]()
        assert trainer.name == trainer_name
