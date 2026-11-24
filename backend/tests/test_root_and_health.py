class TestRootAndHealthRoutes:
    def test_root_returns_service_metadata(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["service"] == "ScamGuard AI"
        assert body["api_prefix"] == "/api/v1"
        assert body["health"] == "/api/v1/health"
        assert body["docs"] == "/docs"

    def test_top_level_health_alias_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_docs_not_blocked_by_strict_api_csp(self, client):
        response = client.get("/docs")
        assert response.status_code == 200
        assert response.headers.get("content-security-policy") is None
