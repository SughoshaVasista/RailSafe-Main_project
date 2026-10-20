from sqlalchemy import select

from app.models import EventLog, User
from app.security.passwords import verify_password

def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, username: str, password: str) -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _managed_user(**overrides):
    user = {
        "name": "Second Administrator",
        "username": "second-admin",
        "email": "second.admin@example.com",
        "password": "NewAdminPassphrase!2026",
        "role": "admin",
        "city": "Bengaluru",
    }
    user.update(overrides)
    return user


def test_admin_can_create_admin_and_new_admin_can_login(auth_client) -> None:
    client, factory, _app = auth_client
    admin = _login(client, "admin-test", "AdminPassphrase!2026")
    response = client.post("/api/users", json=_managed_user(), headers=_headers(admin["token"]))

    assert response.status_code == 201, response.text
    created = response.json()
    assert created["name"] == "Second Administrator"
    assert created["username"] == "second-admin"
    assert created["email"] == "second.admin@example.com"
    assert created["role"] == "admin"
    assert created["approval_status"] == "approved"
    assert created["status"] == "ACTIVE"
    assert created["city"] == "bengaluru"
    assert "password_hash" not in response.text

    logged_in = _login(client, "second-admin", "NewAdminPassphrase!2026")
    assert logged_in["role"] == "admin"
    assert client.get("/api/users", headers=_headers(logged_in["token"])).status_code == 200

    with factory() as session:
        user = session.scalar(select(User).where(User.email == "second.admin@example.com"))
        assert user is not None
        assert user.password_hash != "NewAdminPassphrase!2026"
        assert verify_password("NewAdminPassphrase!2026", user.password_hash)
        event = session.scalar(select(EventLog).where(EventLog.object_id == user.id))
        assert event is not None and event.action == "account_created_by_admin"
        assert "password" not in str(event.details)


def test_only_admin_can_list_and_create_managed_users(auth_client) -> None:
    client, _factory, _app = auth_client
    worker = _login(client, "worker-test", "WorkerPassphrase!2026")
    payload = _managed_user()

    assert client.get("/api/users").status_code == 401
    assert client.post("/api/users", json=payload).status_code == 401
    assert client.get("/api/users", headers=_headers(worker["token"])).status_code == 403
    denied = client.post("/api/users", json=payload, headers=_headers(worker["token"]))
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"


def test_managed_user_creation_rejects_duplicates_and_invalid_fields(auth_client) -> None:
    client, _factory, _app = auth_client
    admin = _login(client, "admin-test", "AdminPassphrase!2026")
    headers = _headers(admin["token"])

    assert client.post("/api/users", json=_managed_user(), headers=headers).status_code == 201
    duplicate_email = client.post("/api/users", json=_managed_user(username="another-admin"), headers=headers)
    assert duplicate_email.status_code == 409
    duplicate_username = client.post(
        "/api/users", json=_managed_user(email="different@example.com", username="SECOND-ADMIN"), headers=headers
    )
    assert duplicate_username.status_code == 409

    invalid_password = client.post("/api/users", json=_managed_user(password="short"), headers=headers)
    assert invalid_password.status_code == 422
    invalid_role = client.post("/api/users", json=_managed_user(role="operator"), headers=headers)
    assert invalid_role.status_code == 422
    invalid_username = client.post("/api/users", json=_managed_user(username="not valid"), headers=headers)
    assert invalid_username.status_code == 422


def test_admin_can_create_worker_and_activate_or_deactivate_accounts(auth_client) -> None:
    client, _factory, _app = auth_client
    admin = _login(client, "admin-test", "AdminPassphrase!2026")
    headers = _headers(admin["token"])
    response = client.post(
        "/api/users",
        json=_managed_user(name="Managed Worker", username="managed-worker", email="managed@example.com", role="worker"),
        headers=headers,
    )
    assert response.status_code == 201
    worker = response.json()
    assert worker["role"] == "worker"
    assert worker["worker_id"].startswith("WKR-")
    assert _login(client, "managed-worker", "NewAdminPassphrase!2026")["role"] == "worker"

    deactivated = client.patch(f"/api/users/{worker['id']}/status", json={"is_active": False}, headers=headers)
    assert deactivated.status_code == 200 and deactivated.json()["status"] == "INACTIVE"
    assert client.post("/api/auth/login", json={
        "username": "managed-worker", "password": "NewAdminPassphrase!2026",
    }).status_code == 401
    activated = client.patch(f"/api/users/{worker['id']}/status", json={"is_active": True}, headers=headers)
    assert activated.status_code == 200 and activated.json()["status"] == "ACTIVE"


def test_admin_status_changes_prevent_self_or_last_admin_lockout(auth_client) -> None:
    client, _factory, _app = auth_client
    admin = _login(client, "admin-test", "AdminPassphrase!2026")
    headers = _headers(admin["token"])

    self_deactivation = client.patch(
        "/api/users/USER-admin-test/status", json={"is_active": False}, headers=headers,
    )
    assert self_deactivation.status_code == 409
    assert self_deactivation.json()["error"]["code"] == "self_deactivation"

    other_admin = client.post("/api/users", json=_managed_user(), headers=headers).json()
    deactivated = client.patch(
        f"/api/users/{other_admin['id']}/status", json={"is_active": False}, headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"


