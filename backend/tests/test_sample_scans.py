"""The 15 demo sample scans and the scam-type rules they exercise."""
from app_service.services import sample_scans


def test_every_case_has_its_input():
    assert len(sample_scans.CASES) == 15
    assert sum(c.expected == "scam" for c in sample_scans.CASES) == 7
    for c in sample_scans.CASES:
        assert c.text or (sample_scans.FIXTURES / c.file).exists()


def test_every_sample_gets_the_expected_verdict(client, monkeypatch):
    # Links are not fetched in tests; everything else runs for real.
    from app_service.services import extraction
    from app_service.services.message_service import MessageService
    from app_service.db.session import get_db
    from app_service.main import app

    monkeypatch.setattr(extraction, "_fetch_url_safely", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")), raising=False)
    db = next(app.dependency_overrides.get(get_db, get_db)())
    for c in sample_scans.CASES:
        text, metadata = sample_scans.extract_case(c)
        result = MessageService(db).analyze_ephemeral(text, c.input_type, metadata)
        verdict = str(getattr(result.verdict, "value", result.verdict)).lower()
        assert verdict == c.expected, (c.id, c.title, verdict)


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
