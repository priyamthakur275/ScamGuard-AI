from app_service.core.security import create_access_token


from tests.conftest import register_and_login  # noqa: F401 (re-exported for this module's tests)


def test_regular_user_cannot_list_users(client):
    token = register_and_login(client, "plainuser@example.com")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"


def test_admin_can_list_users(client, admin_user):
    token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_can_get_specific_user(client, admin_user, regular_user):
    token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    response = client.get(
        f"/api/v1/users/{regular_user.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_regular_user_cannot_get_other_user(client, regular_user):
    token = create_access_token(subject=str(regular_user.id), role=regular_user.role.value)
    response = client.get(
        f"/api/v1/users/{regular_user.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_admin_can_promote_user_role(client, admin_user, regular_user):
    admin_token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    response = client.patch(
        f"/api/v1/users/{regular_user.id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_regular_user_cannot_promote_role(client, regular_user):
    token = create_access_token(subject=str(regular_user.id), role=regular_user.role.value)
    response = client.patch(
        f"/api/v1/users/{regular_user.id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_can_deactivate_user(client, admin_user, regular_user, db_session):
    admin_token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    response = client.delete(
        f"/api/v1/users/{regular_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    db_session.refresh(regular_user)
    assert regular_user.is_active is False


def test_deactivated_user_cannot_authenticate(client, admin_user, regular_user):
    admin_token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    client.delete(
        f"/api/v1/users/{regular_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "UserPass1"},
    )
    assert login_resp.status_code == 401
