"""Integration test for the full offline training pipeline.

Unlike the unit tests, nothing here is mocked: a real dataset is loaded
from disk, real preprocessing runs, a real TF-IDF vectorizer is fit, all
four classical models are really trained and evaluated, and real
artifacts are written to a temporary registry -- then reloaded from disk
in a fresh registry instance to prove persistence actually works, not
just in-memory state.
"""
import os

import joblib
import pytest

from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry
from ml_training.config import TrainingConfig
from ml_training.data.loader import DatasetLoader, DatasetSource, LoaderConfig
from ml_training.data.validator import DatasetValidator
from ml_training.evaluation.evaluator import ModelEvaluator
from ml_training.training.train_pipeline import TrainingPipeline, default_trainers

SAMPLE_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "datasets", "sample_messages.csv"
)


@pytest.fixture()
def pipeline(tmp_path) -> TrainingPipeline:
    config = TrainingConfig(artifacts_dir=str(tmp_path / "artifacts"), test_size=0.3)
    return TrainingPipeline(
        config=config,
        loader=DatasetLoader(LoaderConfig(sources=[DatasetSource(path=SAMPLE_DATASET_PATH)])),
        validator=DatasetValidator(),
        preprocessor=TextPreprocessingPipeline(),
        vectorizer=TfidfFeatureExtractor(config.tfidf),
        trainers=default_trainers(config),
        evaluator=ModelEvaluator(),
        registry=ModelRegistry(root_dir=str(tmp_path / "artifacts")),
    )


class TestTrainingPipelineIntegration:
    def test_full_run_trains_and_compares_all_four_classical_models(self, pipeline):
        result = pipeline.run(version="it-v1")

        model_names = {c.model_name for c in result.candidates}
        assert model_names == {"naive_bayes", "logistic_regression", "random_forest", "svm"}

    def test_full_run_produces_a_positive_vocabulary(self, pipeline):
        result = pipeline.run(version="it-v1")
        assert result.vocabulary_size > 0

    def test_full_run_splits_train_and_test_sets(self, pipeline):
        result = pipeline.run(version="it-v1")
        assert result.train_rows > 0
        assert result.test_rows > 0

    def test_winner_is_registered_and_loadable_from_a_fresh_registry(self, tmp_path):
        artifacts_dir = str(tmp_path / "artifacts")
        config = TrainingConfig(artifacts_dir=artifacts_dir, test_size=0.3)

        pipeline = TrainingPipeline(
            config=config,
            loader=DatasetLoader(LoaderConfig(sources=[DatasetSource(path=SAMPLE_DATASET_PATH)])),
            validator=DatasetValidator(),
            preprocessor=TextPreprocessingPipeline(),
            vectorizer=TfidfFeatureExtractor(config.tfidf),
            trainers=default_trainers(config),
            evaluator=ModelEvaluator(),
            registry=ModelRegistry(root_dir=artifacts_dir),
        )
        result = pipeline.run(version="it-v2")

        # Fresh registry instance -> proves state was actually persisted
        # to disk, not just held in the original registry object.
        fresh_registry = ModelRegistry(root_dir=artifacts_dir)
        production_info = fresh_registry.get_production(result.winner.model_name)

        assert production_info.version == "it-v2"
        assert production_info.is_production is True

        model_path, vectorizer_path = fresh_registry.resolve_artifact_paths(production_info)
        loaded_model = joblib.load(model_path)
        loaded_vectorizer = TfidfFeatureExtractor.load(vectorizer_path)

        assert hasattr(loaded_model, "predict")
        assert loaded_vectorizer.is_fitted is True

    def test_trained_model_scores_an_obvious_scam_higher_than_legitimate_text(self, tmp_path):
        artifacts_dir = str(tmp_path / "artifacts")
        config = TrainingConfig(artifacts_dir=artifacts_dir, test_size=0.3)
        preprocessor = TextPreprocessingPipeline()

        pipeline = TrainingPipeline(
            config=config,
            loader=DatasetLoader(LoaderConfig(sources=[DatasetSource(path=SAMPLE_DATASET_PATH)])),
            validator=DatasetValidator(),
            preprocessor=preprocessor,
            vectorizer=TfidfFeatureExtractor(config.tfidf),
            trainers=default_trainers(config),
            evaluator=ModelEvaluator(),
            registry=ModelRegistry(root_dir=artifacts_dir),
        )
        result = pipeline.run(version="it-v3")

        registry = ModelRegistry(root_dir=artifacts_dir)
        production_info = registry.get_production(result.winner.model_name)
        model_path, vectorizer_path = registry.resolve_artifact_paths(production_info)

        model = joblib.load(model_path)
        vectorizer = TfidfFeatureExtractor.load(vectorizer_path)

        scam_text = preprocessor.process(
            "URGENT! Your bank account will be blocked. Verify your OTP immediately to claim your prize."
        )
        legit_text = preprocessor.process("Hey, are we still on for lunch this Friday?")

        scam_probability = model.predict_proba(vectorizer.transform([scam_text]))[0][1]
        legit_probability = model.predict_proba(vectorizer.transform([legit_text]))[0][1]

        assert scam_probability > legit_probability
