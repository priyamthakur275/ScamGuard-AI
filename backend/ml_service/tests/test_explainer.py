import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_service.inference.explainer import ExplainerConfig, PredictionExplainer, UnsupportedEstimatorError

TEXTS = [
    "urgent verify account now",
    "win free prize click now",
    "hello how are you today",
    "lunch meeting scheduled tomorrow",
] * 5
LABELS = [1, 1, 0, 0] * 5


@pytest.fixture()
def fitted_vectorizer():
    extractor = TfidfFeatureExtractor()
    extractor.fit_transform(TEXTS)
    return extractor


class TestPredictionExplainer:
    def test_logistic_regression_returns_ranked_contributions(self, fitted_vectorizer):
        features = fitted_vectorizer.transform(TEXTS)
        model = LogisticRegression(max_iter=1000).fit(features, LABELS)

        explainer = PredictionExplainer(ExplainerConfig(top_n=3))
        message_features = fitted_vectorizer.transform(["urgent verify account now"])

        contributions = explainer.explain(
            estimator=model,
            feature_names=fitted_vectorizer.get_feature_names(),
            message_features=message_features,
        )

        assert len(contributions) <= 3
        # Contributions must be sorted descending by weight.
        weights = [c.weight for c in contributions]
        assert weights == sorted(weights, reverse=True)

    def test_naive_bayes_returns_contributions(self, fitted_vectorizer):
        features = fitted_vectorizer.transform(TEXTS)
        model = MultinomialNB().fit(features, LABELS)

        explainer = PredictionExplainer()
        message_features = fitted_vectorizer.transform(["urgent verify account now"])

        contributions = explainer.explain(
            estimator=model,
            feature_names=fitted_vectorizer.get_feature_names(),
            message_features=message_features,
        )

        assert isinstance(contributions, list)

    def test_unsupported_estimator_raises(self, fitted_vectorizer):
        class NotARealEstimator:
            pass

        explainer = PredictionExplainer()
        message_features = fitted_vectorizer.transform(["hello"])

        with pytest.raises(UnsupportedEstimatorError):
            explainer.explain(
                estimator=NotARealEstimator(),
                feature_names=fitted_vectorizer.get_feature_names(),
                message_features=message_features,
            )

    def test_random_forest_returns_contributions(self, fitted_vectorizer):
        features = fitted_vectorizer.transform(TEXTS)
        model = RandomForestClassifier(n_estimators=10, random_state=42).fit(features, LABELS)

        explainer = PredictionExplainer()
        message_features = fitted_vectorizer.transform(["urgent verify account now"])

        contributions = explainer.explain(
            estimator=model,
            feature_names=fitted_vectorizer.get_feature_names(),
            message_features=message_features,
        )

        assert isinstance(contributions, list)

    def test_top_n_is_respected(self, fitted_vectorizer):
        features = fitted_vectorizer.transform(TEXTS)
        model = LogisticRegression(max_iter=1000).fit(features, LABELS)

        explainer = PredictionExplainer(ExplainerConfig(top_n=1))
        message_features = fitted_vectorizer.transform(["urgent verify account now win prize"])

        contributions = explainer.explain(
            estimator=model,
            feature_names=fitted_vectorizer.get_feature_names(),
            message_features=message_features,
        )

        assert len(contributions) <= 1
