from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.db.base import Base
from app.main import create_app


def test_health_and_temporary_sqlite_configuration(tmp_path: Path) -> None:
    database_file = tmp_path / "amrin-test.db"
    settings = Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key="test-only-secret-not-used-for-auth",
        database_url=f"sqlite:///{database_file.as_posix()}",
        cors_origins="http://localhost:5173,http://localhost:4173",
        upload_folder=str(tmp_path / "uploads"),
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)

    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        with app.state.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1

    assert database_file.exists()
    app.state.engine.dispose()


def test_cors_preflight_and_malformed_json_are_handled(tmp_path: Path) -> None:
    app = create_app(Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key="test-only-secret-not-used-for-auth",
        database_url=f"sqlite:///{(tmp_path / 'cors-test.db').as_posix()}",
        cors_origins="http://localhost:5173",
    ))
    with TestClient(app) as client:
        preflight = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
        malformed = client.post("/api/auth/login", content="{", headers={"Content-Type": "application/json"})
        assert malformed.status_code == 422
        assert malformed.json()["error"]["code"] == "validation_error"
    app.state.engine.dispose()


def test_missing_database_fails_requests_without_exposing_error_details(tmp_path: Path) -> None:
    database_file = tmp_path / "missing-directory" / "amrin.db"
    app = create_app(Settings(
        _env_file=None,
        environment="production",
        jwt_secret_key="test-only-secret-not-used-for-auth",
        database_url=f"sqlite:///{database_file.as_posix()}",
    ))
    with TestClient(app, raise_server_exceptions=False) as client:
        failed = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
        assert failed.status_code == 500
        assert failed.json() == {"error": {"code": "internal_server_error", "message": "Internal server error"}}
        unavailable = client.get("/api/health")
        assert unavailable.status_code == 503
        assert unavailable.json() == {"status": "unavailable", "database": "unavailable"}
    app.state.engine.dispose()
