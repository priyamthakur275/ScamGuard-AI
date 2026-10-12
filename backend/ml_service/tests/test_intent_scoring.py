"""Intent-based risk engine: scams are judged by what they ask you to do,
and genuine notices that merely mention OTP/bank/account stay low."""
from pathlib import Path

import pandas as pd
import pytest

from ml_service.inference.threat_scorer import ThreatScorer

S = ThreatScorer()


@pytest.mark.parametrize("text", [
    "Sir I am from SBI, your card is blocked, tell me the OTP you received now.",
    "Download AnyDesk and read out the code to get your refund.",
    "You are under digital arrest. Stay on the video call and do not tell anyone.",
    "Pay registration fee Rs 1500 to confirm your work from home job.",
])
def test_scam_intent_lifts_an_unsure_model(text):
    assert S.assess(0.3, text.lower().split(), text).threat_score >= 0.8


@pytest.mark.parametrize("text", [
    "482913 is your OTP for the HDFC transaction. Do not share it with anyone.",
    "Rs 2,450 debited from a/c XX4821. Not you? Call the official helpline on the back of your card.",
    "Your salary of Rs 45,000 has been credited to your account.",
])
def test_genuine_notices_are_pulled_down(text):
    assert S.assess(0.6, text.lower().split(), text).threat_score < 0.5


def test_topic_words_alone_do_not_flag():
    text = "Your bank account statement for September is ready."
    assert S.assess(0.1, text.lower().split(), text).threat_score < 0.2


def test_unseen_challenge_set_accuracy_does_not_regress():
    """Guards the honest hold-out number reported in the datasets README."""
    from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
    from ml_common.registry.model_registry import ModelRegistry
    from ml_service.inference.inference_engine import InferenceEngine

    root = Path(__file__).resolve().parents[2]
    engine = InferenceEngine(ModelRegistry(root_dir=str(root / "artifacts")), TextPreprocessingPipeline(), "svm")
    engine.load()
    df = pd.read_csv(root / "ml_training" / "datasets" / "indian_challenge_set_b.csv")
    correct = 0
    for text, label in zip(df.text, df.label):
        p = engine.predict(text).scam_probability
        tokens, _ = engine.transform(text)
        correct += (S.assess(p, tokens, text).threat_score >= 0.5) == (label == "scam")
    assert correct / len(df) >= 0.85
