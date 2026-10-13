"""The public test bench runs all 15 fixed cases through the real pipeline."""
from app_service.services import test_bench


def test_every_case_has_its_input():
    assert len(test_bench.CASES) == 15
    assert sum(c.expected == "scam" for c in test_bench.CASES) == 7
    for c in test_bench.CASES:
        assert c.text or (test_bench.FIXTURES / c.file).exists()


def test_bench_endpoint_reports_each_case(client, monkeypatch):
    # Links are not fetched in tests; everything else runs for real.
    from app_service.services import extraction
    monkeypatch.setattr(extraction, "_fetch_url_safely", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")), raising=False)
    test_bench._CACHE.clear()
    body = client.get("/api/v1/public/test-bench").json()
    assert len(body["cases"]) == 15
    assert body["summary"]["total"] == 15
    by_id = {c["id"]: c for c in body["cases"]}
    for c in test_bench.CASES:
        row = by_id[c.id]
        assert row["verdict"] in ("scam", "legitimate"), row
        assert row["verdict"] == c.expected, (c.id, c.title, row)


def test_scam_types_follow_what_the_message_asks():
    from ml_service.inference.threat_scorer import ThreatScorer
    s = ThreatScorer()
    arrest = s.assess(0.9, [], "This is Mumbai cyber police. You are under digital arrest. Transfer money to the RBI safe account now.")
    assert arrest.scam_category == "government_scam"
    link = s.assess(0.9, [], "http://sbi-reward-points.xyz/claim?ref=KYC-update")
    assert link.scam_category == "phishing"
    otp = s.assess(0.9, [], "Your SBI bank account will be blocked today. Share the OTP sent to your mobile to update KYC.")
    assert otp.scam_category == "banking_fraud"


def test_link_only_input_is_phishing_even_with_pipeline_notes():
    from ml_service.inference.threat_scorer import ThreatScorer
    text = "http://sbi-reward-points.xyz/claim?ref=KYC-update\n\nDetected language/concepts (heuristic):\nDetected concepts: KYC."
    assert ThreatScorer().assess(0.9, [], text).scam_category == "phishing"
