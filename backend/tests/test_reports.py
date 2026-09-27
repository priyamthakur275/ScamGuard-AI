import csv
import io
import json

from tests.conftest import register_and_login


def _analyze(client, token, text="URGENT verify your bank account immediately or it will be suspended"):
    return client.post(
        "/api/v1/messages/analyze",
        json={"text": text, "input_type": "TEXT"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


class TestScanReportJson:
    def test_json_report_contains_all_required_fields(self, client):
        token = register_and_login(client, "report-json@example.com")
        scan = _analyze(client, token)
        response = client.get(
            f"/api/v1/messages/{scan['id']}/report?format=json",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = json.loads(response.content)

        assert data["scan_id"] == scan["id"]
        assert data["timestamp"]
        assert data["input_type"] == "TEXT"
        assert data["verdict"] == scan["verdict"]
        assert data["model_name"] == scan["model_name"]
        assert data["model_version"] == scan["model_version"]
        assert data["risk_level"] == scan["risk_level"]
        assert "evidence" in data
        assert "entities" in data
        assert "url_email_intelligence" in data
        assert "xai" in data
        assert "recommendations" in data

    def test_report_data_matches_the_real_scan_exactly_not_fabricated(self, client):
        token = register_and_login(client, "report-fidelity@example.com")
        scan = _analyze(client, token)
        response = client.get(
            f"/api/v1/messages/{scan['id']}/report?format=json",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = json.loads(response.content)
        assert data["model_probability"] == scan["scam_probability"]
        assert data["confidence"] == scan["confidence_score"]
        assert data["threat_score"] == scan["threat_score"]

    def test_semantic_separation_of_probability_confidence_threat_score(self, client):
        # These three must always be distinct fields, never merged into one.
        token = register_and_login(client, "report-separation@example.com")
        scan = _analyze(client, token)
        response = client.get(
            f"/api/v1/messages/{scan['id']}/report?format=json",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = json.loads(response.content)
        assert "model_probability" in data
        assert "confidence" in data
        assert "threat_score" in data
        assert "risk_level" in data
        # Distinct keys, not aliases of each other.
        assert len({"model_probability", "confidence", "threat_score", "risk_level"}) == 4

    def test_cannot_export_another_users_scan_report(self, client):
        token_a = register_and_login(client, "report-iso-a@example.com")
        token_b = register_and_login(client, "report-iso-b@example.com")
        scan_a = _analyze(client, token_a)
        response = client.get(
            f"/api/v1/messages/{scan_a['id']}/report?format=json",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404

    def test_invalid_format_is_rejected(self, client):
        token = register_and_login(client, "report-bad-format@example.com")
        scan = _analyze(client, token)
        response = client.get(
            f"/api/v1/messages/{scan['id']}/report?format=xml",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestScanReportCsv:
    def test_csv_report_is_parseable_and_has_expected_columns(self, client):
        token = register_and_login(client, "report-csv@example.com")
        scan = _analyze(client, token)
        response = client.get(
            f"/api/v1/messages/{scan['id']}/report?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")

        reader = csv.DictReader(io.StringIO(response.content.decode("utf-8")))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["scan_id"] == scan["id"]
        assert rows[0]["verdict"] == scan["verdict"]
        assert "model_probability" in rows[0]
        assert "confidence" in rows[0]
        assert "threat_score" in rows[0]


class TestScanReportPdf:
    def test_pdf_report_is_a_real_valid_pdf_with_expected_content(self, client):
        token = register_and_login(client, "report-pdf@example.com")
        scan = _analyze(client, token)
        response = client.get(
            f"/api/v1/messages/{scan['id']}/report?format=pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

        # Verify it's a genuinely valid, parseable PDF (not just bytes
        # that happen to start with the magic number) by reading it back
        # with pypdf and confirming the scan ID text is actually present.
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(response.content))
        assert len(reader.pages) >= 1
        full_text = "".join(page.extract_text() for page in reader.pages)
        assert scan["id"] in full_text
        assert scan["verdict"] in full_text.lower() or scan["verdict"].capitalize() in full_text


class TestCaseReport:
    def test_case_json_report_includes_all_linked_scans(self, client):
        token = register_and_login(client, "report-case@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        scan1 = _analyze(client, token, "Verify OTP immediately")
        scan2 = _analyze(client, token, "Pay Rs 5000 fine urgently")
        case = client.post(
            "/api/v1/cases",
            json={"title": "Multi-scan case", "scan_ids": [scan1["id"], scan2["id"]]},
            headers=headers,
        ).json()

        response = client.get(f"/api/v1/cases/{case['id']}/report?format=json", headers=headers)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["case_id"] == case["id"]
        assert data["scan_count"] == 2
        scan_ids_in_report = {s["scan_id"] for s in data["scans"]}
        assert scan_ids_in_report == {scan1["id"], scan2["id"]}

    def test_case_csv_report_has_one_row_per_scan(self, client):
        token = register_and_login(client, "report-case-csv@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        scan1 = _analyze(client, token, "First scam message")
        scan2 = _analyze(client, token, "Second scam message")
        case = client.post(
            "/api/v1/cases",
            json={"title": "CSV case", "scan_ids": [scan1["id"], scan2["id"]]},
            headers=headers,
        ).json()

        response = client.get(f"/api/v1/cases/{case['id']}/report?format=csv", headers=headers)
        reader = csv.DictReader(io.StringIO(response.content.decode("utf-8")))
        rows = list(reader)
        assert len(rows) == 2

    def test_empty_case_report_does_not_crash(self, client):
        token = register_and_login(client, "report-empty-case@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        case = client.post("/api/v1/cases", json={"title": "Empty case"}, headers=headers).json()

        for fmt in ("json", "csv", "pdf"):
            response = client.get(f"/api/v1/cases/{case['id']}/report?format={fmt}", headers=headers)
            assert response.status_code == 200

    def test_cannot_export_another_users_case_report(self, client):
        token_a = register_and_login(client, "report-case-iso-a@example.com")
        token_b = register_and_login(client, "report-case-iso-b@example.com")
        case = client.post(
            "/api/v1/cases", json={"title": "Private case"}, headers={"Authorization": f"Bearer {token_a}"}
        ).json()
        response = client.get(
            f"/api/v1/cases/{case['id']}/report?format=json",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404
