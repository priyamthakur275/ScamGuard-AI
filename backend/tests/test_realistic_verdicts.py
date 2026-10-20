"""Final-verdict regression tests on realistic Indian messages.

Added after a genuine Airtel 'report spam to 1909' notice was flagged at 100%.
Every genuine message here must be judged legitimate and every scam must be
flagged, by the real model plus the intent engine (no mocks)."""
import pytest

from app_service.services.message_service import get_in_process_prediction_service
from ml_service.services.prediction_service import PredictionRequest
from tests.data import final_check_messages, heldout_messages, realistic_messages

GENUINE = realistic_messages.GENUINE + heldout_messages.GENUINE + final_check_messages.GENUINE
SCAM = realistic_messages.SCAM + heldout_messages.SCAM + final_check_messages.SCAM


def _verdict(text: str):
    return get_in_process_prediction_service().predict(PredictionRequest(text=text, input_type="TEXT", metadata=None))


@pytest.mark.parametrize("text", GENUINE, ids=[t[:40] for t in GENUINE])
def test_genuine_message_is_legitimate(text):
    r = _verdict(text)
    assert r.verdict == "legitimate", f"flagged at {r.threat_score:.2f}: {text}"


@pytest.mark.parametrize("text", SCAM, ids=[t[:40] for t in SCAM])
def test_scam_message_is_flagged(text):
    r = _verdict(text)
    assert r.verdict != "legitimate", f"missed at {r.threat_score:.2f}: {text}"
