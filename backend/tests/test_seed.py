from sqlalchemy import func, select

from app.models import Alert, AlertHistory, DecisionState, Device, EventLog, MaintenanceTask, SensorReading, Track, Train, User
from app.services.demo_seed import seed_demo


def _counts(session) -> dict[str, int]:
    models = {
        "users": User,
        "alerts": Alert,
        "alert_history": AlertHistory,
        "devices": Device,
        "sensor_readings": SensorReading,
        "tasks": MaintenanceTask,
        "tracks": Track,
        "trains": Train,
        "decisions": DecisionState,
        "events": EventLog,
    }
    return {name: session.scalar(select(func.count()).select_from(model)) for name, model in models.items()}


def test_demo_seed_is_idempotent_and_explicitly_marked(db) -> None:
    _engine, factory = db
    with factory.begin() as session:
        first_insert = seed_demo(session)
    with factory.begin() as session:
        first_counts = _counts(session)
        second_insert = seed_demo(session)
    with factory.begin() as session:
        second_counts = _counts(session)
        assert session.get(Alert, "ALT-102").status == "ACTIVE"
        assert session.get(Alert, "ALT-104").status == "RESOLVED"
        assert session.get(User, "worker-01").password_hash is None
        assert all(item.source == "demo" for item in session.scalars(select(Alert)).all())
        assert all(item.source == "demo" for item in session.scalars(select(Device)).all())
        assert all(item.source == "demo" for item in session.scalars(select(SensorReading)).all())
        assert all(item.source == "demo" for item in session.scalars(select(Track)).all())
        assert all(item.source == "demo" for item in session.scalars(select(Train)).all())
        assert session.get(DecisionState, "latest").source == "demo"
    assert sum(first_insert.values()) > 0
    assert sum(second_insert.values()) == 0
    assert first_counts == second_counts
