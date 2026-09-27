from ml_common.security.voice_signals import analyze_voice_transcript


class TestEmptyTranscript:
    def test_empty_string_returns_no_evidence(self):
        assert analyze_voice_transcript("") == ()

    def test_whitespace_only_returns_no_evidence(self):
        assert analyze_voice_transcript("   \n\t  ") == ()


class TestLegitimateCall:
    def test_ordinary_conversation_has_no_evidence(self):
        transcript = "Hi, just calling to confirm our meeting tomorrow at 3pm. Talk soon!"
        assert analyze_voice_transcript(transcript) == ()


class TestScamSignalDetection:
    def test_detects_authority_impersonation(self):
        transcript = "This is the police, we have an arrest warrant issued in your name."
        signals = analyze_voice_transcript(transcript)
        assert any(s.code == "authority_impersonation" for s in signals)

    def test_detects_otp_request(self):
        transcript = "Can you please read out the code we just sent to your phone?"
        signals = analyze_voice_transcript(transcript)
        assert any(s.code == "otp_request" for s in signals)

    def test_detects_remote_access_request(self):
        transcript = "Please install AnyDesk so I can help you fix this issue."
        signals = analyze_voice_transcript(transcript)
        assert any(s.code == "remote_access_request" for s in signals)

    def test_detects_credential_request(self):
        transcript = "I need your internet banking password to verify your identity."
        signals = analyze_voice_transcript(transcript)
        assert any(s.code == "credential_request" for s in signals)

    def test_detects_payment_pressure(self):
        transcript = "You need to pay a fine immediately using a gift card."
        signals = analyze_voice_transcript(transcript)
        codes = {s.code for s in signals}
        assert "payment_pressure" in codes

    def test_detects_threat_language(self):
        transcript = "If you don't comply, your account will be blocked and legal action will be taken."
        signals = analyze_voice_transcript(transcript)
        assert any(s.code == "threat_language" for s in signals)

    def test_detects_bank_impersonation(self):
        transcript = "Hello, this is the bank calling about suspicious activity on your account."
        signals = analyze_voice_transcript(transcript)
        assert any(s.code == "impersonation" for s in signals)

    def test_realistic_vishing_call_triggers_multiple_high_severity_signals(self):
        transcript = (
            "This is the police. There is an arrest warrant in your name. "
            "To resolve this immediately, you must pay a fine using a gift card, "
            "and please install AnyDesk so we can verify your account."
        )
        signals = analyze_voice_transcript(transcript)
        high_severity_codes = {s.code for s in signals if s.severity == "high"}
        assert "authority_impersonation" in high_severity_codes
        assert "remote_access_request" in high_severity_codes


class TestEvidenceStructure:
    def test_every_signal_has_code_severity_reason(self):
        transcript = "This is the police, share the otp now or your account will be blocked."
        signals = analyze_voice_transcript(transcript)
        assert len(signals) > 0
        for s in signals:
            assert s.code
            assert s.severity in ("low", "medium", "high")
            assert len(s.reason) > 10

    def test_single_category_does_not_produce_duplicate_signals(self):
        transcript = "urgent, act now, this is urgent, final warning"
        signals = analyze_voice_transcript(transcript)
        urgency_signals = [s for s in signals if s.code == "urgency_language"]
        assert len(urgency_signals) == 1
