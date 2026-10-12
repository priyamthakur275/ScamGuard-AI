from unittest.mock import patch

import httpx

from app_service.services import copilot_llm_provider as llm


class _Settings:
    COPILOT_LLM_PROVIDER = "gemini"
    COPILOT_LLM_API_KEY = "test-key"
    COPILOT_LLM_MODEL = None


def _client_returning(payload, seen):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_gemini_provider_sends_grounded_prompt_and_parses_reply():
    seen: list[httpx.Request] = []
    payload = {"candidates": [{"content": {"parts": [{"text": "Yes, this is a scam."}]}}]}
    with patch.object(llm, "get_settings", return_value=_Settings()), \
         patch.object(llm, "_http_client", return_value=_client_returning(payload, seen)):
        out = llm.get_llm_answer("is this a scam?", "Verdict: scam")
    assert out == "Yes, this is a scam."
    assert seen[0].headers["x-goog-api-key"] == "test-key"
    assert b"Verdict: scam" in seen[0].content


def test_anthropic_provider_parses_reply():
    seen: list[httpx.Request] = []
    s = _Settings(); s.COPILOT_LLM_PROVIDER = "anthropic"
    payload = {"content": [{"type": "text", "text": "Call 1930 now."}]}
    with patch.object(llm, "get_settings", return_value=s), \
         patch.object(llm, "_http_client", return_value=_client_returning(payload, seen)):
        assert llm.get_llm_answer("I paid", "Verdict: scam") == "Call 1930 now."
    assert seen[0].headers["x-api-key"] == "test-key"


def test_provider_failure_falls_back_to_deterministic_answer():
    from app_service.services import copilot_service

    class Scan:  # minimal stand-in; answer_question only needs these
        verdict = "scam"; threat_score = 0.95; scam_category = "banking_fraud"; metadata = {}
        recommended_actions = []; highlighted_entities = {}; top_contributing_tokens = []
        scam_probability = 0.9; confidence_score = 0.9; risk_level = "high"

    with patch("app_service.services.copilot_llm_provider.get_llm_answer", side_effect=httpx.ConnectError("down")):
        ans = copilot_service.get_answer("I already paid, what now?", Scan())
    assert ans.source == "deterministic" and "1930" in ans.answer
