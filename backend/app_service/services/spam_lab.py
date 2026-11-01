"""Cross-domain SMS spam models from the capstone study (research/cross_domain).

Four scikit-learn pipelines (word TF-IDF + classifier) trained by the study's notebook:

    logistic_regression_word_baseline    trained on the UCI SMS Spam Collection only
    logistic_regression_word_adapted40   UCI + 40% of the Indian adaptation pool
    naive_bayes_word_baseline
    naive_bayes_word_adapted40

They are loaded once on first use and never retrained here. Input gets the same basic
cleaning as in the study (lowercase, collapse whitespace).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

import joblib

ARTIFACTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifacts", "cross_domain")

CLASSIFIERS = {"logistic_regression": "Logistic Regression", "naive_bayes": "Multinomial Naive Bayes"}
VERSIONS = {"baseline": "Baseline: trained on UCI only", "adapted40": "Adapted: UCI + 40% of the Indian adaptation pool"}


class UnknownModelError(ValueError):
    pass


def model_key(classifier: str, version: str) -> str:
    if classifier not in CLASSIFIERS or version not in VERSIONS:
        raise UnknownModelError(f"unknown model {classifier}/{version}")
    return f"{classifier}_word_{version}"


@lru_cache(maxsize=4)
def _load(key: str):
    return joblib.load(os.path.join(ARTIFACTS, f"{key}.joblib"))


@lru_cache(maxsize=1)
def results() -> dict:
    with open(os.path.join(ARTIFACTS, "results.json")) as fh:
        return json.load(fh)


def clean(text: str) -> str:
    return " ".join(text.lower().split())


def contributions(pipe, text: str, k: int = 8) -> list[dict]:
    """Features behind one prediction; positive pushes towards spam, negative towards ham.

    Logistic Regression: TF-IDF value x learned weight.
    Naive Bayes: TF-IDF value x (log P(feature | spam) - log P(feature | ham)).
    """
    vec, clf = pipe.named_steps["tfidf"], pipe.named_steps["clf"]
    x = vec.transform([text]).tocsr()
    names = vec.get_feature_names_out()
    weights = clf.feature_log_prob_[1] - clf.feature_log_prob_[0] if hasattr(clf, "feature_log_prob_") else clf.coef_[0]
    items = [(str(names[j]), float(x[0, j] * weights[j])) for j in x.indices]
    items.sort(key=lambda t: -abs(t[1]))
    return [{"feature": f, "contribution": round(c, 4)} for f, c in items[:k]]


def classify(text: str, classifier: str, version: str) -> dict:
    key = model_key(classifier, version)
    pipe = _load(key)
    cleaned = clean(text)
    p_spam = float(pipe.predict_proba([cleaned])[0, 1])
    info = results().get("saved_models", {}).get(key, {})
    return {
        "label": "spam" if p_spam >= 0.5 else "ham",
        "spam_probability": round(p_spam, 4),
        "model": {
            "id": key,
            "classifier": CLASSIFIERS[classifier],
            "version": VERSIONS[version],
            "features": "word TF-IDF (unigrams + bigrams, max 20,000)",
            "train_messages": info.get("train_messages"),
            "seed": info.get("seed"),
            "target_test_f1": info.get("target_test_f1"),
        },
        "top_features": contributions(pipe, cleaned),
    }


def study_summary() -> dict:
    """The study's measured results, for the dashboard (no message text)."""
    r = results()
    keep = ("seeds", "adapt_fractions", "hyperparameters", "dataset_statistics", "within_vs_cross",
            "adaptation_summary", "confusion_seed42", "group_aware", "nb_default_alpha", "saved_models")
    return {k: r.get(k) for k in keep}
