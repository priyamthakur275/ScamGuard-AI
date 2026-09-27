from tests.conftest import register_and_login
from app_service.services.demo_examples import DEMO_EXAMPLES


class TestDemoExampleCatalog:
    def test_lists_all_six_required_categories(self, client):
        token = register_and_login(client, "demo-catalog@example.com")
        response = client.get("/api/v1/demo/examples", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        ids = {e["id"] for e in response.json()}
        assert ids == {
            "bank_otp_scam", "job_scam", "investment_scam",
            "delivery_scam", "phishing_url", "legitimate_message",
        }

    def test_catalog_never_includes_a_precomputed_verdict_or_probability(self, client):
        token = register_and_login(client, "demo-catalog-shape@example.com")
        response = client.get("/api/v1/demo/examples", headers={"Authorization": f"Bearer {token}"})
        for example in response.json():
            assert set(example.keys()) == {"id", "label", "category", "input_type"}

    def test_requires_auth(self, client):
        response = client.get("/api/v1/demo/examples")
        assert response.status_code == 401


class TestRunningDemoExamples:
    def test_running_an_example_returns_a_real_verdict_from_the_real_pipeline(self, client):
        token = register_and_login(client, "demo-run@example.com")
        response = client.post(
            "/api/v1/demo/examples/bank_otp_scam/run", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["verdict"] in ("scam", "legitimate", "phishing", "spam")
        assert body["model_name"]
        assert body["metadata"]["is_demo"] is True
        assert body["metadata"]["demo_example_id"] == "bank_otp_scam"

    def test_every_catalog_example_runs_successfully(self, client):
        token = register_and_login(client, "demo-run-all@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        for example in DEMO_EXAMPLES:
            response = client.post(f"/api/v1/demo/examples/{example.id}/run", headers=headers)
            assert response.status_code == 200, f"{example.id} failed: {response.text}"

    def test_legitimate_example_and_scam_example_produce_different_real_outputs(self, client):
        token = register_and_login(client, "demo-differentiation@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        legit = client.post("/api/v1/demo/examples/legitimate_message/run", headers=headers).json()
        scam = client.post("/api/v1/demo/examples/bank_otp_scam/run", headers=headers).json()
        assert legit["scam_probability"] != scam["scam_probability"]

    def test_phishing_url_example_produces_real_url_intelligence(self, client):
        token = register_and_login(client, "demo-url-example@example.com")
        response = client.post(
            "/api/v1/demo/examples/phishing_url/run", headers={"Authorization": f"Bearer {token}"}
        )
        metadata = response.json()["metadata"]
        assert "url_intelligence" in metadata
        assert metadata["url_intelligence"]["is_suspicious_tld"] is True

    def test_unknown_example_id_returns_404(self, client):
        token = register_and_login(client, "demo-unknown@example.com")
        response = client.post(
            "/api/v1/demo/examples/not-a-real-example/run", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_requires_auth(self, client):
        response = client.post("/api/v1/demo/examples/bank_otp_scam/run")
        assert response.status_code == 401


class TestDemoRunsNeverPersistToRealHistory:
    def test_running_all_examples_leaves_history_empty(self, client):
        token = register_and_login(client, "demo-no-history@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        for example in DEMO_EXAMPLES:
            client.post(f"/api/v1/demo/examples/{example.id}/run", headers=headers)

        history = client.get("/api/v1/messages/history", headers=headers).json()
        assert history == []

    def test_running_demo_examples_does_not_affect_analytics(self, client):
        token = register_and_login(client, "demo-no-analytics@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        for example in DEMO_EXAMPLES:
            client.post(f"/api/v1/demo/examples/{example.id}/run", headers=headers)

        summary = client.get("/api/v1/analytics/summary", headers=headers).json()
        assert summary["total_scans"] == 0

    def test_a_real_scan_still_appears_in_history_alongside_demo_runs(self, client):
        token = register_and_login(client, "demo-and-real@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/api/v1/demo/examples/bank_otp_scam/run", headers=headers)
        client.post(
            "/api/v1/messages/analyze",
            json={"text": "A genuine real scan for history", "input_type": "TEXT"},
            headers=headers,
        )
        history = client.get("/api/v1/messages/history", headers=headers).json()
        assert len(history) == 1
        assert history[0]["text"] == "A genuine real scan for history"

    def test_demo_result_has_no_database_backed_id_reusable_for_feedback(self, client):
        token = register_and_login(client, "demo-no-feedback@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        demo_result = client.post("/api/v1/demo/examples/bank_otp_scam/run", headers=headers).json()
        response = client.patch(
            f"/api/v1/messages/{demo_result['id']}/feedback",
            json={"is_accurate": True},
            headers=headers,
        )
        assert response.status_code == 404
