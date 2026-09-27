from unittest.mock import patch, MagicMock


from tests.conftest import register_and_login  # noqa: F401 (re-exported for this module's tests)


FAKE_ML_RESPONSE = {
    "verdict": "scam",
    "scam_probability": 0.91,
    "risk_level": "high",
    "scam_category": "banking_fraud",
    "confidence_score": 0.82,
    "threat_score": 0.95,
    "top_contributing_tokens": [{"token": "verify", "weight": 0.5}],
    "model_name": "naive_bayes",
    "model_version": "v1",
    "latency_ms": 3.2,
}


def _mock_httpx_post(*args, **kwargs):
    mock_response = MagicMock()
    mock_response.json.return_value = FAKE_ML_RESPONSE
    mock_response.raise_for_status.return_value = None
    return mock_response


def test_analyze_requires_auth(client):
    response = client.post("/api/v1/messages/analyze", json={"text": "hello"})
    assert response.status_code == 401


def test_analyze_persists_and_returns_result(client):
    token = register_and_login(client, "analyze@example.com")
    with patch("app_service.services.message_service.httpx.post", side_effect=_mock_httpx_post):
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "Urgent verify your account now"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "scam"
    assert data["text"] == "Urgent verify your account now"
    assert data["user_feedback"] is None


def test_history_returns_persisted_analyses(client):
    token = register_and_login(client, "history@example.com")
    with patch("app_service.services.message_service.httpx.post", side_effect=_mock_httpx_post):
        client.post(
            "/api/v1/messages/analyze",
            json={"text": "message one"},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get("/api/v1/messages/history", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["text"] == "message one"


def test_history_is_scoped_to_user(client):
    token_a = register_and_login(client, "usera@example.com")
    token_b = register_and_login(client, "userb@example.com")
    with patch("app_service.services.message_service.httpx.post", side_effect=_mock_httpx_post):
        client.post(
            "/api/v1/messages/analyze",
            json={"text": "user a message"},
            headers={"Authorization": f"Bearer {token_a}"},
        )

    response = client.get("/api/v1/messages/history", headers={"Authorization": f"Bearer {token_b}"})
    assert response.json() == []


def test_feedback_updates_prediction(client):
    token = register_and_login(client, "feedback@example.com")
    with patch("app_service.services.message_service.httpx.post", side_effect=_mock_httpx_post):
        analyze_resp = client.post(
            "/api/v1/messages/analyze",
            json={"text": "feedback test"},
            headers={"Authorization": f"Bearer {token}"},
        )
    prediction_id = analyze_resp.json()["id"]

    response = client.patch(
        f"/api/v1/messages/{prediction_id}/feedback",
        json={"is_accurate": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user_feedback"] is True


def test_feedback_on_missing_prediction_returns_404(client):
    import uuid

    token = register_and_login(client, "missingfeedback@example.com")
    response = client.patch(
        f"/api/v1/messages/{uuid.uuid4()}/feedback",
        json={"is_accurate": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_analyze_returns_503_when_ml_service_unavailable(client):
    token = register_and_login(client, "unavailable@example.com")
    import httpx as httpx_module

    with patch(
        "app_service.services.message_service.httpx.post",
        side_effect=httpx_module.ConnectError("connection refused"),
    ), patch(
        "app_service.services.message_service.get_in_process_prediction_service",
        side_effect=RuntimeError("in-process model unavailable"),
    ):
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 503


def test_cannot_submit_feedback_on_another_users_prediction(client):
    """Object-level authorization: prediction_id alone must never be
    sufficient to act on a prediction -- it must belong to the requesting
    user. This tests against another user's REAL prediction id (not a
    random/nonexistent uuid, which wouldn't catch a bug where the user_id
    filter was accidentally dropped from the query).
    """
    token_a = register_and_login(client, "objauth-a@example.com")
    token_b = register_and_login(client, "objauth-b@example.com")

    analyze_resp = client.post(
        "/api/v1/messages/analyze",
        json={"text": "Hi there, are we still on for lunch?"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert analyze_resp.status_code == 200
    prediction_id = analyze_resp.json()["id"]

    # User B attempts to leave feedback on user A's prediction.
    response = client.patch(
        f"/api/v1/messages/{prediction_id}/feedback",
        json={"is_accurate": True},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404

    # Confirm it genuinely wasn't modified.
    history_a = client.get(
        "/api/v1/messages/history", headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    assert history_a[0]["user_feedback"] is None


def test_cannot_delete_another_users_prediction(client):
    token_a = register_and_login(client, "objauth-del-a@example.com")
    token_b = register_and_login(client, "objauth-del-b@example.com")

    analyze_resp = client.post(
        "/api/v1/messages/analyze",
        json={"text": "Hi there, are we still on for lunch?"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    prediction_id = analyze_resp.json()["id"]

    response = client.delete(
        f"/api/v1/messages/{prediction_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404

    history_a = client.get(
        "/api/v1/messages/history", headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    assert len(history_a) == 1


def test_cannot_view_another_users_history(client):
    token_a = register_and_login(client, "objauth-hist-a@example.com")
    token_b = register_and_login(client, "objauth-hist-b@example.com")

    client.post(
        "/api/v1/messages/analyze",
        json={"text": "Only user A should ever see this scan"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    history_b = client.get(
        "/api/v1/messages/history", headers={"Authorization": f"Bearer {token_b}"}
    ).json()
    assert history_b == []


def test_scan_endpoint_accepts_a_real_image_upload_over_http(client):
    """Regression/coverage test: no prior test exercised POST
    /messages/scan over real HTTP (existing upload tests call
    ExtractionService directly) -- this both closes that gap and confirms
    BodySizeLimitMiddleware's multipart allowance doesn't break a normal,
    legitimately-sized image upload through the actual route.
    """
    import io
    from PIL import Image, ImageDraw, ImageFont

    token = register_and_login(client, "scanupload@example.com")
    img = Image.new("RGB", (1400, 180), color="white")
    ImageDraw.Draw(img).text((30, 50), "Share your OTP to verify your bank account now.", fill="black", font=ImageFont.load_default(size=36))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/v1/messages/scan",
        files={"file": ("test.png", buf, "image/png")},
        data={"input_type": "IMAGE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["input_type"] == "IMAGE"


def test_url_intelligence_survives_end_to_end_to_the_api_response(client):
    """Contract test for the unified-pipeline audit: extraction.py computes
    real, structured url_intelligence signals (punycode/lookalike/suspicious
    TLD/etc.) for URL scans. This confirms that data actually reaches the
    API response's `metadata` field (it's stored via Prediction.metadata_
    and returned via AnalysisResult.metadata) rather than being silently
    computed-and-discarded, which is what the frontend needs to render it.
    """
    token = register_and_login(client, "urlintel@example.com")
    response = client.post(
        "/api/v1/messages/scan",
        data={"text": "http://arnazon-verify-account.tk/login", "input_type": "URL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata is not None
    assert "url_intelligence" in metadata
    intel = metadata["url_intelligence"]
    assert intel["is_suspicious_tld"] is True
    assert intel["registrable_domain"] == "arnazon-verify-account.tk"


class TestGracefulErrorHandling:
    """Phase 2 requirement: every failure mode in the pipeline must degrade
    gracefully with a clear, honest error -- never a raw 500, never a
    fabricated result pretending the input was analyzed.
    """

    def test_empty_text_input_is_rejected_cleanly(self, client):
        token = register_and_login(client, "empty-input@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_whitespace_only_text_is_rejected_cleanly(self, client):
        token = register_and_login(client, "whitespace-input@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "   \n\t  ", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_corrupt_image_upload_fails_gracefully_not_500(self, client):
        import io

        token = register_and_login(client, "corrupt-image@example.com")
        garbage = io.BytesIO(b"this is not a real image file, just garbage bytes")
        response = client.post(
            "/api/v1/messages/scan",
            files={"file": ("fake.png", garbage, "image/png")},
            data={"input_type": "IMAGE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert "error_code" in response.json()

    def test_qr_scan_with_no_qr_code_present_fails_gracefully(self, client):
        import io
        from PIL import Image, ImageDraw, ImageFont

        token = register_and_login(client, "no-qr@example.com")
        img = Image.new("RGB", (30, 30), color="white")  # blank image, no QR code
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        response = client.post(
            "/api/v1/messages/scan",
            files={"file": ("blank.png", buf, "image/png")},
            data={"input_type": "QR"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_unsupported_input_type_is_rejected_cleanly(self, client):
        token = register_and_login(client, "unsupported-type@example.com")
        response = client.post(
            "/api/v1/messages/scan",
            data={"text": "hello", "input_type": "HOLOGRAM"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # A genuinely unsupported input type must fail cleanly, never
        # silently fall through to analyzing it as plain text.
        assert response.status_code == 422

    def test_missing_file_for_file_required_type_fails_gracefully(self, client):
        token = register_and_login(client, "missing-file@example.com")
        response = client.post(
            "/api/v1/messages/scan",
            data={"input_type": "PDF"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_url_with_no_extractable_content_still_gets_a_verdict(self, client):
        # A URL that fails to fetch (DNS failure, blocked target, etc.)
        # must not crash the pipeline -- extraction.py falls back to
        # analyzing the URL string itself as the payload.
        token = register_and_login(client, "url-fetch-fail@example.com")
        response = client.post(
            "/api/v1/messages/scan",
            data={"text": "http://this-domain-does-not-exist-abc123.invalid/path", "input_type": "URL"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["metadata"]["fetch_status"] == "direct_url_analysis"


def test_email_forensics_survives_end_to_end_to_the_api_response(client):
    """Contract test mirroring the URL-intelligence one: confirms the real
    email header/content/attachment evidence computed by
    email_forensics.py actually reaches the API response's metadata field,
    not just the extraction.py internals.
    """
    token = register_and_login(client, "emailforensics@example.com")
    raw_email = (
        "From: security@arnazon.com\r\n"
        "Reply-To: attacker@totally-different.tk\r\n"
        "Subject: Urgent account verification\r\n"
        "\r\n"
        "Your account will be suspended. Verify your identity and share the otp now."
    )
    response = client.post(
        "/api/v1/messages/scan",
        data={"text": raw_email, "input_type": "EMAIL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    forensics = response.json()["metadata"]["email_forensics"]
    assert forensics["headers"]["spf"] == "not_available"
    header_codes = {s["code"] for s in forensics["header_evidence"]}
    assert "reply_to_domain_mismatch" in header_codes
    assert "sender_domain_lookalike" in header_codes
    content_codes = {s["code"] for s in forensics["content_evidence"]}
    assert "otp_request" in content_codes


def test_all_modalities_return_the_same_consistent_result_shape(client):
    """Phase 5: confirms the 'one unified flow' claim empirically -- every
    input modality goes through the same /messages/scan endpoint and
    produces a result with the same required fields, not a different
    shape per scanner.
    """
    import io
    from PIL import Image, ImageDraw, ImageFont

    token = register_and_login(client, "unified-flow@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    required_fields = {
        "id", "verdict", "scam_probability", "risk_level", "scam_category",
        "confidence_score", "threat_score", "model_name", "model_version",
        "input_type", "created_at",
    }

    img_buf = io.BytesIO()
    img = Image.new("RGB", (1400, 180), color="white")
    ImageDraw.Draw(img).text((30, 50), "Share your OTP to verify your bank account now.", fill="black", font=ImageFont.load_default(size=36))
    img.save(img_buf, format="PNG")
    img_buf.seek(0)

    cases = [
        ({"text": "Hi, are we still meeting tomorrow?", "input_type": "TEXT"}, None),
        ({"text": "http://example.com", "input_type": "URL"}, None),
        ({"text": "From: x@example.com\r\n\r\nHello there.", "input_type": "EMAIL"}, None),
        (None, ("file", ("test.png", img_buf, "image/png"))),
    ]

    for data, file_case in cases:
        kwargs = {"headers": headers}
        if data:
            kwargs["data"] = data
        if file_case:
            kwargs["files"] = {file_case[0]: file_case[1]}
            kwargs["data"] = {"input_type": "IMAGE"}
        response = client.post("/api/v1/messages/scan", **kwargs)
        assert response.status_code == 200, response.text
        body = response.json()
        missing = required_fields - body.keys()
        assert not missing, f"missing fields {missing} for case {data or file_case}"


class TestVoiceScamAnalyzer:
    def test_voice_transcript_from_browser_is_analyzed_through_the_real_pipeline(self, client):
        token = register_and_login(client, "voice-real@example.com")
        transcript = (
            "This is the police. There is an arrest warrant in your name. "
            "You must pay a fine immediately using a gift card, "
            "and please install AnyDesk so we can verify your account."
        )
        response = client.post(
            "/api/v1/messages/scan",
            data={"text": transcript, "input_type": "VOICE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["input_type"] == "VOICE"
        # A real model verdict, not a fabricated one -- same pipeline as
        # every other modality.
        assert body["verdict"] in ("scam", "legitimate", "phishing", "spam")
        voice_evidence = body["metadata"]["voice_evidence"]
        codes = {s["code"] for s in voice_evidence}
        assert "authority_impersonation" in codes
        assert "remote_access_request" in codes
        assert "payment_pressure" in codes

    def test_benign_voice_transcript_has_no_voice_evidence(self, client):
        token = register_and_login(client, "voice-benign@example.com")
        response = client.post(
            "/api/v1/messages/scan",
            data={"text": "Hey, just checking if we're still on for lunch tomorrow.", "input_type": "VOICE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["metadata"]["voice_evidence"] == []

    def test_empty_transcript_is_rejected_cleanly(self, client):
        token = register_and_login(client, "voice-empty@example.com")
        response = client.post(
            "/api/v1/messages/scan",
            data={"text": "   ", "input_type": "VOICE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_audio_file_upload_without_configured_provider_fails_honestly_not_500(self, client):
        import io

        token = register_and_login(client, "voice-audio-noprovider@example.com")
        fake_audio = io.BytesIO(b"not real audio data, just bytes for the test")
        response = client.post(
            "/api/v1/messages/scan",
            files={"file": ("call.wav", fake_audio, "audio/wav")},
            data={"input_type": "VOICE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        # The error must be honest about WHY -- unavailable transcription,
        # not a generic/misleading failure.
        assert "not configured" in body["message"].lower() or "transcription" in body["message"].lower()

    def test_no_transcript_and_no_file_is_rejected_cleanly(self, client):
        token = register_and_login(client, "voice-nothing@example.com")
        response = client.post(
            "/api/v1/messages/scan",
            data={"input_type": "VOICE"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestMultilingualPreprocessing:
    def test_hinglish_message_survives_end_to_end_to_the_api_response(self, client):
        token = register_and_login(client, "hinglish@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={
                "text": "Turant apna UPI OTP bhejo warna aapka bank khata band ho jayega",
                "input_type": "TEXT",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        multilingual = response.json()["metadata"]["multilingual"]
        assert multilingual["detected_language"] == "hinglish"
        assert "upi" in multilingual["detected_concepts"]
        assert "otp" in multilingual["detected_concepts"]
        assert "bank" in multilingual["detected_concepts"]

    def test_hindi_devanagari_message_survives_end_to_end(self, client):
        token = register_and_login(client, "hindi@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "आपका बैंक खाता तुरंत बंद हो जाएगा, अभी ओटीपी भेजें", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        multilingual = response.json()["metadata"]["multilingual"]
        assert multilingual["detected_language"] == "hindi"
        assert "bank" in multilingual["detected_concepts"]
        assert "otp" in multilingual["detected_concepts"]

    def test_original_text_is_preserved_in_the_stored_and_returned_result(self, client):
        token = register_and_login(client, "preserve-original@example.com")
        original = "Turant apna UPI OTP bhejo warna khata band ho jayega"
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": original, "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["text"].startswith(original)

    def test_plain_english_message_has_no_fabricated_language_claim(self, client):
        token = register_and_login(client, "english-control@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "Hi, are you free for a call later today?", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        multilingual = response.json()["metadata"]["multilingual"]
        assert multilingual["detected_language"] == "english"
        assert multilingual["detected_concepts"] == []


def test_extended_entities_survive_end_to_end_to_the_api_response(client):
    """Contract test: confirms the Phase 10 entity types (payment amounts,
    bank references, dates, organizations) computed by EntityHighlighter
    actually reach the API response's highlighted_entities field.
    """
    token = register_and_login(client, "entities-e2e@example.com")
    text = (
        "Dear Customer, your HDFC Bank account KYC will expire on 20/03/2026. "
        "Pay Rs. 500 processing fee to Account Number 445566778899, "
        "or call 9876543210 immediately."
    )
    response = client.post(
        "/api/v1/messages/analyze",
        json={"text": text, "input_type": "TEXT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    entities = response.json()["highlighted_entities"]
    assert "HDFC Bank" in entities["organizations"]
    assert "445566778899" in entities["bank_references"]
    assert "20/03/2026" in entities["dates"]
    assert any("500" in a for a in entities["payment_amounts"])


def test_history_rejects_out_of_range_paging(client):
    """Negative offsets error on PostgreSQL and unbounded limits allow
    oversized reads; both must be rejected as input errors, not 500s."""
    token = register_and_login(client, "paging@example.com")
    auth_headers = {"Authorization": f"Bearer {token}"}
    for query in ("skip=-1", "limit=0", "limit=201"):
        response = client.get(f"/api/v1/messages/history?{query}", headers=auth_headers)
        assert response.status_code == 422, query
    assert client.get("/api/v1/messages/history?limit=200", headers=auth_headers).status_code == 200
