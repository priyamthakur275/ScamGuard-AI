from tests.conftest import register_and_login


def _analyze(client, token, text, input_type="TEXT"):
    return client.post(
        "/api/v1/messages/analyze",
        json={"text": text, "input_type": input_type},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def _scan_url(client, token, url_text):
    return client.post(
        "/api/v1/messages/scan",
        data={"text": url_text, "input_type": "URL"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


class TestNoCorrelationOnFirstScan:
    def test_first_ever_scan_has_no_correlation_evidence(self, client):
        token = register_and_login(client, "corr-first@example.com")
        scan = _analyze(client, token, "Call 9876543210 to verify your bank account")
        assert scan["metadata"].get("correlation", []) == []


class TestEntityRecurrence:
    def test_repeated_phone_number_across_scans_is_flagged(self, client):
        token = register_and_login(client, "corr-phone@example.com")
        _analyze(client, token, "Call 9876543210 urgently to verify your bank account")
        second = _analyze(client, token, "Contact 9876543210 immediately regarding your parcel")

        correlation = second["metadata"].get("correlation", [])
        assert any(s["code"] == "recurring_entity" for s in correlation)

    def test_repeated_entity_uses_careful_suspicious_signal_wording(self, client):
        token = register_and_login(client, "corr-wording@example.com")
        _analyze(client, token, "Call 9876543210 urgently to verify your bank account")
        second = _analyze(client, token, "Contact 9876543210 immediately regarding your parcel")

        signal = next(s for s in second["metadata"]["correlation"] if s["code"] == "recurring_entity")
        assert signal["reason"].startswith("Suspicious signal detected")
        assert signal["severity"] in ("low", "medium")

    def test_different_phone_numbers_do_not_trigger_recurrence(self, client):
        token = register_and_login(client, "corr-different-phone@example.com")
        _analyze(client, token, "Call 9876543210 urgently")
        second = _analyze(client, token, "Call 8765432109 urgently")

        correlation = second["metadata"].get("correlation", [])
        assert not any(s["code"] == "recurring_entity" for s in correlation)


class TestDomainRecurrence:
    def test_repeated_domain_across_url_scans_is_flagged(self, client):
        token = register_and_login(client, "corr-domain@example.com")
        _scan_url(client, token, "http://arnaz0n-verify.tk/login1")
        second = _scan_url(client, token, "http://arnaz0n-verify.tk/login2")

        correlation = second["metadata"].get("correlation", [])
        assert any(s["code"] == "recurring_domain" for s in correlation)

    def test_repeated_brand_lookalike_is_flagged(self, client):
        token = register_and_login(client, "corr-brand@example.com")
        _scan_url(client, token, "http://arnazon.com/deal1")
        second = _scan_url(client, token, "http://amaz0n.tk/deal2")

        correlation = second["metadata"].get("correlation", [])
        assert any(s["code"] == "recurring_brand_impersonation" for s in correlation)


class TestCorrelationIsolatedPerUser:
    def test_correlation_never_crosses_between_users(self, client):
        token_a = register_and_login(client, "corr-iso-a@example.com")
        token_b = register_and_login(client, "corr-iso-b@example.com")
        _analyze(client, token_a, "Call 9876543210 urgently to verify your account")
        second_b = _analyze(client, token_b, "Contact 9876543210 immediately about your parcel")

        correlation = second_b["metadata"].get("correlation", [])
        assert not any(s["code"] == "recurring_entity" for s in correlation)


class TestCategoryRecurrence:
    def test_category_recurrence_severity_is_never_high(self, client):
        token = register_and_login(client, "corr-category@example.com")
        for _ in range(3):
            _analyze(client, token, "URGENT verify your bank account immediately or suspension")
        fourth = _analyze(client, token, "URGENT verify your bank account immediately or suspension again")

        for s in fourth["metadata"]["correlation"]:
            if s["code"] == "recurring_category_pattern":
                assert s["severity"] == "low"


class TestCorrelationDoesNotApplyToDemoMode:
    def test_demo_runs_have_no_correlation_field_at_all(self, client):
        token = register_and_login(client, "corr-no-demo@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/demo/examples/bank_otp_scam/run", headers=headers)
        assert "correlation" not in response.json()["metadata"]
