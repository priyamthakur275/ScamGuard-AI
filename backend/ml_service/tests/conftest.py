import os

import pytest
from fastapi.testclient import TestClient

from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry
from ml_service.inference.confidence import ConfidenceCalculator
from ml_service.inference.explainer import PredictionExplainer
from ml_service.inference.inference_engine import InferenceEngine
from ml_service.inference.threat_scorer import ThreatScorer
from ml_service.services.prediction_service import PredictionService

SAMPLE_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ml_training", "datasets", "sample_messages.csv"
)


@pytest.fixture()
def trained_registry_dir(tmp_path) -> str:
    """Trains a real (not mocked) model into a temporary registry.

    This is the ONLY place in the codebase where ml_service test code
    imports from ml_training -- a deliberate, test-only exception to the
    one-directional dependency rule, since test fixtures never ship in
    the deployed ml_service container.
    """
    from ml_training.config import TrainingConfig
    from ml_training.data.loader import DatasetLoader, DatasetSource, LoaderConfig
    from ml_training.data.validator import DatasetValidator
    from ml_training.evaluation.evaluator import ModelEvaluator
    from ml_training.training.train_pipeline import TrainingPipeline, default_trainers

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
    result = pipeline.run(version="test-v1")

    # Record which model won so tests can point PRODUCTION_MODEL_NAME at it.
    return artifacts_dir, result.winner.model_name


@pytest.fixture()
def loaded_inference_engine(trained_registry_dir) -> InferenceEngine:
    artifacts_dir, winning_model_name = trained_registry_dir
    registry = ModelRegistry(root_dir=artifacts_dir)
    engine = InferenceEngine(
        registry=registry,
        preprocessor=TextPreprocessingPipeline(),
        model_name=winning_model_name,
    )
    engine.load()
    return engine


@pytest.fixture()
def prediction_service(loaded_inference_engine) -> PredictionService:
    return PredictionService(
        engine=loaded_inference_engine,
        confidence_calculator=ConfidenceCalculator(),
        threat_scorer=ThreatScorer(),
        explainer=PredictionExplainer(),
    )


@pytest.fixture()
def client(trained_registry_dir):
    """A TestClient wired to a real trained model via environment
    variables, exercising the actual FastAPI lifespan startup path
    (including model loading) rather than bypassing it.
    """
    artifacts_dir, winning_model_name = trained_registry_dir

    os.environ["ARTIFACTS_DIR"] = artifacts_dir
    os.environ["PRODUCTION_MODEL_NAME"] = winning_model_name

    from ml_service.core.config import get_settings

    get_settings.cache_clear()

    # main module must be imported AFTER env vars are set, since Settings
    # are read (and cached) at import time.
    import importlib

    import ml_service.main as ml_main

    importlib.reload(ml_main)

    with TestClient(ml_main.app) as test_client:
        yield test_client

    get_settings.cache_clear()
