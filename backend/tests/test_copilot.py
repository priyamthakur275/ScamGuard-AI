import pytest

from app_service.schemas.message import AnalysisResult, TokenContribution
from app_service.services.copilot_service import classify_intent, answer_question, get_answer
from app_service.services.copilot_llm_provider import get_llm_answer, CopilotLlmUnavailableError
from app_service.core.config import get_settings
from datetime import datetime, timezone
import uuid

from tests.conftest import register_and_login


def _fake_scan(**overrides) -> AnalysisResult:
    defaults = dict(
        id=uuid.uuid4(),
        text="URGENT verify your account",
        input_type="TEXT",
        metadata=None,
        verdict="scam",
        scam_probability=0.9,
        risk_level="high",
        scam_category="banking_fraud",
        confidence_score=0.8,
        threat_score=0.95,
        top_contributing_tokens=[
            TokenContribution(token="urgent", weight=0.5),
            TokenContribution(token="verify", weight=0.3),
        ],
        model_name="naive_bayes",
        model_version="v1",
        latency_ms=5.0,
        user_feedback=None,
        recommended_actions=["Do not click any links", "Contact your bank directly"],
        highlighted_entities=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


class TestIntentClassification:
    def test_why_flagged_intent(self):
        assert classify_intent("Why was this flagged?") == "why_flagged"

    def test_evidence_intent(self):
        assert classify_intent("What evidence caused the risk?") == "evidence"

    def test_attacker_request_intent(self):
        assert classify_intent("What is the attacker asking for?") == "attacker_request"

    def test_recommended_action_intent(self):
        assert classify_intent("What should I do?") == "recommended_action"

    def test_suspicious_indicators_intent(self):
        assert classify_intent("Which indicators are suspicious?") == "suspicious_indicators"

    def test_unrecognized_question_is_unknown(self):
        assert classify_intent("What's the weather like today?") == "unknown"


class TestWhyFlaggedGrounding:
    def test_answer_cites_real_verdict_and_probability(self):
        scan = _fake_scan()
        result = answer_question("Why was this flagged?", scan)
        assert "scam" in result.answer
        assert "90%" in result.answer
        assert result.source == "deterministic"

    def test_answer_cites_real_top_tokens(self):
        scan = _fake_scan()
        result = answer_question("Why was this flagged?", scan)
        assert "urgent" in result.answer
        assert "verify" in result.answer

    def test_legitimate_verdict_produces_a_different_honest_answer(self):
        scan = _fake_scan(verdict="legitimate", scam_probability=0.1, risk_level="low")
        result = answer_question("Why was this flagged?", scan)
        assert "legitimate" in result.answer
        assert "10%" in result.answer


class TestEvidenceGrounding:
    def test_lists_real_url_intelligence_evidence(self):
        scan = _fake_scan(metadata={
            "url_intelligence": {
                "evidence": [{"code": "suspicious_tld", "severity": "low", "reason": "The TLD is commonly abused."}]
            }
        })
        result = answer_question("What evidence caused the risk?", scan)
        assert "The TLD is commonly abused." in result.answer

    def test_no_evidence_is_stated_honestly_not_fabricated(self):
        scan = _fake_scan(metadata=None)
        result = answer_question("What evidence caused the risk?", scan)
        assert "No additional structured evidence" in result.answer


class TestAttackerRequestGrounding:
    def test_detects_otp_request_from_real_evidence(self):
        scan = _fake_scan(metadata={
            "voice_evidence": [{"code": "otp_request", "severity": "high", "reason": "..."}]
        })
        result = answer_question("What is the attacker asking for?", scan)
        assert "OTP" in result.answer

    def test_no_request_detected_is_stated_honestly(self):
        scan = _fake_scan(metadata=None)
        result = answer_question("What is the attacker asking for?", scan)
        assert "No specific request" in result.answer
        assert "does not necessarily mean" in result.answer


class TestRecommendedActionGrounding:
    def test_returns_the_real_recommended_actions_verbatim(self):
        scan = _fake_scan()
        result = answer_question("What should I do?", scan)
        assert "Do not click any links" in result.answer
        assert "Contact your bank directly" in result.answer

    def test_no_actions_is_stated_honestly(self):
        scan = _fake_scan(recommended_actions=None)
        result = answer_question("What should I do?", scan)
        assert "No specific recommended actions" in result.answer


class TestSuspiciousIndicatorsGrounding:
    def test_lists_real_entities(self):
        scan = _fake_scan(highlighted_entities={"phones": ["+919876543210"]})
        result = answer_question("Which indicators are suspicious?", scan)
        assert "+919876543210" in result.answer


class TestUnknownQuestionHandling:
    def test_unmatched_question_says_so_honestly_not_a_generic_answer(self):
        scan = _fake_scan()
        result = answer_question("What's the weather like today?", scan)
        assert "I couldn't match your question" in result.answer
        assert result.intent == "unknown"


class TestNeverHallucinatesBeyondScanData:
    def test_answer_never_mentions_a_category_not_in_this_scan(self):
        scan = _fake_scan(scam_category="banking_fraud")
        result = answer_question("Why was this flagged?", scan)
        assert "lottery" not in result.answer.lower()
        assert "job_scam" not in result.answer.lower()

    def test_grounded_in_field_reflects_what_was_actually_used(self):
        scan = _fake_scan()
        result = answer_question("What should I do?", scan)
        assert result.grounded_in == ("recommended_actions",)


class TestLlmProviderUnavailable:
    def test_raises_unavailable_when_no_provider_configured(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.delenv("COPILOT_LLM_PROVIDER", raising=False)
        with pytest.raises(CopilotLlmUnavailableError, match="No LLM provider"):
            get_llm_answer("Why was this flagged?", "some context")
        get_settings.cache_clear()

    def test_unknown_provider_name_raises_unavailable(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.setenv("COPILOT_LLM_PROVIDER", "not-a-real-provider")
        with pytest.raises(CopilotLlmUnavailableError, match="not a recognized"):
            get_llm_answer("Why was this flagged?", "some context")
        monkeypatch.delenv("COPILOT_LLM_PROVIDER", raising=False)
        get_settings.cache_clear()

    def test_get_answer_falls_back_to_deterministic_when_llm_unavailable(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.delenv("COPILOT_LLM_PROVIDER", raising=False)
        scan = _fake_scan()
        result = get_answer("What should I do?", scan)
        assert result.source == "deterministic"
        assert "Do not click any links" in result.answer
        get_settings.cache_clear()


class TestCopilotApiEndToEnd:
    def test_copilot_answers_grounded_in_a_real_scan_via_the_api(self, client):
        token = register_and_login(client, "copilot-e2e@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        scan = client.post(
            "/api/v1/messages/analyze",
            json={"text": "URGENT verify your bank account immediately or it will be suspended", "input_type": "TEXT"},
            headers=headers,
        ).json()

        response = client.post(
            f"/api/v1/messages/{scan['id']}/copilot",
            json={"question": "What should I do?"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "deterministic"
        assert body["intent"] == "recommended_action"

    def test_copilot_requires_auth(self, client):
        response = client.post(
            "/api/v1/messages/00000000-0000-0000-0000-000000000000/copilot",
            json={"question": "Why?"},
        )
        assert response.status_code == 401

    def test_copilot_cannot_be_asked_about_another_users_scan(self, client):
        token_a = register_and_login(client, "copilot-iso-a@example.com")
        token_b = register_and_login(client, "copilot-iso-b@example.com")
        scan_a = client.post(
            "/api/v1/messages/analyze",
            json={"text": "Hello there", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token_a}"},
        ).json()

        response = client.post(
            f"/api/v1/messages/{scan_a['id']}/copilot",
            json={"question": "Why was this flagged?"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404

    def test_empty_question_is_rejected(self, client):
        token = register_and_login(client, "copilot-empty@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        scan = client.post(
            "/api/v1/messages/analyze",
            json={"text": "Hello there", "input_type": "TEXT"},
            headers=headers,
        ).json()
        response = client.post(
            f"/api/v1/messages/{scan['id']}/copilot", json={"question": ""}, headers=headers
        )
        assert response.status_code == 422
