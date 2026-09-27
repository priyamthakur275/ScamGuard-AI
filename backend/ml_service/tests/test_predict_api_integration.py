class TestHealthAndReadiness:
    def test_health_returns_ok(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_reports_model_loaded(self, client):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["model_loaded"] is True


class TestPredictEndpoint:
    def test_predict_scam_message_returns_high_probability_fields(self, client):
        response = client.post(
            "/api/v1/internal/predict",
            json={
                "text": "URGENT! Your bank account will be blocked immediately. "
                "Verify your OTP now to claim your prize."
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["verdict"] in {"scam", "phishing", "spam", "legitimate"}
        assert 0.0 <= data["scam_probability"] <= 1.0
        assert data["risk_level"] in {"low", "medium", "high"}
        assert isinstance(data["top_contributing_tokens"], list)
        assert data["model_name"]
        assert data["model_version"]

    def test_predict_legitimate_message_succeeds(self, client):
        response = client.post(
            "/api/v1/internal/predict",
            json={"text": "Hey, can you send me the pasta recipe from last week?"},
        )
        assert response.status_code == 200

    def test_predict_rejects_empty_text(self, client):
        response = client.post("/api/v1/internal/predict", json={"text": ""})
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_predict_rejects_missing_text_field(self, client):
        response = client.post("/api/v1/internal/predict", json={})
        assert response.status_code == 422

    def test_predict_rejects_whitespace_only_text(self, client):
        response = client.post("/api/v1/internal/predict", json={"text": "     "})
        assert response.status_code == 422

    def test_predict_response_shape_matches_schema(self, client):
        response = client.post(
            "/api/v1/internal/predict",
            json={"text": "Your package delivery could not be completed, pay a fee to reschedule."},
        )
        data = response.json()
        expected_keys = {
            "verdict",
            "scam_probability",
            "risk_level",
            "scam_category",
            "confidence_score",
            "threat_score",
            "top_contributing_tokens",
            "model_name",
            "model_version",
            "latency_ms",
        }
        assert expected_keys.issubset(data.keys())


class TestModelInfoEndpoint:
    def test_get_production_model_info(self, client, trained_registry_dir):
        _artifacts_dir, model_name = trained_registry_dir
        response = client.get(f"/api/v1/internal/models/{model_name}/production")
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == model_name
        assert data["is_production"] is True
        assert 0.0 <= data["accuracy"] <= 1.0

    def test_get_unknown_model_info_returns_error(self, client):
        response = client.get("/api/v1/internal/models/does-not-exist/production")
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_REQUEST"
