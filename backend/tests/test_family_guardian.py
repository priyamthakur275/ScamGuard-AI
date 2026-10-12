from tests.conftest import register_and_login

SCAM = "URGENT: Your SBI account will be blocked today. Share the OTP sent to your phone at http://sbi-kyc-verify.xyz"
SAFE = "Hi, are you still free for lunch tomorrow at 1pm?"


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def test_full_guardian_flow_with_consent(client, db_session):
    mom = register_and_login(client, "mom@example.com")
    son = register_and_login(client, "son@example.com")

    # Before linking, the son sees nothing.
    client.post("/api/v1/messages/analyze", json={"text": SCAM}, headers=_h(mom))
    from datetime import datetime, timedelta, timezone
    from app_service.db.postgres.models import Prediction
    for p in db_session.query(Prediction).all():  # this scan happened an hour before linking
        p.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()
    r = client.post("/api/v1/family/guardians", json={"email": "Son@Example.com"}, headers=_h(mom))
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert client.get("/api/v1/family/alerts", headers=_h(son)).json() == []

    invites = client.get("/api/v1/family/protecting", headers=_h(son)).json()
    assert len(invites) == 1 and invites[0]["status"] == "pending"
    assert client.get("/api/v1/family/summary", headers=_h(son)).json()["pending_invitations"] == 1
    link_id = invites[0]["id"]
    assert client.post(f"/api/v1/family/links/{link_id}/accept", headers=_h(son)).json()["status"] == "active"

    # Only high-risk scans made after acceptance are shared.
    client.post("/api/v1/messages/analyze", json={"text": SCAM}, headers=_h(mom))
    client.post("/api/v1/messages/analyze", json={"text": SAFE}, headers=_h(mom))
    alerts = client.get("/api/v1/family/alerts", headers=_h(son)).json()
    assert len(alerts) == 1 and alerts[0]["person_email"] == "mom@example.com"
    assert alerts[0]["threat_score"] >= 0.7 and "SBI" in alerts[0]["preview"]
    assert client.get("/api/v1/family/guardians", headers=_h(mom)).json()[0]["status"] == "active"

    # Either side can end it; then nothing is shared.
    assert client.delete(f"/api/v1/family/links/{link_id}", headers=_h(mom)).status_code == 204
    assert client.get("/api/v1/family/alerts", headers=_h(son)).json() == []


def test_strangers_cannot_accept_or_see(client):
    a = register_and_login(client, "a@example.com")
    stranger = register_and_login(client, "stranger@example.com")
    link = client.post("/api/v1/family/guardians", json={"email": "b@example.com"}, headers=_h(a)).json()
    assert client.post(f"/api/v1/family/links/{link['id']}/accept", headers=_h(stranger)).status_code == 404
    assert client.delete(f"/api/v1/family/links/{link['id']}", headers=_h(stranger)).status_code == 404


def test_invite_validation(client):
    a = register_and_login(client, "solo@example.com")
    assert client.post("/api/v1/family/guardians", json={"email": "solo@example.com"}, headers=_h(a)).status_code in (400, 422)
    client.post("/api/v1/family/guardians", json={"email": "x@example.com"}, headers=_h(a))
    assert client.post("/api/v1/family/guardians", json={"email": "x@example.com"}, headers=_h(a)).status_code == 409
    assert client.get("/api/v1/family/alerts").status_code == 401
