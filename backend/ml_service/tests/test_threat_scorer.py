from ml_service.inference.threat_scorer import ThreatScorer, ThreatScoreConfig


class TestThreatScorer:
    def test_low_probability_yields_low_risk(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.1, tokens=["hello", "friend"])
        assert assessment.risk_level == "low"

    def test_high_probability_yields_high_risk(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.9, tokens=["urgent", "verify", "account"])
        assert assessment.risk_level == "high"

    def test_medium_probability_yields_medium_risk(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.5, tokens=["hello"])
        assert assessment.risk_level == "medium"

    def test_urgency_tokens_boost_threat_score_above_raw_probability(self):
        scorer = ThreatScorer()
        without_urgency = scorer.assess(0.5, tokens=["account", "payment"])
        with_urgency = scorer.assess(0.5, tokens=["account", "payment", "urgent", "immediately"])
        assert with_urgency.threat_score > without_urgency.threat_score

    def test_urgency_boost_is_capped(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(
            0.9, tokens=list({"urgent", "immediate", "immediately", "now", "today", "final"})
        )
        assert assessment.threat_score <= 1.0

    def test_category_inferred_for_upi_signals(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.8, tokens=["upi", "gpay", "collect"])
        assert assessment.scam_category == "upi_scam"

    def test_category_inferred_for_banking_signals(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.8, tokens=["bank", "account", "payment"])
        assert assessment.scam_category == "banking_fraud"

    def test_category_inferred_for_lottery_signals(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.8, tokens=["win", "prize", "claim"])
        assert assessment.scam_category == "lottery_scam"

    def test_no_category_when_probability_below_threshold(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.2, tokens=["bank", "account"])
        assert assessment.scam_category is None

    def test_no_category_when_no_signals_present(self):
        scorer = ThreatScorer()
        assessment = scorer.assess(0.9, tokens=["completely", "unrelated", "words"])
        assert assessment.scam_category is None

    def test_custom_thresholds_are_respected(self):
        scorer = ThreatScorer(ThreatScoreConfig(low_risk_ceiling=0.2, medium_risk_ceiling=0.4))
        assessment = scorer.assess(0.3, tokens=[])
        assert assessment.risk_level == "medium"
