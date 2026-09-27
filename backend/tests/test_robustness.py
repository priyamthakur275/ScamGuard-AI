from app_service.core.security import create_access_token
from app_service.services.robustness_service import run_robustness_suite, _classify_stability

from tests.conftest import register_and_login  # noqa: F401


class TestStabilityClassification:
    def test_small_delta_is_stable(self):
        assert _classify_stability(0.01) == "stable"

    def test_moderate_delta_is_changed(self):
        assert _classify_stability(0.08) == "changed"

    def test_large_delta_is_significantly_changed(self):
        assert _classify_stability(0.3) == "significantly_changed"

    def test_thresholds_are_fixed_boundaries_not_arbitrary(self):
        assert _classify_stability(0.049) == "stable"
        assert _classify_stability(0.05) == "changed"
        assert _classify_stability(0.149) == "changed"
        assert _classify_stability(0.15) == "significantly_changed"


class TestRobustnessSuiteContent:
    def test_suite_covers_both_scam_and_benign_categories(self, db_session):
        reports = run_robustness_suite(db_session)
        categories = {r.category for r in reports}
        assert categories == {"scam", "benign_scam_vocab"}

    def test_every_base_message_has_a_result_for_every_transform(self, db_session):
        from ml_common.testing.robustness_transforms import TRANSFORM_CATALOG

        reports = run_robustness_suite(db_session)
        for report in reports:
            assert len(report.transform_results) == len(TRANSFORM_CATALOG)

    def test_transform_results_reflect_real_computed_deltas_not_fabricated(self, db_session):
        reports = run_robustness_suite(db_session)
        for report in reports:
            for t in report.transform_results:
                if t.stability != "not_applicable":
                    expected_delta = round(abs(t.transformed_probability - t.base_probability), 4)
                    assert t.probability_delta == expected_delta

    def test_no_op_transforms_are_honestly_marked_not_applicable(self, db_session):
        reports = run_robustness_suite(db_session)
        benign_no_url_report = next(
            r for r in reports if r.message_id == "benign_urgent_word"
        )
        homoglyph_result = next(
            t for t in benign_no_url_report.transform_results if t.transform_code == "homoglyph_domain"
        )
        assert homoglyph_result.stability == "not_applicable"

    def test_verdict_changed_flag_is_consistent_with_actual_verdicts(self, db_session):
        reports = run_robustness_suite(db_session)
        for report in reports:
            for t in report.transform_results:
                assert t.verdict_changed == (t.transformed_verdict != t.base_verdict)


class TestRobustnessDoesNotPersist:
    def test_running_the_suite_does_not_pollute_any_users_history(self, client, db_session):
        token = register_and_login(client, "robustness-no-history@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        run_robustness_suite(db_session)

        history = client.get("/api/v1/messages/history", headers=headers).json()
        assert history == []


class TestRobustnessApiRBAC:
    def test_regular_user_cannot_run_robustness_test(self, client):
        token = register_and_login(client, "robustness-plain@example.com")
        response = client.post(
            "/api/v1/admin/robustness-test", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_unauthenticated_request_is_rejected(self, client):
        response = client.post("/api/v1/admin/robustness-test")
        assert response.status_code == 401

    def test_admin_can_run_robustness_test(self, client, admin_user):
        token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
        response = client.post(
            "/api/v1/admin/robustness-test", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) > 0
        assert "transform_results" in body[0]
