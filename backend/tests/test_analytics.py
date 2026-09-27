from tests.conftest import register_and_login

SCAM_TEXT = "URGENT: your bank account will be suspended, verify now by clicking this link"
LEGIT_TEXT = "Hi, are you coming to college tomorrow?"


def _analyze(client, token, text):
    return client.post(
        "/api/v1/messages/analyze",
        json={"text": text, "input_type": "TEXT"},
        headers={"Authorization": f"Bearer {token}"},
    )


class TestAnalyticsSummaryBasics:
    def test_summary_requires_auth(self, client):
        response = client.get("/api/v1/analytics/summary")
        assert response.status_code == 401

    def test_summary_with_no_scans_is_all_zeros(self, client):
        token = register_and_login(client, "emptyanalytics@example.com")
        response = client.get(
            "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_scans"] == 0
        assert data["verdict_distribution"] == {}
        assert data["high_risk_count"] == 0

    def test_invalid_range_is_rejected(self, client):
        token = register_and_login(client, "badrange@example.com")
        response = client.get(
            "/api/v1/analytics/summary?range=nonsense",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestAnalyticsAggregationCorrectness:
    def test_verdict_and_risk_distribution_reflect_real_scans(self, client):
        token = register_and_login(client, "aggregation@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        for _ in range(3):
            resp = _analyze(client, token, SCAM_TEXT)
            assert resp.status_code == 200
        for _ in range(2):
            resp = _analyze(client, token, LEGIT_TEXT)
            assert resp.status_code == 200

        summary = client.get("/api/v1/analytics/summary", headers=headers).json()

        assert summary["total_scans"] == 5
        assert sum(summary["verdict_distribution"].values()) == 5
        assert sum(summary["risk_distribution"].values()) == 5
        # Every category count and risk count must be a real integer from
        # the DB, never negative, never fabricated.
        for count in summary["risk_distribution"].values():
            assert isinstance(count, int) and count >= 0

    def test_high_risk_count_matches_actual_high_risk_scans(self, client):
        token = register_and_login(client, "highrisk@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        results = []
        for _ in range(3):
            resp = _analyze(client, token, SCAM_TEXT)
            results.append(resp.json())

        expected_high_risk = sum(1 for r in results if r["risk_level"] == "high")

        summary = client.get("/api/v1/analytics/summary", headers=headers).json()
        assert summary["high_risk_count"] == expected_high_risk

    def test_analytics_is_scoped_per_user(self, client):
        token_a = register_and_login(client, "analytics-a@example.com")
        token_b = register_and_login(client, "analytics-b@example.com")

        _analyze(client, token_a, SCAM_TEXT)
        _analyze(client, token_a, SCAM_TEXT)
        _analyze(client, token_b, LEGIT_TEXT)

        summary_a = client.get(
            "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token_a}"}
        ).json()
        summary_b = client.get(
            "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {token_b}"}
        ).json()

        assert summary_a["total_scans"] == 2
        assert summary_b["total_scans"] == 1

    def test_feedback_counts_reflect_real_feedback(self, client):
        token = register_and_login(client, "feedbackanalytics@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        result = _analyze(client, token, SCAM_TEXT).json()
        client.patch(
            f"/api/v1/messages/{result['id']}/feedback",
            json={"is_accurate": True},
            headers=headers,
        )
        _analyze(client, token, LEGIT_TEXT)  # left with no feedback

        summary = client.get("/api/v1/analytics/summary", headers=headers).json()
        assert summary["feedback_accurate"] == 1
        assert summary["feedback_pending"] == 1
        assert summary["feedback_inaccurate"] == 0


class TestAnalyticsIsNotLimitedToAPage:
    def test_total_scans_exceeds_the_old_history_page_size(self, client):
        """Regression test for the actual bug being fixed: 'All Time'
        analytics used to be computed client-side from a single page of
        /messages/history (default limit=50), so anyone with more than 50
        scans saw an undercounted total. This creates more than 50 real
        scans and confirms the server-side aggregate reflects the true
        total, not a 50-row ceiling.
        """
        from app_service.core.rate_limit import limiter

        token = register_and_login(client, "manyscans@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        total_created = 55
        for i in range(total_created):
            # /messages/analyze is rate-limited to 30/minute (a real,
            # intentional abuse control -- see rate limiting elsewhere in
            # this suite). This test needs more real scans than that limit
            # allows within the seconds it takes to run, so periodically
            # reset the limiter's counter, exactly like the autouse
            # reset_rate_limiter fixture already does between tests -- this
            # simulates enough real time passing for the window to clear,
            # rather than disabling the actual rate-limit logic.
            if i % 25 == 0:
                limiter.reset()
            text = SCAM_TEXT if i % 2 == 0 else LEGIT_TEXT
            resp = _analyze(client, token, text)
            assert resp.status_code == 200

        summary = client.get("/api/v1/analytics/summary", headers=headers).json()
        assert summary["total_scans"] == total_created
        assert summary["total_scans"] > 50
