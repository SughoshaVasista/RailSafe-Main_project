from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models import User
from app.services.demo_seed import seed_demo

SECRET = "phase-five-telemetry-test-secret-longer-than-32-bytes"


@pytest.fixture
def telemetry_client(tmp_path):
    app = create_app(Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key=SECRET,
        database_url=f"sqlite:///{(tmp_path / 'telemetry-tests.db').as_posix()}",
    ))
    Base.metadata.create_all(app.state.engine)
    factory = app.state.session_factory
    with factory.begin() as session:
        seed_demo(session)
        session.add(User(
            id="telemetry-admin", name="Telemetry Admin", email="telemetry-admin@example.com",
            role="admin", approval_status="approved", is_active=True, source="test",
        ))
    with TestClient(app) as client:
        yield client, factory, app
    app.state.engine.dispose()


def token(user_id: str) -> dict[str, str]:
    value = jwt.encode({
        "sub": user_id,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
    }, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {value}"}


def test_devices_sensors_history_and_diagnostics(telemetry_client) -> None:
    client, _factory, _app = telemetry_client
    admin = token("telemetry-admin")
    device_response = client.get("/api/devices", headers=admin)
    assert device_response.status_code == 200
    device = device_response.json()["items"][0]
    assert device["id"] == "device-01" and device["source"] == "demo"

    latest = client.get("/api/devices/device-01/sensors", headers=admin)
    assert latest.status_code == 200
    assert {item["name"] for item in latest.json()["items"]} == {"Camera", "Ultrasonic", "Accelerometer", "Temperature", "GPS"}
    gps = next(item for item in latest.json()["items"] if item["name"] == "GPS")
    assert gps["accuracy"] == 2.8 and gps["satellites"] == 8 and gps["fix_type"] == "3D"

    history = client.get("/api/devices/device-01/sensors?history=true&window=24h", headers=admin)
    assert history.status_code == 200 and len(history.json()["items"]) == 5
    assert client.get("/api/devices/device-01/sensors?history=true&window=forever", headers=admin).status_code == 422
    assert client.get("/api/devices/missing/sensors", headers=admin).status_code == 404

    diagnostics = client.get("/api/devices/device-01/diagnostics", headers=admin)
    assert diagnostics.status_code == 200
    assert diagnostics.json()["device_id"] == "device-01"
    assert diagnostics.json()["network_status"] == "ONLINE"
    assert isinstance(diagnostics.json()["checks"], list)


def test_map_switch_and_simulation_decision_persistence(telemetry_client) -> None:
    client, factory, _app = telemetry_client
    worker = token("worker-01")
    tracks = client.get("/api/tracks?city=bengaluru", headers=worker)
    assert tracks.status_code == 200 and len(tracks.json()["items"]) == 2
    coordinates = tracks.json()["items"][0]["geometry"]["coordinates"]
    assert coordinates[0][0] > coordinates[0][1]  # GeoJSON uses [longitude, latitude].
    trains = client.get("/api/trains", headers=worker)
    assert trains.status_code == 200
    train = trains.json()["items"][0]
    assert train["id"] == "train-demo-01" and train["gps"]["satellites"] == 8
    assert client.get("/api/devices", headers=worker).status_code == 403

    demo_decision = client.get("/api/switch/status", headers=worker)
    assert demo_decision.status_code == 200
    assert demo_decision.json()["source"] == "demo" and demo_decision.json()["demo"] is True
    payload = {
        "timestamp": "2026-10-20T12:30:00Z",
        "train_id": "train_0",
        "switch_id": "switch_0",
        "position": 55.2,
        "action": "SWITCH",
        "action_level": "NORMAL",
        "target_track": "Track B",
        "confidence": 0.88,
        "rules_checked": [{"rule": "Target track is not occupied", "passed": True}],
        "raw_scores": {"A": 0.4, "B": 0.88},
        "reason": "Simulation selected Track B.",
    }
    denied = client.post("/api/switch/decision", json=payload, headers=worker)
    assert denied.status_code == 403
    accepted = client.post("/api/switch/decision", json=payload, headers=token("telemetry-admin"))
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["source"] == "simulation" and body["demo"] is False
    assert body["train_id"] == "train_0" and body["target_track"] == "Track B"
    assert body["raw_scores"] == {"A": 0.4, "B": 0.88}
    assert client.post("/api/switch/decision", json={**payload, "confidence": 1.2}, headers=token("telemetry-admin")).status_code == 422
    with factory() as session:
        from app.models import DecisionState
        persisted = session.get(DecisionState, "latest")
        assert persisted is not None and persisted.payload["train_id"] == "train_0"


def test_dashboard_aggregates_model_truth_and_empty_ai_state(telemetry_client) -> None:
    client, _factory, _app = telemetry_client
    admin = token("telemetry-admin")
    summary = client.get("/api/dashboard/summary?city=bengaluru", headers=admin)
    assert summary.status_code == 200
    assert summary.json()["active_alerts"] == 4
    assert summary.json()["s3_alerts"] == 1
    assert summary.json()["pending_tasks"] == 1
    assert summary.json()["online_devices"] == 1
    assert summary.json()["total_devices"] == 1

    events = client.get("/api/dashboard/event-log", headers=admin)
    assert events.status_code == 200
    assert events.json()["items"]
    assert "message" in events.json()["items"][0]
    assert client.get("/api/dashboard/summary", headers=token("worker-01")).status_code == 403

    model = client.get("/api/model/status", headers=admin)
    assert model.status_code == 200
    assert model.json()["model"]["loaded"] is False
    assert model.json()["model"]["inference_active"] is False
    detection = client.get("/api/ai/detection", headers=admin)
    assert detection.status_code == 200
    assert detection.json()["detection"]["status"] == "NO ML DETECTION"
    assert detection.json()["detection"]["confidence"] is None


def test_empty_telemetry_endpoints_are_safe_and_auth_required(tmp_path) -> None:
    app = create_app(Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key=SECRET,
        database_url=f"sqlite:///{(tmp_path / 'empty-telemetry.db').as_posix()}",
    ))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory.begin() as session:
        session.add(User(
            id="empty-admin", name="Empty Admin", email="empty-admin@example.com",
            role="admin", approval_status="approved", is_active=True, source="test",
        ))
    with TestClient(app) as client:
        # Empty operational endpoints are protected and do not fabricate data.
        assert client.get("/api/tracks").status_code == 401
        empty_tracks = client.get("/api/tracks", headers=token("empty-admin"))
        assert empty_tracks.status_code == 200 and empty_tracks.json()["items"] == []
        empty_ai = client.get("/api/ai/detection", headers=token("empty-admin"))
        assert empty_ai.status_code == 200 and empty_ai.json()["detection"]["confidence"] is None
        assert client.get("/api/ai/detection", headers=token("missing-user")).status_code == 401
    app.state.engine.dispose()
