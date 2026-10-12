from tests.conftest import register_and_login

SCAM = "URGENT: Your SBI account will be blocked today. Update KYC at http://sbi-kyc-verify.xyz and share the OTP. Call +91 9876543210."


def test_quick_check_needs_no_login_and_stores_nothing(client):
    r = client.post("/api/v1/public/quick-check", json={"text": SCAM})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verdict"] in {"scam", "phishing", "spam"}
    token = register_and_login(client, "qc@example.com")
    history = client.get("/api/v1/messages/history", headers={"Authorization": f"Bearer {token}"}).json()
    assert history == []


def test_quick_check_rejects_empty_and_huge_text(client):
    assert client.post("/api/v1/public/quick-check", json={"text": ""}).status_code == 422
    assert client.post("/api/v1/public/quick-check", json={"text": "a" * 2001}).status_code == 422


def test_phone_lookup_counts_only_own_scans(client):
    owner = {"Authorization": f"Bearer {register_and_login(client, 'owner@example.com')}"}
    other = {"Authorization": f"Bearer {register_and_login(client, 'other@example.com')}"}
    client.post("/api/v1/messages/analyze", json={"text": SCAM}, headers=owner)

    mine = client.get("/api/v1/messages/lookup/phone", params={"number": "98765 43210"}, headers=owner).json()
    assert mine["number"] == "+919876543210"
    assert mine["is_valid_indian_mobile"] is True
    assert mine["seen_count"] == 1 and mine["flagged_count"] == 1
    assert len(mine["scans"]) == 1

    theirs = client.get("/api/v1/messages/lookup/phone", params={"number": "+91 9876543210"}, headers=other).json()
    assert theirs["seen_count"] == 0


def test_phone_lookup_requires_login(client):
    assert client.get("/api/v1/messages/lookup/phone", params={"number": "9876543210"}).status_code == 401
