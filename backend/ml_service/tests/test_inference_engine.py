import pytest

from ml_service.inference.inference_engine import InferenceEngine, InferenceEngineNotReadyError


class TestInferenceEngine:
    def test_predict_before_load_raises(self, trained_registry_dir):
        from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
        from ml_common.registry.model_registry import ModelRegistry

        artifacts_dir, model_name = trained_registry_dir
        engine = InferenceEngine(
            registry=ModelRegistry(root_dir=artifacts_dir),
            preprocessor=TextPreprocessingPipeline(),
            model_name=model_name,
        )

        with pytest.raises(InferenceEngineNotReadyError):
            engine.predict("hello")

    def test_is_ready_false_before_load(self, trained_registry_dir):
        from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
        from ml_common.registry.model_registry import ModelRegistry

        artifacts_dir, model_name = trained_registry_dir
        engine = InferenceEngine(
            registry=ModelRegistry(root_dir=artifacts_dir),
            preprocessor=TextPreprocessingPipeline(),
            model_name=model_name,
        )
        assert engine.is_ready is False

    def test_is_ready_true_after_load(self, loaded_inference_engine):
        assert loaded_inference_engine.is_ready is True

    def test_predict_returns_probability_in_unit_interval(self, loaded_inference_engine):
        result = loaded_inference_engine.predict("Urgent verify your account now")
        assert 0.0 <= result.scam_probability <= 1.0

    def test_predict_returns_model_metadata(self, loaded_inference_engine):
        result = loaded_inference_engine.predict("hello")
        assert result.model_name
        assert result.model_version

    def test_transform_returns_tokens_and_features(self, loaded_inference_engine):
        tokens, features = loaded_inference_engine.transform("Urgent verify account now")
        assert isinstance(tokens, list)
        assert features.shape[0] == 1

    def test_version_info_before_load_raises(self, trained_registry_dir):
        from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
        from ml_common.registry.model_registry import ModelRegistry

        artifacts_dir, model_name = trained_registry_dir
        engine = InferenceEngine(
            registry=ModelRegistry(root_dir=artifacts_dir),
            preprocessor=TextPreprocessingPipeline(),
            model_name=model_name,
        )
        with pytest.raises(InferenceEngineNotReadyError):
            _ = engine.version_info

    def test_reload_refreshes_state(self, loaded_inference_engine):
        loaded_inference_engine.reload()
        assert loaded_inference_engine.is_ready is True
