import json
from unittest.mock import patch

import pytest

from app_service.api.v1.copilot_chat import looks_like_evidence
from app_service.rag import crag
from app_service.rag.retriever import HybridRetriever, get_retriever, load_knowledge_base
from app_service.services.copilot_llm_provider import CopilotLlmUnavailableError

KYC = ("Dear SBI customer, your YONO account will be blocked today due to pending KYC. Share the OTP sent to your "
       "mobile and update PAN at http://sbi-yono-kyc.xyz")
JOB = ("Congratulations! You are selected for a part-time job. Earn Rs 5000 daily by liking YouTube videos. "
       "Pay Rs 999 registration fee on UPI to start today.")
GENUINE = "Rs. 2,450.00 debited from A/c XX4821 on 12-10-26 to AMAZON PAY. Not you? Call 1800-1234. Never share your OTP with anyone."


def _events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.split("\n\n"):
        lines = [l for l in block.splitlines() if not l.startswith(":")]
        if not lines:
            continue
        name = next(l[7:] for l in lines if l.startswith("event: "))
        data = json.loads(next(l[6:] for l in lines if l.startswith("data: ")))
        out.append((name, data))
    return out


def test_knowledge_base_is_valid_and_cites_https_sources():
    entries = load_knowledge_base()
    assert len(entries) >= 30
    assert len({e.id for e in entries}) == len(entries)
    assert all(e.source_url.startswith("https://") for e in entries)
    assert all(e.tactics for e in entries if e.kind == "scam")


def test_retriever_ranks_matching_scheme_first_and_scores_genuine_low():
    r = get_retriever()
    top = r.search(KYC, {"account_threat", "deadline", "asks_for_secret"}, top_k=3)[0]
    assert top.entry.id == "kb-001" and top.relevance >= crag.CORRECT_MIN
    assert r.search("Are we still meeting for the project discussion tomorrow at 10?", set(), top_k=1)[0].relevance < crag.AMBIGUOUS_MIN


def test_retriever_rejects_empty_knowledge_base():
    with pytest.raises(ValueError):
        HybridRetriever([])


def test_grade_retrieval_thresholds():
    r = get_retriever()
    grade, conf, refined = crag.grade_retrieval(r.search(KYC, {"asks_for_secret"}, top_k=5))
    assert grade == "CORRECT" and conf >= crag.CORRECT_MIN and refined
    assert crag.grade_retrieval([]) == ("INCORRECT", 0.0, [])


def test_parse_llm_json_rejects_preamble_and_bad_schema():
    good = '{"is_scam": true, "confidence_percentage": 90, "risk_tier": "High", "matched_tactics": [], "citation_links": []}'
    assert crag.parse_llm_json(good).is_scam is True
    with pytest.raises(ValueError):
        crag.parse_llm_json("Sure! Here is the JSON: " + good)
    with pytest.raises(Exception):
        crag.parse_llm_json('{"is_scam": true, "confidence_percentage": 140, "risk_tier": "High", "matched_tactics": [], "citation_links": []}')


def test_analyze_scam_returns_strict_verdict_with_citations(client):
    res = client.post("/api/v1/copilot/analyze", json={"text": KYC})
    assert res.status_code == 200
    v = res.json()["verdict"]
    assert v["is_scam"] is True and v["risk_tier"] == "High" and v["fraud_index"] >= 90
    assert v["retrieval_grade"] == "CORRECT" and v["citation_links"][0]["kb_id"] == "kb-001"
    assert {"asks_for_secret", "account_threat"} <= {t["id"] for t in v["matched_tactics"]}
    assert v["verdict_source"] == "engine" and v["emerging_threat"] is False


def test_analyze_genuine_message(client):
    v = client.post("/api/v1/copilot/analyze", json={"text": GENUINE}).json()["verdict"]
    assert v["is_scam"] is False and v["risk_tier"] == "Low" and v["scam_type"] is None


def test_analyze_validation_errors(client):
    assert client.post("/api/v1/copilot/analyze", json={"text": "  \u0000 "}).status_code == 422
    assert client.post("/api/v1/copilot/analyze", json={"text": "x" * 4001}).status_code == 422
    assert client.post("/api/v1/copilot/analyze", json={}).status_code == 422


def test_unmatched_scam_is_flagged_as_emerging_threat(db_session):
    with patch.object(crag, "grade_retrieval", return_value=("INCORRECT", 0.1, [])):
        out = crag.analyze_evidence(db_session, KYC)
    assert out.verdict.is_scam and out.verdict.emerging_threat and not out.verdict.citation_links
    assert "emerging" in out.answer


def test_llm_review_is_guarded(db_session):
    invented = json.dumps({"is_scam": True, "confidence_percentage": 88, "risk_tier": "High",
                           "matched_tactics": ["Asks for OTP / PIN / password", "Made up tactic"],
                           "citation_links": ["https://www.rbi.org.in", "https://evil.example.com"]})
    with patch("app_service.services.copilot_llm_provider.get_llm_completion", return_value=invented):
        v = crag.analyze_evidence(db_session, KYC).verdict
    assert v.verdict_source == "llm_reviewed" and v.confidence_percentage == 88
    assert all(c.url != "https://evil.example.com" for c in v.citation_links)
    assert [t.label for t in v.matched_tactics] == ["Asks for OTP / PIN / password"]


def test_llm_contradicting_confident_engine_is_overruled(db_session):
    flip = json.dumps({"is_scam": False, "confidence_percentage": 70, "risk_tier": "Low", "matched_tactics": [], "citation_links": []})
    with patch("app_service.services.copilot_llm_provider.get_llm_completion", return_value=flip):
        v = crag.analyze_evidence(db_session, KYC).verdict
    assert v.is_scam is True and v.verdict_source == "engine_kept_over_llm"


def test_llm_garbage_falls_back_to_engine(db_session):
    with patch("app_service.services.copilot_llm_provider.get_llm_completion", return_value="I think it's a scam!"):
        v = crag.analyze_evidence(db_session, KYC).verdict
    assert v.verdict_source == "engine" and any("failed validation" in n for n in v.notes)


def test_no_provider_configured_uses_engine(db_session):
    with patch("app_service.services.copilot_llm_provider.get_llm_completion", side_effect=CopilotLlmUnavailableError("x")):
        assert crag.analyze_evidence(db_session, KYC).verdict.verdict_source == "engine"


def test_looks_like_evidence():
    assert looks_like_evidence(KYC)
    assert looks_like_evidence("http://paypa1-login.top")
    assert not looks_like_evidence("what should I do?")
    assert not looks_like_evidence("hi")


def test_chat_streams_verdict_and_tokens(client):
    res = client.post("/api/v1/copilot/chat", json={"message": JOB})
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/event-stream")
    ev = _events(res.text)
    names = [n for n, _ in ev]
    assert names[0] == "status" and "verdict" in names and names[-1] == "done"
    verdict = next(d for n, d in ev if n == "verdict")
    assert verdict["is_scam"] is True and verdict["scam_type"] == "job_scam"
    text = "".join(d["text"] for n, d in ev if n == "token")
    assert text.startswith("This looks like a scam")


def test_chat_follow_up_uses_previous_evidence(client):
    res = client.post("/api/v1/copilot/chat", json={"message": "I already paid, what now?", "history": [{"role": "user", "content": JOB}]})
    ev = _events(res.text)
    assert ev[-1] == ("done", {"kind": "follow_up"})
    assert "1930" in "".join(d["text"] for n, d in ev if n == "token")


def test_chat_without_evidence_gives_guidance(client):
    ev = _events(client.post("/api/v1/copilot/chat", json={"message": "hello"}).text)
    assert ev[-1] == ("done", {"kind": "guidance"})


def test_chat_server_failure_becomes_error_event(client):
    with patch("app_service.api.v1.copilot_chat.analyze_evidence", side_effect=RuntimeError("db down")):
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": JOB}).text)
    assert ev == [("error", {"message": "The analysis failed on the server. Please try again in a moment.", "retryable": True})]


def test_chat_history_limits(client):
    turns = [{"role": "user", "content": "hi"}] * 21
    assert client.post("/api/v1/copilot/chat", json={"message": "hi", "history": turns}).status_code == 422
    assert client.post("/api/v1/copilot/chat", json={"message": "hi", "history": [{"role": "system", "content": "x"}]}).status_code == 422


def test_xray_does_not_flag_a_never_share_warning():
    from ml_service.inference.scam_xray import xray
    spans = xray("Rs. 2,450.00 debited from A/c XX4821. Never share your OTP with anyone.")["spans"]
    assert "asks_for_secret" not in {s["intent"] for s in spans}


def test_bank_alert_is_reassuring_unless_it_asks_for_something():
    from ml_service.inference.threat_scorer import ThreatScorer
    s = ThreatScorer()
    found, protective = s.intents("Rs. 2,450.00 debited from A/c XX4821 on 12-10-26 to AMAZON PAY. Not you? Call 1800-1234.")
    assert "transaction_alert" in protective and not found
    found, protective = s.intents("Rs 5000 credited to your A/c XX1234 by mistake from my side. Please return it on PhonePe.")
    assert "mistaken_transfer" in found and "transaction_alert" not in protective


def test_genuine_short_debit_alert_is_not_flagged(client):
    v = client.post("/api/v1/copilot/analyze", json={"text": GENUINE}).json()["verdict"]
    assert v["is_scam"] is False and not v["matched_tactics"]


SALARY = ("Dear Customer, your A/c XX4417 is credited with INR 52,300.00 on 01-10-2026 towards SALARY FOR SEP 2026. "
          "Avl Bal: INR 61,882.40 - HDFC Bank")


def test_knowledge_base_has_scam_and_genuine_layers():
    entries = load_knowledge_base()
    kinds = {e.kind for e in entries}
    assert kinds == {"scam", "genuine"}
    assert sum(e.kind == "scam" for e in entries) >= 40 and sum(e.kind == "genuine" for e in entries) >= 10


@pytest.mark.parametrize("text", [
    SALARY,
    "Rs 1,200.00 credited to your A/c XX5562 on 13-10-26 by NEFT from INFOSYS LTD. Avl bal Rs 45,120.",
    "Salary for the month of September 2026 has been credited to your account XXXX8890. Ref No 482910337. -ICICI Bank",
    "INR 899.00 spent on your SBI Credit Card ending 4432 at SWIGGY on 12/10/26. Available limit Rs 54,210. Not you? Call 1860 180 1290.",
    "Your EMI of Rs 6,412 for loan a/c XX8812 is due on 05-11-2026. Please keep sufficient balance. -Bajaj Finance",
])
def test_genuine_transaction_guard_accepts_real_alerts(text):
    from ml_service.inference.threat_scorer import ThreatScorer, is_genuine_transaction
    found, protective = ThreatScorer.intents(text)
    assert is_genuine_transaction(text, found, protective)
    assert ThreatScorer().assess(0.96, [], text).threat_score <= 0.15


@pytest.mark.parametrize("text", [
    "Your salary of Rs 45,000 is credited to your A/c XX1234. To receive it click http://salary-hr-portal.xyz and verify.",
    "Salary Rs 50,000 credited to A/c XX1234 by mistake from our HR. Please return it to 9876543210 on PhonePe.",
    "Rs 25,000 credited to your A/c XX7781. Call 9812345670 to activate the amount.",
    "Your A/c XX7781 is credited with Rs 4,999 cashback reward. Pay Rs 49 processing fee to claim.",
    "Rs 10,000 credited to your account XX2231. Share the OTP to confirm receipt. Avl bal Rs 12,000.",
    "Your A/c XX1234 salary has been credited. Install SalaryPay app from apk link to withdraw.",
])
def test_genuine_transaction_guard_rejects_lookalike_scams(text):
    from ml_service.inference.threat_scorer import ThreatScorer, is_genuine_transaction
    found, protective = ThreatScorer.intents(text)
    assert not is_genuine_transaction(text, found, protective)


def test_salary_credit_is_low_risk_with_genuine_match(client):
    v = client.post("/api/v1/copilot/analyze", json={"text": SALARY}).json()["verdict"]
    assert v["is_scam"] is False and v["risk_tier"] == "Low"
    assert v["genuine_matches"] and v["genuine_matches"][0]["kb_id"] == "gen-001"
    assert all(c["kind"] == "scam" for c in v["citation_links"])


def test_scam_verdict_never_lists_genuine_matches(client):
    v = client.post("/api/v1/copilot/analyze", json={"text": KYC}).json()["verdict"]
    assert v["is_scam"] is True and v["genuine_matches"] == []


def test_otp_requested_by_pronoun_and_police_threats_are_detected():
    from ml_service.inference.threat_scorer import ThreatScorer
    found, _ = ThreatScorer.intents("I have sent a 6-digit code to your phone. Please read it to me so I can stop the block.")
    assert "asks_for_secret" in found
    found, _ = ThreatScorer.intents("Your account will be frozen and police action will follow.")
    assert "legal_threat" in found


def test_awareness_message_is_reassuring():
    from ml_service.inference.threat_scorer import ThreatScorer
    _, protective = ThreatScorer.intents("Beware of fake KYC calls. SBI never asks for your OTP or PIN.")
    assert "awareness_warning" in protective


class _FakeLLM:
    def __init__(self, reply="Phishing is a trick to steal your details.", fail=False):
        self.reply, self.fail, self.calls = reply, fail, []

    def complete(self, system, user, max_tokens=400):
        self.calls.append((system, user))
        if self.fail:
            raise RuntimeError("provider down")
        return self.reply


def test_long_question_is_not_treated_as_evidence():
    assert not looks_like_evidence("What is the difference between phishing and smishing and how can I protect my parents from both?")
    assert looks_like_evidence("Dear customer your KYC is pending, click here to update or your account will be blocked today?")


def test_chat_general_question_uses_llm_with_history(client):
    fake = _FakeLLM()
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=fake):
        ev = _events(client.post("/api/v1/copilot/chat", json={
            "message": "what is phishing?", "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello!"}]}).text)
    assert "".join(d["text"] for n, d in ev if n == "token") == fake.reply
    assert ev[-1] == ("done", {"kind": "guidance"})
    system, user = fake.calls[0]
    assert "ScamGuard Copilot" in system and "Copilot: Hello!" in user and "what is phishing?" in user


def test_chat_follow_up_gives_llm_the_scan(client):
    fake = _FakeLLM("Call 1930 now.")
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=fake):
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": "I already paid, what now?", "history": [{"role": "user", "content": JOB}]}).text)
    assert ev[-1] == ("done", {"kind": "follow_up"})
    assert "analysis of the message" in fake.calls[-1][1]


def test_chat_llm_failure_falls_back_to_builtin(client):
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=_FakeLLM(fail=True)):
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": "hello"}).text)
    assert "aste" in "".join(d["text"] for n, d in ev if n == "token")


class _SlowLLM:
    def stream(self, system, user, max_tokens=400):
        import time
        time.sleep(1.5)
        yield "too late"


def test_chat_slow_llm_falls_back_quickly(client):
    import time
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=_SlowLLM()), \
         patch("app_service.api.v1.copilot_chat.FIRST_TOKEN_SECONDS", 0.3):
        t0 = time.time()
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": "how do I report a scam?"}).text)
    text = "".join(d["text"] for n, d in ev if n == "token")
    assert "1930" in text and "Chakshu" in text and "too late" not in text and ev[-1][0] == "done"
    assert time.time() - t0 < 1.4


class _StreamingLLM:
    def __init__(self, pieces, fail_after=None):
        self.pieces, self.fail_after = pieces, fail_after

    def stream(self, system, user, max_tokens=400):
        for i, p in enumerate(self.pieces):
            if self.fail_after is not None and i == self.fail_after:
                raise RuntimeError("connection reset")
            yield p


def test_chat_streams_llm_pieces_live(client):
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=_StreamingLLM(["Digital ", "arrest ", "is a scam."])):
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": "what is digital arrest?"}).text)
    assert [d["text"] for n, d in ev if n == "token"] == ["Digital ", "arrest ", "is a scam."]
    assert ev[-1] == ("done", {"kind": "guidance"})


def test_chat_llm_stream_interrupted_midway(client):
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=_StreamingLLM(["Part one ", "two"], fail_after=1)):
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": "what is phishing?"}).text)
    assert ("token", {"text": "Part one "}) in ev and ev[-1][0] == "error" and ev[-1][1]["retryable"] is True


def test_chat_llm_fails_before_first_piece_uses_builtin(client):
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=_StreamingLLM(["x"], fail_after=0)):
        ev = _events(client.post("/api/v1/copilot/chat", json={"message": "hello"}).text)
    assert "aste" in "".join(d["text"] for n, d in ev if n == "token") and ev[-1][0] == "done"


def _mock_client(body: str):
    import httpx

    return lambda: httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})))


def test_gemini_stream_parser():
    from app_service.services import copilot_llm_provider as prov

    body = ('data: {"candidates":[{"content":{"parts":[{"text":"Hello "}]}}]}\r\n\r\n'
            'data: {"candidates":[{"content":{"parts":[{"text":"there"}]},"finishReason":"STOP"}]}\r\n\r\n')
    from types import SimpleNamespace

    cfg = SimpleNamespace(COPILOT_LLM_MODEL=None, COPILOT_LLM_API_KEY="test-key")
    with patch.object(prov, "_http_client", _mock_client(body)), patch.object(prov, "get_settings", return_value=cfg):
        assert list(prov.GeminiProvider().stream("s", "u")) == ["Hello ", "there"]


def test_openai_compatible_stream_parser():
    from app_service.services import copilot_llm_provider as prov

    body = ('data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"Namaste"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"!"}}]}\n\ndata: [DONE]\n\n')
    with patch.object(prov, "_http_client", _mock_client(body)):
        assert list(prov.GroqProvider().stream("s", "u")) == ["Namaste", "!"]


def test_llm_self_check_reports_without_key():
    from app_service.services import copilot_llm_provider as prov

    with patch.object(prov, "get_configured_provider", return_value=_FakeLLM("OK")):
        assert prov.self_check().startswith("Copilot LLM check OK")
    with patch.object(prov, "get_configured_provider", return_value=_FakeLLM(fail=True)):
        assert "FAILED" in prov.self_check()


def test_gemini_config_per_generation():
    from app_service.services.copilot_llm_provider import _gemini_config

    assert _gemini_config("gemini-2.5-flash", 900)["thinkingConfig"] == {"thinkingBudget": 0}
    g3 = _gemini_config("gemini-3.8-flash", 900)
    assert g3["thinkingConfig"] == {"thinkingLevel": "minimal"} and g3["maxOutputTokens"] > 900


def test_llm_self_check_flags_empty_reply():
    from app_service.services import copilot_llm_provider as prov

    with patch.object(prov, "get_configured_provider", return_value=_FakeLLM("")):
        assert "empty reply" in prov.self_check()


def test_llm_budget_caps_per_visitor_and_per_day():
    from app_service.services import llm_budget

    llm_budget.reset()
    t = 1_800_000_000.0
    assert all(llm_budget.allow("a", 0, t + i) for i in range(llm_budget.PER_VISITOR))
    assert not llm_budget.allow("a", 0, t + 20)                       # visitor over the cap
    assert llm_budget.allow("b", 0, t + 20)                           # others unaffected
    assert llm_budget.allow("a", 0, t + llm_budget.PER_VISITOR_WINDOW + 10)  # window slides
    llm_budget.reset()
    assert llm_budget.allow("x", 2, t) and llm_budget.allow("y", 2, t) and not llm_budget.allow("z", 2, t)
    assert llm_budget.allow("z", 2, t + 86_400)                      # new day
    llm_budget.reset()


def test_chat_falls_back_when_llm_cap_reached(client):
    from app_service.services import llm_budget

    llm_budget.reset()
    fake = _FakeLLM("AI answer")
    with patch("app_service.services.copilot_llm_provider.get_configured_provider", return_value=fake), \
         patch.object(llm_budget, "PER_VISITOR", 1):
        first = _events(client.post("/api/v1/copilot/chat", json={"message": "what is phishing?"}).text)
        second = _events(client.post("/api/v1/copilot/chat", json={"message": "what is vishing?"}).text)
    assert "".join(d["text"] for n, d in first if n == "token") == "AI answer"
    assert "aste" in "".join(d["text"] for n, d in second if n == "token")
    llm_budget.reset()


def test_gemini_thinking_falls_back_to_low_once():
    from app_service.services import copilot_llm_provider as p

    p._THINKING_LEVEL[0] = "minimal"
    try:
        assert p._downgrade_thinking(400, '{"error": "thinking_level minimal is not supported"}')
        assert p._THINKING_LEVEL[0] == "low"
        assert not p._downgrade_thinking(400, "thinking")  # only once
    finally:
        p._THINKING_LEVEL[0] = "minimal"


def test_general_answer_intents():
    from app_service.api.v1.copilot_chat import general_answer
    assert "ScamGuard Copilot" in general_answer("who are u")
    assert "1930" in general_answer("maine paise bhej diye, fraud ho gaya")
    assert "Chakshu" in general_answer("how do I report a scam")
    assert "digital arrest" in general_answer("is digital arrest real?").lower()
