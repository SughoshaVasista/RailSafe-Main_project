from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import build_engine, build_session_factory
from app import models  # noqa: F401 - register all model metadata
from app.config import Settings
from app.main import create_app
from app.models import User
from app.security.passwords import hash_password


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = build_engine(f"sqlite:///{(tmp_path / 'amrin-tests.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        yield engine, factory
    finally:
        engine.dispose()


@pytest.fixture
def auth_client(tmp_path: Path):
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
