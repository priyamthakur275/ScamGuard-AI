import email

from ml_common.security.email_forensics import analyze_email


def _parse(raw: str):
    return email.message_from_string(raw)


class TestLegitimateEmail:
    def test_clean_email_with_matching_headers_and_passing_auth_has_no_high_severity_evidence(self):
        raw = (
            "From: alerts@github.com\r\n"
            "To: user@example.com\r\n"
            "Reply-To: alerts@github.com\r\n"
            "Return-Path: <alerts@github.com>\r\n"
            "Subject: Your weekly digest\r\n"
            "Date: Mon, 1 Sep 2026 10:00:00 +0000\r\n"
            "Message-ID: <abc123@github.com>\r\n"
            "Authentication-Results: mx.google.com; spf=pass smtp.mailfrom=github.com; "
            "dkim=pass header.i=@github.com; dmarc=pass header.from=github.com\r\n"
            "\r\n"
            "Here is your weekly summary of activity."
        )
        msg = _parse(raw)
        result = analyze_email(msg, "Here is your weekly summary of activity.")

        assert result.headers.spf == "pass"
        assert result.headers.dkim == "pass"
        assert result.headers.dmarc == "pass"
        assert result.headers.from_domain == "github.com"
        high_severity = [s for s in result.header_evidence if s.severity == "high"]
        assert high_severity == []
        assert result.content_evidence == ()


class TestPhishingEmail:
    def test_credential_and_urgency_language_detected(self):
        body = (
            "URGENT: Your account will be suspended within 24 hours. "
            "Click here to verify your identity and confirm your account immediately."
        )
        msg = _parse("From: security@example.com\r\nSubject: Alert\r\n\r\n" + body)
        result = analyze_email(msg, body)

        codes = {s.code for s in result.content_evidence}
        assert "urgency_language" in codes
        assert "credential_request" in codes

    def test_otp_request_detected(self):
        body = "Please reply with the one-time password sent to your phone to confirm."
        msg = _parse("From: support@example.com\r\n\r\n" + body)
        result = analyze_email(msg, body)
        assert any(s.code == "otp_request" for s in result.content_evidence)

    def test_embedded_phishing_url_gets_real_url_evidence(self):
        body = "Please login here: http://arnaz0n-verify.tk/login to secure your account."
        msg = _parse("From: x@example.com\r\n\r\n" + body)
        result = analyze_email(msg, body)
        assert len(result.url_evidence) == 1
        url = next(iter(result.url_evidence))
        assert result.url_evidence[url]["is_suspicious_tld"] is True


class TestSpoofLikeEmail:
    def test_reply_to_mismatch_detected(self):
        msg = _parse(
            "From: security@paypal.com\r\n"
            "Reply-To: attacker@totally-different-domain.tk\r\n"
            "\r\nYour account needs attention."
        )
        result = analyze_email(msg, "Your account needs attention.")
        assert any(s.code == "reply_to_domain_mismatch" for s in result.header_evidence)

    def test_return_path_mismatch_detected(self):
        msg = _parse(
            "From: security@paypal.com\r\n"
            "Return-Path: <bounce@spammer-domain.xyz>\r\n"
            "\r\nAccount notice."
        )
        result = analyze_email(msg, "Account notice.")
        assert any(s.code == "return_path_domain_mismatch" for s in result.header_evidence)

    def test_sender_domain_lookalike_detected(self):
        msg = _parse("From: security@arnazon.com\r\n\r\nAccount notice.")
        result = analyze_email(msg, "Account notice.")
        assert any(s.code == "sender_domain_lookalike" for s in result.header_evidence)

    def test_spf_fail_produces_high_severity_signal(self):
        msg = _parse(
            "From: ceo@example.com\r\n"
            "Authentication-Results: mx.google.com; spf=fail smtp.mailfrom=example.com\r\n"
            "\r\nWire the funds now."
        )
        result = analyze_email(msg, "Wire the funds now.")
        spf_signal = next(s for s in result.header_evidence if s.code == "spf_fail")
        assert spf_signal.severity == "high"


class TestMissingHeaders:
    def test_no_authentication_results_header_reports_not_available_never_fabricated(self):
        msg = _parse("From: someone@example.com\r\nSubject: Hi\r\n\r\nJust a note.")
        result = analyze_email(msg, "Just a note.")
        assert result.headers.spf == "not_available"
        assert result.headers.dkim == "not_available"
        assert result.headers.dmarc == "not_available"
        assert any(s.code == "no_authentication_results" for s in result.header_evidence)

    def test_partial_authentication_results_only_reports_available_mechanisms(self):
        msg = _parse(
            "From: someone@example.com\r\n"
            "Authentication-Results: mx.google.com; spf=pass smtp.mailfrom=example.com\r\n"
            "\r\nHello."
        )
        result = analyze_email(msg, "Hello.")
        assert result.headers.spf == "pass"
        assert result.headers.dkim == "not_available"
        assert result.headers.dmarc == "not_available"

    def test_missing_reply_to_and_return_path_are_not_flagged_as_mismatches(self):
        # Absence is not evidence -- only an actual mismatch is.
        msg = _parse("From: someone@example.com\r\n\r\nHello.")
        result = analyze_email(msg, "Hello.")
        codes = {s.code for s in result.header_evidence}
        assert "reply_to_domain_mismatch" not in codes
        assert "return_path_domain_mismatch" not in codes

    def test_missing_from_header_does_not_crash(self):
        msg = _parse("Subject: No sender\r\n\r\nBody text.")
        result = analyze_email(msg, "Body text.")
        assert result.headers.from_address is None
        assert result.headers.from_domain is None


class TestMalformedEmail:
    def test_completely_empty_string_does_not_crash(self):
        msg = _parse("")
        result = analyze_email(msg, "")
        assert result.headers.from_address is None
        assert result.content_evidence == ()

    def test_garbage_non_email_text_does_not_crash(self):
        msg = _parse("this is not an email at all, just some random text without headers")
        result = analyze_email(msg, "this is not an email at all, just some random text without headers")
        assert result.headers.from_domain is None

    def test_malformed_authentication_results_does_not_crash(self):
        msg = _parse(
            "From: x@example.com\r\n"
            "Authentication-Results: garbled nonsense with no real tokens ;;;===\r\n"
            "\r\nBody."
        )
        result = analyze_email(msg, "Body.")
        assert result.headers.spf == "not_available"

    def test_malformed_from_address_does_not_crash(self):
        msg = _parse("From: not a valid email address at all\r\n\r\nBody.")
        result = analyze_email(msg, "Body.")
        # Should degrade gracefully, not raise.
        assert result.headers.from_address == "not a valid email address at all"


class TestLargeEmail:
    def test_very_large_body_is_handled_without_excessive_slowdown_or_crash(self):
        import time

        large_body = ("This is a normal sentence. " * 5000) + " urgent verify your account now"
        msg = _parse("From: x@example.com\r\n\r\n" + large_body)

        start = time.perf_counter()
        result = analyze_email(msg, large_body)
        elapsed = time.perf_counter() - start

        assert elapsed < 5.0
        assert any(s.code == "urgency_language" for s in result.content_evidence)

    def test_many_embedded_urls_are_capped_not_unbounded(self):
        body = " ".join(f"http://example{i}.com/path" for i in range(50))
        msg = _parse("From: x@example.com\r\n\r\n" + body)
        result = analyze_email(msg, body)
        assert len(result.url_evidence) <= 10


class TestMaliciousAttachmentMetadata:
    def test_exe_attachment_flagged_as_dangerous(self):
        raw = (
            "From: x@example.com\r\n"
            "Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n"
            "\r\n"
            "--BOUNDARY\r\n"
            "Content-Type: text/plain\r\n"
            "\r\n"
            "See attached invoice.\r\n"
            "--BOUNDARY\r\n"
            'Content-Type: application/octet-stream; name="invoice.exe"\r\n'
            'Content-Disposition: attachment; filename="invoice.exe"\r\n'
            "Content-Transfer-Encoding: base64\r\n"
            "\r\n"
            "ZmFrZSBjb250ZW50\r\n"
            "--BOUNDARY--\r\n"
        )
        msg = _parse(raw)
        result = analyze_email(msg, "See attached invoice.")

        assert len(result.attachments) == 1
        assert result.attachments[0].filename == "invoice.exe"
        assert any(s.code == "dangerous_attachment_extension" for s in result.attachment_evidence)

    def test_double_extension_attachment_flagged(self):
        raw = (
            "From: x@example.com\r\n"
            "Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n"
            "\r\n"
            "--BOUNDARY\r\n"
            "Content-Type: text/plain\r\n\r\n"
            "See attached.\r\n"
            "--BOUNDARY\r\n"
            'Content-Type: application/octet-stream; name="invoice.pdf.exe"\r\n'
            'Content-Disposition: attachment; filename="invoice.pdf.exe"\r\n'
            "Content-Transfer-Encoding: base64\r\n\r\n"
            "ZmFrZQ==\r\n"
            "--BOUNDARY--\r\n"
        )
        msg = _parse(raw)
        result = analyze_email(msg, "See attached.")
        assert any(s.code == "double_extension_attachment" for s in result.attachment_evidence)

    def test_ordinary_pdf_attachment_not_flagged(self):
        raw = (
            "From: x@example.com\r\n"
            "Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
            "--BOUNDARY\r\n"
            "Content-Type: text/plain\r\n\r\n"
            "See attached.\r\n"
            "--BOUNDARY\r\n"
            'Content-Type: application/pdf; name="invoice.pdf"\r\n'
            'Content-Disposition: attachment; filename="invoice.pdf"\r\n'
            "Content-Transfer-Encoding: base64\r\n\r\n"
            "ZmFrZQ==\r\n"
            "--BOUNDARY--\r\n"
        )
        msg = _parse(raw)
        result = analyze_email(msg, "See attached.")
        assert result.attachment_evidence == ()

    def test_no_attachments_produces_empty_tuples_not_none(self):
        msg = _parse("From: x@example.com\r\n\r\nNo attachments here.")
        result = analyze_email(msg, "No attachments here.")
        assert result.attachments == ()
        assert result.attachment_evidence == ()


class TestReceivedChainEvidence:
    def test_no_received_headers_with_from_present_produces_informational_signal(self):
        msg = _parse("From: someone@example.com\r\nSubject: Hi\r\n\r\nJust a note.")
        result = analyze_email(msg, "Just a note.")
        signal = next(s for s in result.header_evidence if s.code == "no_received_chain")
        assert signal.severity == "low"

    def test_no_from_and_no_received_headers_does_not_produce_the_signal(self):
        # Guards against firing on a genuinely empty/malformed input where
        # there's nothing to say anything about at all.
        msg = _parse("Subject: Hi\r\n\r\nJust a note.")
        result = analyze_email(msg, "Just a note.")
        assert not any(s.code == "no_received_chain" for s in result.header_evidence)

    def test_real_received_chain_present_does_not_trigger_no_received_chain_signal(self):
        raw = (
            "From: alerts@github.com\r\n"
            "Received: from mail.github.com (mail.github.com [192.30.252.1])\r\n"
            "\t by mx.google.com with ESMTPS id abc123\r\n"
            "Received: by mail.github.com with SMTP id def456\r\n"
            "\r\nWeekly digest."
        )
        msg = _parse(raw)
        result = analyze_email(msg, "Weekly digest.")
        assert not any(s.code == "no_received_chain" for s in result.header_evidence)
        assert len(result.headers.received_chain) == 2

    def test_private_ip_in_received_chain_detected(self):
        raw = (
            "From: alerts@example.com\r\n"
            "Received: from internal-relay.corp.local (10.0.5.12)\r\n"
            "\t by mx.example.com with ESMTP id xyz789\r\n"
            "\r\nInternal notice."
        )
        msg = _parse(raw)
        result = analyze_email(msg, "Internal notice.")
        signal = next(s for s in result.header_evidence if s.code == "received_chain_private_ip")
        assert signal.severity == "low"
        assert "1 hop" in signal.reason

    def test_public_ip_in_received_chain_is_not_flagged(self):
        raw = (
            "From: alerts@example.com\r\n"
            "Received: from mail.example.com (8.8.8.8)\r\n"
            "\t by mx.example.com with ESMTP id xyz789\r\n"
            "\r\nNotice."
        )
        msg = _parse(raw)
        result = analyze_email(msg, "Notice.")
        assert not any(s.code == "received_chain_private_ip" for s in result.header_evidence)

    def test_multiple_hops_with_private_ips_are_counted(self):
        raw = (
            "From: alerts@example.com\r\n"
            "Received: from a.corp.local (10.0.0.1)\r\n\tby b (unknown)\r\n"
            "Received: from b.corp.local (192.168.1.1)\r\n\tby c (unknown)\r\n"
            "\r\nNotice."
        )
        msg = _parse(raw)
        result = analyze_email(msg, "Notice.")
        signal = next(s for s in result.header_evidence if s.code == "received_chain_private_ip")
        assert "2 hop" in signal.reason

    def test_received_chain_is_exposed_verbatim_in_headers_dict(self):
        raw = (
            "From: alerts@example.com\r\n"
            "Received: from a.example.com by b.example.com\r\n"
            "\r\nNotice."
        )
        msg = _parse(raw)
        result = analyze_email(msg, "Notice.")
        assert len(result.headers.received_chain) == 1
        assert "a.example.com" in result.headers.received_chain[0]


class TestSerialization:
    def test_to_dict_produces_json_serializable_structure(self):
        import json

        msg = _parse(
            "From: security@arnazon.com\r\n"
            "Reply-To: attacker@evil.tk\r\n"
            "\r\nurgent verify your account, share the otp now"
        )
        result = analyze_email(msg, "urgent verify your account, share the otp now")
        # Must not raise -- proves every field is JSON-safe.
        json.dumps(result.to_dict())
