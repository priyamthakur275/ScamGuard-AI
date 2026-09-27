from tests.conftest import register_and_login


class TestSecurityHeaders:
    def test_response_includes_security_headers(self, client):
        # Regression test: SecurityHeadersMiddleware existed in code but
        # was never actually registered via app.add_middleware(), so none
        # of these headers were ever sent. This confirms it now is.
        response = client.get("/api/v1/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "strict-transport-security" in response.headers

    def test_security_headers_present_on_error_responses_too(self, client):
        response = client.get("/api/v1/messages/history")  # no auth -> 401
        assert response.status_code == 401
        assert response.headers.get("x-content-type-options") == "nosniff"


class TestBodySizeLimit:
    def test_oversized_json_body_is_rejected_before_processing(self, client):
        token = register_and_login(client, "bodysize@example.com")
        # Comfortably over the 256KB JSON limit, well under anything a
        # legitimate request to this API would ever need.
        huge_text = "a" * (300 * 1024)
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": huge_text, "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 413
        assert response.json()["error_code"] == "PAYLOAD_TOO_LARGE"

    def test_normal_sized_request_is_not_affected(self, client):
        token = register_and_login(client, "bodysize-normal@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "A perfectly ordinary message", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
