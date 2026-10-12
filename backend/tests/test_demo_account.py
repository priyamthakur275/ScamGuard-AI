import pytest

from app_service.core.config import get_settings
from app_service.db.postgres.models import Message, User


@pytest.fixture
def demo_enabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "DEMO_ACCOUNT_ENABLED", True)


def _login(client):
    resp = client.post("/api/v1/auth/demo-login")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_demo_login_disabled_by_default(client):
    assert client.post("/api/v1/auth/demo-login").status_code == 404


def test_demo_login_creates_account_with_real_sample_scans(client, db_session, demo_enabled):
    headers = _login(client)
    me = client.get("/api/v1/users/me", headers=headers).json()
    assert me["email"] == get_settings().DEMO_ACCOUNT_EMAIL
    user = db_session.query(User).filter_by(email=me["email"]).one()
    scans = db_session.query(Message).filter_by(user_id=user.id).count()
    assert scans >= 5
    cases = client.get("/api/v1/cases", headers=headers).json()
    assert len(cases) == 1

    # A second sign-in reuses the account and does not duplicate samples.
    _login(client)
    assert db_session.query(User).filter_by(email=me["email"]).count() == 1
    assert db_session.query(Message).filter_by(user_id=user.id).count() == scans


def test_demo_account_cannot_change_password_or_be_deleted(client, demo_enabled):
    headers = _login(client)
    r = client.patch("/api/v1/users/me/password", headers=headers,
                     json={"current_password": "x", "new_password": "NewStrongPass1"})
    assert r.status_code == 403
    assert client.delete("/api/v1/users/me", headers=headers).status_code == 403
    assert client.patch("/api/v1/users/me", headers=headers, json={"full_name": "Hacked"}).status_code == 403
    # Theme and other preferences are still allowed.
    assert client.patch("/api/v1/users/me", headers=headers, json={"preferences": {"theme": "dark"}}).status_code == 200
