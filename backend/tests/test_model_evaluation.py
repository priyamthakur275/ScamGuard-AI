from app_service.core.security import create_access_token
from app_service.services.model_evaluation_service import get_model_evaluations, _dataset_limitation_note

from tests.conftest import register_and_login  # noqa: F401


class TestModelEvaluationRBAC:
    def test_regular_user_cannot_access_model_evaluation(self, client):
        token = register_and_login(client, "model-eval-plain@example.com")
        response = client.get("/api/v1/admin/model-evaluation", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_unauthenticated_request_is_rejected(self, client):
        response = client.get("/api/v1/admin/model-evaluation")
        assert response.status_code == 401

    def test_admin_can_access_model_evaluation(self, client, admin_user):
        token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
        response = client.get("/api/v1/admin/model-evaluation", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestModelEvaluationContent:
    def test_response_contains_the_real_registered_model(self, client, admin_user):
        token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
        response = client.get("/api/v1/admin/model-evaluation", headers={"Authorization": f"Bearer {token}"})
        entries = response.json()
        assert len(entries) >= 1
        naive_bayes_entries = [e for e in entries if e["model_name"] == "naive_bayes"]
        assert len(naive_bayes_entries) >= 1

    def test_every_entry_has_the_required_fields(self, client, admin_user):
        token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
        response = client.get("/api/v1/admin/model-evaluation", headers={"Authorization": f"Bearer {token}"})
        for entry in response.json():
            assert "accuracy" in entry
            assert "precision" in entry
            assert "recall" in entry
            assert "f1" in entry
            assert "confusion_matrix" in entry
            cm = entry["confusion_matrix"]
            assert {"true_positives", "true_negatives", "false_positives", "false_negatives"} <= cm.keys()
            assert "dataset_size" in entry
            assert "model_name" in entry
            assert "version" in entry

    def test_confusion_matrix_counts_sum_to_dataset_test_split(self, client, admin_user):
        token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
        response = client.get("/api/v1/admin/model-evaluation", headers={"Authorization": f"Bearer {token}"})
        for entry in response.json():
            if entry["test_rows"] == 0:
                continue
            cm = entry["confusion_matrix"]
            total = cm["true_positives"] + cm["true_negatives"] + cm["false_positives"] + cm["false_negatives"]
            assert total == entry["test_rows"]

    def test_evaluation_data_is_never_mixed_into_a_real_scan_result(self, client):
        token = register_and_login(client, "model-eval-separation@example.com")
        response = client.post(
            "/api/v1/messages/analyze",
            json={"text": "Hello there", "input_type": "TEXT"},
            headers={"Authorization": f"Bearer {token}"},
        )
        result = response.json()
        assert "confusion_matrix" not in result
        assert "dataset_size" not in result
        assert "train_rows" not in result


class TestDatasetLimitationNote:
    def test_small_dataset_gets_an_explicit_limitation_note(self):
        note = _dataset_limitation_note(24)
        assert note is not None
        assert "24" in note

    def test_large_dataset_gets_no_limitation_note(self):
        note = _dataset_limitation_note(5000)
        assert note is None

    def test_zero_dataset_size_gets_a_not_recorded_note_not_a_fabricated_one(self):
        note = _dataset_limitation_note(0)
        assert note is not None
        assert "not recorded" in note.lower()

    def test_real_registry_entry_exposes_its_actual_small_dataset_limitation(self):
        evaluations = get_model_evaluations()
        production_entries = [e for e in evaluations if e.is_production]
        assert len(production_entries) >= 1
        for entry in production_entries:
            if entry.dataset_size > 0:
                assert entry.dataset_size < 200
                assert entry.dataset_limitation_note is not None
