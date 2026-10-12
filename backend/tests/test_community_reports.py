from tests.conftest import register_and_login

NUMBER_MSG = "Hi, I am from the courier office, call me back on 9812345670 about your parcel."


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_report_is_counted_once_per_user_and_normalised(client):
    t1 = register_and_login(client, "rep1@example.com")
    r = client.post("/api/v1/community/reports", json={"indicator_type": "phone", "value": "+91 98123 45670"}, headers=_auth(t1))
    assert r.status_code == 201 and r.json()["report_count"] == 1 and r.json()["indicator_value"] == "+919812345670"
    again = client.post("/api/v1/community/reports", json={"indicator_type": "phone", "value": "09812345670"}, headers=_auth(t1))
    assert again.json()["report_count"] == 1 and again.json()["created"] is False
    t2 = register_and_login(client, "rep2@example.com")
    client.post("/api/v1/community/reports", json={"indicator_type": "phone", "value": "9812345670"}, headers=_auth(t2))
    look = client.get("/api/v1/community/lookup", params={"indicator_type": "phone", "value": "98123 45670"})
    assert look.status_code == 200 and look.json()["report_count"] == 2


def test_reporting_requires_login_and_valid_value(client):
    assert client.post("/api/v1/community/reports", json={"indicator_type": "phone", "value": "9812345670"}).status_code == 401
    t = register_and_login(client, "rep3@example.com")
    bad = client.post("/api/v1/community/reports", json={"indicator_type": "upi", "value": "not a upi"}, headers=_auth(t))
    assert bad.status_code in (400, 422)


def test_link_reports_use_the_domain(client):
    t = register_and_login(client, "rep4@example.com")
    r = client.post("/api/v1/community/reports", json={"indicator_type": "url", "value": "https://www.sbi-kyc-verify.xyz/login?id=1"}, headers=_auth(t))
    assert r.json()["indicator_value"] == "sbi-kyc-verify.xyz"


def test_reported_number_appears_on_scan_and_raises_score(client):
    before = client.post("/api/v1/public/quick-check", json={"text": NUMBER_MSG}).json()
    for i in range(3):
        tok = register_and_login(client, f"crowd{i}@example.com")
        client.post("/api/v1/community/reports", json={"indicator_type": "phone", "value": "9812345670"}, headers=_auth(tok))
    after = client.post("/api/v1/public/quick-check", json={"text": NUMBER_MSG}).json()
    reports = after["metadata"]["community_reports"]
    assert reports and reports[0]["report_count"] == 3
    assert after["threat_score"] > before["threat_score"]
    assert after["scam_probability"] == before["scam_probability"]  # the model's own number is untouched
    assert any("Reported as a scam by 3" in a for a in after["recommended_actions"])
