import pytest

from ml_service.services.prediction_service import EmptyMessageError, PredictionRequest


class TestPredictionServiceIntegration:
    def test_empty_text_raises(self, prediction_service):
        with pytest.raises(EmptyMessageError):
            prediction_service.predict(PredictionRequest(text=""))

    def test_whitespace_only_text_raises(self, prediction_service):
        with pytest.raises(EmptyMessageError):
            prediction_service.predict(PredictionRequest(text="   "))

    def test_result_has_all_required_fields(self, prediction_service):
        result = prediction_service.predict(
            PredictionRequest(text="Urgent! Verify your bank account now.")
        )
        assert result.verdict in {"legitimate", "spam", "phishing", "scam"}
        assert 0.0 <= result.scam_probability <= 1.0
        assert result.risk_level in {"low", "medium", "high"}
        assert 0.0 <= result.confidence_score <= 1.0
        assert 0.0 <= result.threat_score <= 1.0
        assert result.latency_ms >= 0.0
        assert result.model_name
        assert result.model_version

    def test_legitimate_message_is_not_flagged_high_risk(self, prediction_service):
        result = prediction_service.predict(
            PredictionRequest(text="Hey, are we still on for lunch this Friday?")
        )
        assert result.risk_level in {"low", "medium"}

    def test_latency_is_recorded_and_reasonable(self, prediction_service):
        result = prediction_service.predict(PredictionRequest(text="Hello there"))
        # A classical TF-IDF model should score in low milliseconds, not
        # seconds -- this guards against an accidental O(n^2) regression.
        assert result.latency_ms < 1000

    def test_scam_probability_is_never_overwritten_by_the_risk_engine(
        self, prediction_service, loaded_inference_engine
    ):
        """Regression test: scam_probability must always equal exactly what
        the model itself predicted. A previous version of this pipeline
        replaced it with an arbitrarily-boosted "calibrated_probability"
        from the risk engine (raw + 0.35 + keyword bonuses) whenever
        several scam keywords were present -- so a message could be shown
        to the user with a 90%+ "scam probability" that the model never
        actually produced. threat_score is allowed to differ from
        scam_probability (that's the whole point of a risk engine on top
        of the raw model); scam_probability itself must not be.
        """
        text = "URGENT: your bank account will be suspended, verify now by clicking this link"
        raw = loaded_inference_engine.predict(text)
        result = prediction_service.predict(PredictionRequest(text=text))

        assert result.scam_probability == round(raw.scam_probability, 4)


    def test_unreadable_link_starts_from_trust_score_not_bare_url_text(self, prediction_service):
        """A bare address says nothing to the text model; when the page could
        not be read, a trustworthy site must not be flagged because links were
        common in SMS spam, while a deceptive one still is."""
        safe = prediction_service.predict(PredictionRequest(
            text="URL Target: https://www.irctc.co.in/nget/train-search", input_type="URL",
            metadata={"fetch_status": "direct_url_analysis", "url_intelligence": {"trust": {"score": 65}}}))
        assert safe.verdict == "legitimate"
        bad = prediction_service.predict(PredictionRequest(
            text="URL Target: http://paypa1-secure-login.verify-account.top/signin", input_type="URL",
            metadata={"fetch_status": "direct_url_analysis", "url_intelligence": {"trust": {"score": 10}}}))
        assert bad.verdict == "scam"
