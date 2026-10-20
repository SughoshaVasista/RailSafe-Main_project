from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
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

    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        with app.state.engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1

    assert database_file.exists()
    app.state.engine.dispose()
