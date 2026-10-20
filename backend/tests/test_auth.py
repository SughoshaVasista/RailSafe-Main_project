from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import models  # noqa: F401
from app.config import Settings
from app.db.base import Base
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import EventLog, User
from app.security.passwords import hash_password


@pytest.fixture
def auth_client(tmp_path):
    database_file = tmp_path / "auth-tests.db"
    app = create_app(Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key="test-secret-for-auth-tests-only-32-bytes-minimum",
        jwt_access_token_minutes=60,
        database_url=f"sqlite:///{database_file.as_posix()}",
        upload_folder=str(tmp_path / "uploads"),
    ))
    Base.metadata.create_all(app.state.engine)
    factory = app.state.session_factory
    with factory.begin() as session:
        session.add(User(
            id="USER-admin-test", name="Test Admin", email="admin@example.test",
            username="admin-test", password_hash=hash_password("AdminPassphrase!2026"),
            role="admin", approval_status="approved", is_active=True, source="test",
        ))
        session.add(User(
            id="USER-worker-test", name="Test Worker", email="worker@example.test",
            username="worker-test", password_hash=hash_password("WorkerPassphrase!2026"),
            role="worker", approval_status="approved", worker_id="WKR-TEST-001",
            is_active=True, city="bengaluru", source="test",
        ))
    with TestClient(app) as client:
        yield client, factory, app
    app.state.engine.dispose()


def _login(client: TestClient, username: str, password: str) -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_by_email_and_username_wrong_password_and_me(auth_client) -> None:
    client, _factory, _app = auth_client
    admin = _login(client, "ADMIN@example.test", "AdminPassphrase!2026")
    assert admin["role"] == "admin"
    assert admin["name"] == "Test Admin"
    assert admin["worker_id"] is None
    assert "password" not in admin and "password_hash" not in admin

    worker = _login(client, "worker-test", "WorkerPassphrase!2026")
    assert worker["worker_id"] == "WKR-TEST-001"
    me = client.get("/api/auth/me", headers=_headers(worker["token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "worker@example.test"
    assert "password_hash" not in me.text

    bad_password = client.post("/api/auth/login", json={"username": "worker-test", "password": "wrong"})
    assert bad_password.status_code == 401
    assert bad_password.json()["error"]["code"] == "invalid_credentials"


def test_registration_stays_pending_worker_even_for_admin_request(auth_client) -> None:
    client, factory, _app = auth_client
    response = client.post("/api/auth/register", json={
        "name": "  New   Applicant ", "email": " NEW@Example.com ",
        "password": "LongEnoughPassword!", "city": " Bengaluru ", "role": "admin",
    })
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["name"] == "New Applicant"
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["city"] == "bengaluru"
    assert body["user"]["role"] == "worker"
    assert body["user"]["approval_status"] == "pending"
    assert "password_hash" not in response.text
    with factory() as session:
        user = session.scalar(select(User).where(User.email == "new@example.com"))
        assert user is not None and user.password_hash != "LongEnoughPassword!"
        event = session.scalar(select(EventLog).where(EventLog.object_id == user.id))
        assert event is not None
        assert event.details == {"requested_role": "admin", "assigned_role": "worker"}

    pending_login = client.post("/api/auth/login", json={
        "username": "new@example.com", "password": "LongEnoughPassword!",
    })
    assert pending_login.status_code == 403
    assert pending_login.json()["error"]["code"] == "pending_approval"
    duplicate = client.post("/api/auth/register", json={
        "name": "Another", "email": "new@example.com",
        "password": "LongEnoughPassword!", "city": "bengaluru", "role": "worker",
    })
    assert duplicate.status_code == 409


def test_auth_tokens_require_valid_signature_and_unexpired_claims(auth_client) -> None:
    client, _factory, _app = auth_client
    missing = client.get("/api/auth/me")
    assert missing.status_code == 401

    invalid = client.get("/api/auth/me", headers=_headers("not-a-jwt"))
    assert invalid.status_code == 401

    expired = jwt.encode({
        "sub": "USER-admin-test",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }, "test-secret-for-auth-tests-only-32-bytes-minimum", algorithm="HS256")
    response = client.get("/api/auth/me", headers=_headers(expired))
    assert response.status_code == 401

    wrong_type = jwt.encode({
        "sub": "USER-admin-test", "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, "test-secret-for-auth-tests-only-32-bytes-minimum", algorithm="HS256")
    assert client.get("/api/auth/me", headers=_headers(wrong_type)).status_code == 401


def test_admin_approval_rejection_workers_and_role_enforcement(auth_client) -> None:
    client, factory, _app = auth_client
    admin = _login(client, "admin-test", "AdminPassphrase!2026")
    worker = _login(client, "worker-test", "WorkerPassphrase!2026")
    admin_headers = _headers(admin["token"])
    worker_headers = _headers(worker["token"])

    pending = client.post("/api/auth/register", json={
        "name": "Approved Worker", "email": "approve@example.com",
        "password": "WorkerApprovalPass!", "city": "mysuru", "role": "operator",
    }).json()["user"]
    denied = client.get("/api/users/pending", headers=worker_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"

    pending_list = client.get("/api/users/pending", headers=admin_headers)
    assert pending_list.status_code == 200
    assert any(item["id"] == pending["id"] for item in pending_list.json()["items"])

    approved_response = client.post(f"/api/users/{pending['id']}/approve", headers=admin_headers)
    assert approved_response.status_code == 200
    approved = approved_response.json()
    assert approved["role"] == "worker"
    assert approved["approval_status"] == "approved"
    assert approved["worker_id"].startswith("WKR-")
    assert "password_hash" not in approved_response.text
    assert client.post(f"/api/users/{pending['id']}/approve", headers=admin_headers).status_code == 409

    workers = client.get("/api/workers", headers=admin_headers)
    assert workers.status_code == 200
    assert any(item["worker_id"] == approved["worker_id"] for item in workers.json()["items"])
    assert client.get("/api/workers", headers=worker_headers).status_code == 403

    rejected = client.post("/api/auth/register", json={
        "name": "Rejected Worker", "email": "reject@example.com",
        "password": "WorkerRejectPass!", "city": "hubballi", "role": "worker",
    }).json()["user"]
    rejection = client.post(f"/api/users/{rejected['id']}/reject", headers=admin_headers)
    assert rejection.status_code == 200
    assert rejection.json()["approval_status"] == "rejected"
    rejected_login = client.post("/api/auth/login", json={
        "username": "reject@example.com", "password": "WorkerRejectPass!",
    })
    assert rejected_login.status_code == 401

    with factory() as session:
        audit_actions = set(session.scalars(select(EventLog.action)).all())
        assert {"account_approved", "account_rejected"} <= audit_actions


def test_create_admin_cli_hides_password_and_refuses_second_admin(tmp_path, monkeypatch, capsys) -> None:
    from app import cli

    engine = build_engine(f"sqlite:///{(tmp_path / 'cli-admin.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    prompts = iter(["First Admin", "first@example.com", "first-admin"])
    secrets = iter(["FirstAdminSecurePassphrase!", "FirstAdminSecurePassphrase!"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(prompts))
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(secrets))

    cli._create_admin(factory)
    output = capsys.readouterr().out
    assert "first@example.com" in output
    assert "FirstAdminSecurePassphrase!" not in output
    with factory() as session:
        admin = session.scalar(select(User).where(User.email == "first@example.com"))
        assert admin is not None
        assert admin.role == "admin" and admin.approval_status == "approved"
        assert admin.password_hash != "FirstAdminSecurePassphrase!"

    with pytest.raises(SystemExit, match="administrator already exists"):
        cli._create_admin(factory)
    engine.dispose()
