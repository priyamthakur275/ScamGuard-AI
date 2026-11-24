"""v2: optional Hindi/Hinglish model. The fixture is a tiny UNTRAINED model, used only to test the plumbing."""
import os

import pytest

from ml_service.inference import indic_model

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "indic_tiny")


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv("INDIC_MODEL_DIR", raising=False)
    monkeypatch.delenv("INDIC_MODEL_URL", raising=False)
    indic_model.reset_for_tests()
    yield
    indic_model.reset_for_tests()


def test_is_indic():
    assert indic_model.is_indic("आपका खाता बंद कर दिया जाएगा")
    assert indic_model.is_indic("Aapka account band ho jayega turant KYC karo")
    assert not indic_model.is_indic("Your SBI account is blocked, update KYC")
    assert not indic_model.is_indic("")


def test_off_by_default():
    assert indic_model.get_indic_model() is None


def test_bad_path_falls_back(monkeypatch):
    monkeypatch.setenv("INDIC_MODEL_DIR", "/nonexistent")
    assert indic_model.get_indic_model() is None


def test_loads_and_scores(monkeypatch):
    pytest.importorskip("onnxruntime")
    monkeypatch.setenv("INDIC_MODEL_DIR", FIXTURE)
    m = indic_model.get_indic_model()
    assert m is not None
    p = m.probability("आपका खाता बंद कर दिया जाएगा, तुरंत KYC करें")
    assert 0.0 <= p <= 1.0


def test_prediction_uses_indic_model_only_for_indic_text(monkeypatch):
    pytest.importorskip("onnxruntime")
    from app_service.services.message_service import get_in_process_prediction_service
    from ml_service.services.prediction_service import PredictionRequest

    class Fixed:
        def probability(self, text):
            return 0.99

    monkeypatch.setattr(indic_model, "get_indic_model", lambda: Fixed())
    svc = get_in_process_prediction_service()
    hindi = svc.predict(PredictionRequest(text="आपका बिजली कनेक्शन आज रात काट दिया जाएगा"))
    english = svc.predict(PredictionRequest(text="Your order has been delivered. Thank you for shopping."))
    assert hindi.model_name == indic_model.MODEL_NAME and hindi.scam_probability == 0.99
    assert english.model_name != indic_model.MODEL_NAME and english.verdict == "legitimate"
