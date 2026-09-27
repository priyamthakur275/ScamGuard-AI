from tests.conftest import register_and_login


def _analyze(client, token, text="Test scam message urgent verify your account"):
    return client.post(
        "/api/v1/messages/analyze",
        json={"text": text, "input_type": "TEXT"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


class TestCaseCreation:
    def test_create_case_with_no_scans(self, client):
        token = register_and_login(client, "case-create@example.com")
        response = client.post(
            "/api/v1/cases",
            json={"title": "Suspicious banking scam", "description": "Multiple reports", "severity": "high"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Suspicious banking scam"
        assert body["status"] == "open"
        assert body["severity"] == "high"
        assert body["scan_count"] == 0

    def test_create_case_with_linked_scans(self, client):
        token = register_and_login(client, "case-create-scans@example.com")
        scan = _analyze(client, token)
        response = client.post(
            "/api/v1/cases",
            json={"title": "Case with scan", "scan_ids": [scan["id"]]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["scan_count"] == 1

    def test_default_severity_is_medium(self, client):
        token = register_and_login(client, "case-default-severity@example.com")
        response = client.post(
            "/api/v1/cases", json={"title": "Untitled case"}, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.json()["severity"] == "medium"

    def test_invalid_severity_is_rejected(self, client):
        token = register_and_login(client, "case-bad-severity@example.com")
        response = client.post(
            "/api/v1/cases",
            json={"title": "Bad severity", "severity": "extreme"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_empty_title_is_rejected(self, client):
        token = register_and_login(client, "case-empty-title@example.com")
        response = client.post(
            "/api/v1/cases", json={"title": ""}, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422

    def test_scans_belonging_to_another_user_are_silently_skipped_not_linked(self, client):
        token_a = register_and_login(client, "case-cross-a@example.com")
        token_b = register_and_login(client, "case-cross-b@example.com")
        scan_b = _analyze(client, token_b)

        response = client.post(
            "/api/v1/cases",
            json={"title": "Attempted cross-user link", "scan_ids": [scan_b["id"]]},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 201
        assert response.json()["scan_count"] == 0  # silently skipped, not linked

    def test_case_creation_requires_auth(self, client):
        response = client.post("/api/v1/cases", json={"title": "No auth"})
        assert response.status_code == 401


class TestCaseIsolation:
    def test_user_cannot_list_another_users_cases(self, client):
        token_a = register_and_login(client, "case-iso-a@example.com")
        token_b = register_and_login(client, "case-iso-b@example.com")
        client.post("/api/v1/cases", json={"title": "A's case"}, headers={"Authorization": f"Bearer {token_a}"})

        response_b = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_b}"})
        assert response_b.json() == []

    def test_user_cannot_get_another_users_case_by_id(self, client):
        token_a = register_and_login(client, "case-iso-get-a@example.com")
        token_b = register_and_login(client, "case-iso-get-b@example.com")
        case = client.post(
            "/api/v1/cases", json={"title": "Private case"}, headers={"Authorization": f"Bearer {token_a}"}
        ).json()

        response = client.get(f"/api/v1/cases/{case['id']}", headers={"Authorization": f"Bearer {token_b}"})
        assert response.status_code == 404

    def test_user_cannot_update_another_users_case(self, client):
        token_a = register_and_login(client, "case-iso-update-a@example.com")
        token_b = register_and_login(client, "case-iso-update-b@example.com")
        case = client.post(
            "/api/v1/cases", json={"title": "Original"}, headers={"Authorization": f"Bearer {token_a}"}
        ).json()

        response = client.patch(
            f"/api/v1/cases/{case['id']}",
            json={"title": "Hijacked"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404

    def test_user_cannot_link_their_own_scan_to_another_users_case(self, client):
        token_a = register_and_login(client, "case-iso-link-a@example.com")
        token_b = register_and_login(client, "case-iso-link-b@example.com")
        case_a = client.post(
            "/api/v1/cases", json={"title": "A's case"}, headers={"Authorization": f"Bearer {token_a}"}
        ).json()
        scan_b = _analyze(client, token_b)

        response = client.post(
            f"/api/v1/cases/{case_a['id']}/scans",
            json={"prediction_id": scan_b["id"]},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404  # case not found for user B


class TestCaseStatusLifecycle:
    def test_status_transitions_through_full_lifecycle(self, client):
        token = register_and_login(client, "case-lifecycle@example.com")
        case = client.post(
            "/api/v1/cases", json={"title": "Lifecycle test"}, headers={"Authorization": f"Bearer {token}"}
        ).json()
        headers = {"Authorization": f"Bearer {token}"}

        for status in ["investigating", "resolved", "archived"]:
            response = client.patch(f"/api/v1/cases/{case['id']}", json={"status": status}, headers=headers)
            assert response.status_code == 200
            assert response.json()["status"] == status

    def test_invalid_status_is_rejected(self, client):
        token = register_and_login(client, "case-bad-status@example.com")
        case = client.post(
            "/api/v1/cases", json={"title": "Bad status test"}, headers={"Authorization": f"Bearer {token}"}
        ).json()
        response = client.patch(
            f"/api/v1/cases/{case['id']}",
            json={"status": "deleted"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_status_change_creates_a_real_timeline_entry(self, client):
        token = register_and_login(client, "case-status-timeline@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Timeline test"}, headers=headers).json()
        client.patch(f"/api/v1/cases/{case['id']}", json={"status": "investigating"}, headers=headers)

        detail = client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()
        entry_types = [e["entry_type"] for e in detail["timeline"]]
        assert "created" in entry_types
        assert "status_changed" in entry_types


class TestScanLinkingAndUnlinking:
    def test_link_and_unlink_scan(self, client):
        token = register_and_login(client, "case-link-unlink@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Link test"}, headers=headers).json()
        scan = _analyze(client, token)

        link_resp = client.post(f"/api/v1/cases/{case['id']}/scans", json={"prediction_id": scan["id"]}, headers=headers)
        assert link_resp.status_code == 200
        assert link_resp.json()["scan_count"] == 1

        unlink_resp = client.delete(f"/api/v1/cases/{case['id']}/scans/{scan['id']}", headers=headers)
        assert unlink_resp.status_code == 200
        assert unlink_resp.json()["scan_count"] == 0

    def test_linking_nonexistent_scan_returns_404(self, client):
        token = register_and_login(client, "case-link-missing@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Missing scan test"}, headers=headers).json()
        response = client.post(
            f"/api/v1/cases/{case['id']}/scans",
            json={"prediction_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers,
        )
        assert response.status_code == 404

    def test_case_detail_includes_full_real_scan_data_not_a_summary(self, client):
        token = register_and_login(client, "case-detail-scan@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        scan = _analyze(client, token, "URGENT verify your bank account immediately or it will be suspended")
        case = client.post(
            "/api/v1/cases", json={"title": "Detail test", "scan_ids": [scan["id"]]}, headers=headers
        ).json()

        detail = client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()
        assert len(detail["scans"]) == 1
        assert detail["scans"][0]["id"] == scan["id"]
        assert detail["scans"][0]["verdict"] == scan["verdict"]  # same real prediction, not re-fabricated


class TestEntityAggregation:
    def test_entities_aggregated_from_real_linked_scans(self, client):
        token = register_and_login(client, "case-entities@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        scan = _analyze(client, token, "Call 9876543210 urgently to verify your HDFC Bank account")
        case = client.post(
            "/api/v1/cases", json={"title": "Entity test", "scan_ids": [scan["id"]]}, headers=headers
        ).json()

        detail = client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()
        assert "phones" in detail["aggregated_entities"]
        assert "+919876543210" in detail["aggregated_entities"]["phones"]

    def test_no_scans_means_no_aggregated_entities(self, client):
        token = register_and_login(client, "case-no-entities@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Empty case"}, headers=headers).json()
        detail = client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()
        assert detail["aggregated_entities"] == {}


class TestNotesAndTimeline:
    def test_add_note_appears_in_timeline(self, client):
        token = register_and_login(client, "case-notes@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Notes test"}, headers=headers).json()

        note_resp = client.post(
            f"/api/v1/cases/{case['id']}/notes", json={"content": "Called the victim, confirmed scam."}, headers=headers
        )
        assert note_resp.status_code == 201
        assert note_resp.json()["entry_type"] == "note"

        detail = client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()
        note_entries = [e for e in detail["timeline"] if e["entry_type"] == "note"]
        assert len(note_entries) == 1
        assert note_entries[0]["content"] == "Called the victim, confirmed scam."

    def test_timeline_is_chronologically_ordered(self, client):
        token = register_and_login(client, "case-timeline-order@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Order test"}, headers=headers).json()
        client.post(f"/api/v1/cases/{case['id']}/notes", json={"content": "First note"}, headers=headers)
        client.patch(f"/api/v1/cases/{case['id']}", json={"status": "investigating"}, headers=headers)
        client.post(f"/api/v1/cases/{case['id']}/notes", json={"content": "Second note"}, headers=headers)

        detail = client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()
        timestamps = [e["created_at"] for e in detail["timeline"]]
        assert timestamps == sorted(timestamps)

    def test_empty_note_is_rejected(self, client):
        token = register_and_login(client, "case-empty-note@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Empty note test"}, headers=headers).json()
        response = client.post(f"/api/v1/cases/{case['id']}/notes", json={"content": ""}, headers=headers)
        assert response.status_code == 422


class TestCaseListing:
    def test_filter_by_status(self, client):
        token = register_and_login(client, "case-filter@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        c1 = client.post("/api/v1/cases", json={"title": "Open case"}, headers=headers).json()
        c2 = client.post("/api/v1/cases", json={"title": "Will be resolved"}, headers=headers).json()
        client.patch(f"/api/v1/cases/{c2['id']}", json={"status": "resolved"}, headers=headers)

        open_cases = client.get("/api/v1/cases?status=open", headers=headers).json()
        resolved_cases = client.get("/api/v1/cases?status=resolved", headers=headers).json()

        assert any(c["id"] == c1["id"] for c in open_cases)
        assert not any(c["id"] == c2["id"] for c in open_cases)
        assert any(c["id"] == c2["id"] for c in resolved_cases)
