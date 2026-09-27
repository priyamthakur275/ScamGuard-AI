"""TF-IDF feature engineering (shared: used by both training and serving).

Per the approved ML Pipeline Architecture (Section 8): the vectorizer is
fit exactly once on training data, then frozen and versioned as a
first-class artifact alongside the model. This wrapper exists specifically
to make that frozen/versioned lifecycle explicit and to prevent accidental
re-fitting at inference time (the most common train/serve skew bug).
"""
from dataclasses import dataclass

import joblib
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer


class VectorizerNotFittedError(Exception):
    pass


@dataclass(frozen=True)
class TfidfConfig:
    max_features: int = 5000
    ngram_range: tuple[int, int] = (1, 2)
    min_df: int = 1
    max_df: float = 0.95
    sublinear_tf: bool = True


class TfidfFeatureExtractor:
    """Wraps scikit-learn's TfidfVectorizer with an explicit fit/frozen
    lifecycle and its own serialization, so the training pipeline and the
    inference engine both go through the same narrow interface.
    """

    def __init__(self, config: TfidfConfig | None = None):
        self._config = config or TfidfConfig()
        self._vectorizer = TfidfVectorizer(
            max_features=self._config.max_features,
            ngram_range=self._config.ngram_range,
            min_df=self._config.min_df,
            max_df=self._config.max_df,
            sublinear_tf=self._config.sublinear_tf,
        )
        self._is_fitted = False

    def fit_transform(self, preprocessed_texts: list[str]) -> csr_matrix:
        self._apply_small_corpus_safety(len(preprocessed_texts))
        matrix = self._vectorizer.fit_transform(preprocessed_texts)
        self._is_fitted = True
        return matrix

    def _apply_small_corpus_safety(self, document_count: int) -> None:
        """A fractional max_df (e.g. 0.95) combined with a very small
        corpus can compute an effective max-document-count below min_df,
        which scikit-learn rejects outright. Rather than let a small
        training batch crash the whole pipeline, widen max_df to 1.0 for
        corpora too small for the configured fraction to make sense.
        """
        max_df = self._vectorizer.max_df
        min_df = self._vectorizer.min_df
        if isinstance(max_df, float) and document_count > 0:
            effective_max_docs = max_df * document_count
            if effective_max_docs < min_df:
                self._vectorizer.max_df = 1.0

    def transform(self, preprocessed_texts: list[str]) -> csr_matrix:
        if not self._is_fitted:
            raise VectorizerNotFittedError(
                "TfidfFeatureExtractor.transform() called before fit_transform(). "
                "The vectorizer must be fit once during training and loaded "
                "(never re-fit) at inference time."
            )
        return self._vectorizer.transform(preprocessed_texts)

    def get_feature_names(self) -> list[str]:
        if not self._is_fitted:
            raise VectorizerNotFittedError("Vectorizer has not been fitted yet")
        return list(self._vectorizer.get_feature_names_out())

    def save(self, path: str) -> None:
        if not self._is_fitted:
            raise VectorizerNotFittedError("Cannot save a vectorizer that has not been fitted")
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "TfidfFeatureExtractor":
        loaded = joblib.load(path)
        if not isinstance(loaded, TfidfFeatureExtractor):
            raise TypeError(f"Artifact at '{path}' is not a TfidfFeatureExtractor")
        return loaded

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def vocabulary_size(self) -> int:
        return len(self.get_feature_names())
