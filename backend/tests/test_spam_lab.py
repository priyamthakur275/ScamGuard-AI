"""The cross-domain study's models, as served by the public API."""
import os

import pandas as pd
import pytest
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

from app_service.services import spam_lab

PROMO = "CONGRATULATIONS! FREE 2GB data is yours! Claim on Airtel Thanks App Now. Hurry i.airtel.in/e/csl_ml_2GB"
CHAT = "Around 2 pm I will join the meeting, see you there"
STUDY = os.path.join(os.path.dirname(__file__), "..", "..", "research", "cross_domain")


@pytest.mark.parametrize("classifier", ["logistic_regression", "naive_bayes"])
@pytest.mark.parametrize("version", ["baseline", "adapted40"])
def test_classify_returns_label_probability_model_and_features(client, classifier, version):
    r = client.post("/api/v1/public/cross-domain/classify", json={"text": CHAT, "classifier": classifier, "version": version})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["label"] == "ham"
    assert 0 <= body["spam_probability"] < 0.5
    assert body["model"]["id"] == f"{classifier}_word_{version}"
    assert body["model"]["train_messages"] > 4000
    assert isinstance(body["top_features"], list)


def test_adapted_model_is_more_confident_on_indian_promotion(client):
    base = client.post("/api/v1/public/cross-domain/classify", json={"text": PROMO, "version": "baseline"}).json()
    adapted = client.post("/api/v1/public/cross-domain/classify", json={"text": PROMO, "version": "adapted40"}).json()
    assert adapted["label"] == "spam"
    assert adapted["spam_probability"] > base["spam_probability"]
    assert any(f["contribution"] > 0 for f in adapted["top_features"])


def test_classify_rejects_bad_input(client):
    url = "/api/v1/public/cross-domain/classify"
    assert client.post(url, json={"text": ""}).status_code == 422
    assert client.post(url, json={"text": "   "}).status_code == 422
    assert client.post(url, json={"text": "a" * 2001}).status_code == 422
    assert client.post(url, json={"text": "hi", "classifier": "random_forest"}).status_code == 422


def test_results_endpoint_returns_the_measured_study(client):
    body = client.get("/api/v1/public/cross-domain/results").json()
    assert body["seeds"] == [42, 123, 2026]
    assert {r["Test domain"] for r in body["within_vs_cross"]} == {"Source A", "Target B"}
    assert len(body["confusion_seed42"]) == 4
    assert "message" not in str(body.get("adaptation_summary"))


@pytest.mark.skipif(not os.path.exists(os.path.join(STUDY, "data", "clean", "dataset_B_india_clean.csv")), reason="study data not present")
def test_served_models_reproduce_the_notebook_numbers():
    """The files the API serves give exactly the F1 the notebook recorded on its final target test set."""
    b = pd.read_csv(os.path.join(STUDY, "data", "clean", "dataset_B_india_clean.csv"))
    _, test = train_test_split(b, test_size=0.30, stratify=b["label"], random_state=42)
    saved = spam_lab.results()["saved_models"]
    for key, info in saved.items():
        pipe = spam_lab._load(key)
        assert f1_score(test["label"], pipe.predict(test["message"])) == pytest.approx(info["target_test_f1"], abs=1e-9)
