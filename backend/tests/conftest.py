from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import build_engine, build_session_factory
from app import models  # noqa: F401 - register all model metadata


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = build_engine(f"sqlite:///{(tmp_path / 'amrin-tests.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        yield engine, factory
    finally:
        engine.dispose()
