"""TrustLens: behaviour tests. Verdicts come from the real model and are not
assumed; tests check that TrustLens reports the pipeline's evidence faithfully."""
from unittest.mock import patch

from app_service.services.message_service import get_in_process_prediction_service
from app_service.services.trustlens import build_trustlens
from ml_service.services.prediction_service import PredictionRequest

OTP_REQUEST = "Dear customer your SBI account will be blocked today. Share the OTP sent to your phone to keep it active."
OTP_WARNING = "482913 is your OTP for login. Do not share this OTP with anyone. SBI never asks for your OTP."
URGENCY_ONLY = "Reminder: the library closes today at 6 pm. Return your books before the deadline."
BANK_ALERT = "Rs 2,500.00 debited from A/c XX4821 on 12-10-26 to UPI/ramesh.kirana. Avl bal Rs 18,240.50. Not you? Call the number on the back of your card."
CONFLICT = "Never share your OTP with anyone. To avoid suspension, share the OTP sent to your mobile with our verification officer today."
UNFAMILIAR = "ok see you there"


def _report(text, xray="auto"):
    r = get_in_process_prediction_service().predict(PredictionRequest(text=text, input_type="TEXT", metadata=None))
    tl = build_trustlens(text=text, verdict=r.verdict, scam_probability=r.scam_probability, threat_score=r.threat_score,
                         risk_level=r.risk_level, xray=None if xray == "auto" else xray)
    return r, tl


def _stage(tl, key):
    return next(j for j in tl["journey"] if j["stage"] == key)


def test_scores_are_the_pipelines_own_and_kept_separate():
    r, tl = _report(OTP_REQUEST)
    assert tl["classifier_probability"] == round(r.scam_probability, 4)
    assert tl["risk_score"] == round(r.threat_score, 4)
    assert tl["verdict"] == r.verdict and tl["risk_level"] == r.risk_level
    assert [j["stage"] for j in tl["journey"]] == ["hook", "pressure", "ask", "cashout"]


def test_explicit_otp_request():
    _r, tl = _report(OTP_REQUEST)
    asks = [e for e in tl["evidence_for"] if e["intent"] == "asks_for_secret"]
    assert asks and asks[0]["phrase"] and asks[0]["why"] and asks[0]["stage"] == "ask"
    assert _stage(tl, "ask")["detected"] and _stage(tl, "pressure")["detected"]
    assert any(x["id"] == "secret" for x in tl["recommendations"])


def test_protective_warning_is_not_a_red_flag():
    _r, tl = _report(OTP_WARNING)
    assert not any(e["intent"] == "asks_for_secret" for e in tl["evidence_for"])
    assert any(e["pattern"] == "warns_not_to_share" and e["phrase"] for e in tl["evidence_against"])
    assert not _stage(tl, "ask")["detected"]


def test_urgency_without_a_request_only_marks_pressure():
    _r, tl = _report(URGENCY_ONLY)
    assert _stage(tl, "pressure")["detected"]
    assert not _stage(tl, "ask")["detected"] and not _stage(tl, "cashout")["detected"]
    assert not any(x["id"] in ("secret", "money", "collect") for x in tl["recommendations"])


def test_genuine_bank_notification():
    r, tl = _report(BANK_ALERT)
    assert tl["genuine_transaction"] is True or tl["evidence_against"]
    if r.verdict == "legitimate":
        assert not any(x["id"] == "report" for x in tl["recommendations"])


def test_conflicting_evidence_is_flagged():
    _r, tl = _report(CONFLICT)
    if tl["evidence_for"] and tl["evidence_against"]:
        assert tl["uncertainty"]["conflicting"] is True
        assert any("mixes scam signs" in m for m in tl["uncertainty"]["may_be_wrong"])
        assert "mixed" in tl["summary"]


def test_unfamiliar_message_reports_insufficient_evidence():
    _r, tl = _report(UNFAMILIAR)
    assert tl["evidence_for"] == [] and tl["evidence_against"] == []
    assert tl["uncertainty"]["insufficient"] is True
    assert any("classifier" in m for m in tl["uncertainty"]["may_be_wrong"])
    assert all(not j["detected"] for j in tl["journey"])


def test_malformed_xray_is_recomputed():
    _r, good = _report(OTP_REQUEST)
    for bad in ({"spans": "nope"}, {"spans": [{"start": "x", "end": 3, "stage": "ask"}, {"start": 0, "end": 999, "stage": "ask"}]}, "garbage"):
        _r, tl = _report(OTP_REQUEST, xray=bad)
        if isinstance(bad, dict) and isinstance(bad.get("spans"), list):
            assert tl["evidence_for"] == []  # invalid spans are dropped, never shown
        else:
            assert tl["evidence_for"] == good["evidence_for"]


def test_retrieval_unavailable_keeps_the_verdict():
    r, normal = _report(OTP_REQUEST)
    with patch("app_service.rag.retriever.get_retriever", side_effect=RuntimeError("index missing")):
        _r, tl = _report(OTP_REQUEST)
    assert tl["similar_pattern"] == {"status": "unavailable", "match": None, "genuine_match": None}
    assert tl["verdict"] == normal["verdict"] == r.verdict and tl["risk_score"] == normal["risk_score"]


def test_similar_pattern_only_shown_when_accepted():
    _r, tl = _report(OTP_REQUEST)
    sp = tl["similar_pattern"]
    if sp["status"] == "match":
        assert sp["match"]["source_url"].startswith("https://") and sp["match"]["title"]
    else:
        assert sp["match"] is None
    _r, tl = _report(UNFAMILIAR)
    assert tl["similar_pattern"]["match"] is None


def test_api_adds_trustlens_without_changing_existing_fields(client):
    res = client.post("/api/v1/public/quick-check", json={"text": OTP_REQUEST})
    body = res.json()
    assert res.status_code == 200
    for key in ("verdict", "scam_probability", "threat_score", "risk_level", "top_contributing_tokens", "metadata"):
        assert key in body
    assert "xray" in body["metadata"]
    tl = body["metadata"]["trustlens"]
    assert tl["verdict"] == body["verdict"] and tl["risk_score"] == round(body["threat_score"], 4)
    assert tl["disclaimer"]


def test_trustlens_failure_does_not_break_analysis(client):
    with patch("app_service.services.trustlens.build_trustlens", side_effect=RuntimeError("boom")):
        res = client.post("/api/v1/public/quick-check", json={"text": OTP_REQUEST})
    assert res.status_code == 200 and "trustlens" not in res.json()["metadata"] and res.json()["verdict"]


def test_genuine_contrast_matches_the_evidence():
    r, tl = _report(OTP_REQUEST)
    gc = tl["genuine_contrast"]
    if r.verdict != "legitimate":
        assert gc and gc["points"]
        assert {p["label"] for p in gc["points"]} <= {e["label"] for e in tl["evidence_for"]}
        assert all(p["genuine"] and p["scam_phrase"] for p in gc["points"])
        assert gc["example"] is None or gc["example"]["source_url"].startswith("https://")
    _r, safe = _report(OTP_WARNING)
    if safe["verdict"] == "legitimate":
        assert safe["genuine_contrast"] is None
