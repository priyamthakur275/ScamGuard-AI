import pytest

from ml_common.features.tfidf_vectorizer import (
    TfidfConfig,
    TfidfFeatureExtractor,
    VectorizerNotFittedError,
)


class TestTfidfFeatureExtractor:
    def test_transform_before_fit_raises(self):
        extractor = TfidfFeatureExtractor()
        with pytest.raises(VectorizerNotFittedError):
            extractor.transform(["some text"])

    def test_fit_transform_marks_as_fitted(self):
        extractor = TfidfFeatureExtractor()
        extractor.fit_transform(["urgent payment", "hello friend"])
        assert extractor.is_fitted is True

    def test_fit_transform_returns_correct_shape(self):
        extractor = TfidfFeatureExtractor()
        matrix = extractor.fit_transform(["urgent payment now", "hello my friend"])
        assert matrix.shape[0] == 2

    def test_transform_after_fit_uses_frozen_vocabulary(self):
        extractor = TfidfFeatureExtractor()
        extractor.fit_transform(["urgent payment now"])
        vocab_before = set(extractor.get_feature_names())

        # Transforming new text must NOT change the vocabulary.
        extractor.transform(["a completely different sentence entirely"])
        vocab_after = set(extractor.get_feature_names())

        assert vocab_before == vocab_after

    def test_get_feature_names_before_fit_raises(self):
        extractor = TfidfFeatureExtractor()
        with pytest.raises(VectorizerNotFittedError):
            extractor.get_feature_names()

    def test_save_before_fit_raises(self, tmp_path):
        extractor = TfidfFeatureExtractor()
        with pytest.raises(VectorizerNotFittedError):
            extractor.save(str(tmp_path / "vec.joblib"))

    def test_save_and_load_round_trip(self, tmp_path):
        extractor = TfidfFeatureExtractor(TfidfConfig(max_features=50))
        extractor.fit_transform(["urgent payment now", "hello my friend"])

        save_path = str(tmp_path / "vectorizer.joblib")
        extractor.save(save_path)

        loaded = TfidfFeatureExtractor.load(save_path)
        assert loaded.is_fitted is True
        assert loaded.get_feature_names() == extractor.get_feature_names()

        # The loaded vectorizer must reproduce identical transforms.
        original_matrix = extractor.transform(["urgent payment"])
        loaded_matrix = loaded.transform(["urgent payment"])
        assert (original_matrix != loaded_matrix).nnz == 0

    def test_vocabulary_size_respects_max_features(self):
        extractor = TfidfFeatureExtractor(TfidfConfig(max_features=3))
        extractor.fit_transform(
            ["alpha beta gamma delta epsilon zeta eta theta iota kappa"]
        )
        assert extractor.vocabulary_size <= 3
