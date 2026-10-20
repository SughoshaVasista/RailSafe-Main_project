from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models import Alert, AlertHistory, EventLog, MlOriginEvent
from app.services.demo_seed import seed_demo

JWT_SECRET = "ml-ingestion-tests-jwt-secret-longer-than-32-bytes"
INGEST_TOKEN = "ml-ingestion-tests-token"


def make_client(tmp_path, ml_token=INGEST_TOKEN):
    app = create_app(Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key=JWT_SECRET,
        ml_ingest_token=ml_token,
        database_url=f"sqlite:///{(tmp_path / 'ml-tests.db').as_posix()}",
    ))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory.begin() as session:
        seed_demo(session)
    return app


def payload(**changes):
    value = {
        "schema_version": "1.0",
        "source_event_id": "camera-evt-0042",
        "detected_at": "2026-10-20T10:30:00Z",
        "source": "rail-vision-v1",
        "device_id": "device-01",
        "defect": "rail_crack",
        "severity": "S2",
        "confidence": 0.94,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "gps_accuracy_m": 2.5,
        "track": "Track A",
        "chainage": "KM 12/4",
        "boxes": [{"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.2}],
        "sensor_fusion": {"vibration": "elevated"},
        "model_version": "vision-1.2",
        "inference_ms": 21.4,
    }
    value.update(changes)
    return value


def test_ingest_is_authenticated_atomic_and_idempotent(tmp_path):
    app = make_client(tmp_path)
    with TestClient(app) as client:
        url = "/api/integrations/ml/events"
        body = payload()
        assert client.post(url, json=body).status_code == 401
        assert client.post(url, json=body, headers={"X-ML-API-Key": "wrong"}).status_code == 401
        headers = {"X-ML-API-Key": INGEST_TOKEN}
        first = client.post(url, json=body, headers=headers)
        assert first.status_code == 201
        assert first.json()["duplicate"] is False
        second = client.post(url, json=body, headers=headers)
        assert second.status_code == 201
        assert second.json() == {**first.json(), "duplicate": True}
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count(Alert.id)).where(Alert.source == "ml_backend")) == 1
        assert session.scalar(select(func.count(MlOriginEvent.id))) == 1
        assert session.scalar(select(func.count(AlertHistory.id)).where(AlertHistory.source == "ml_backend")) == 1
        assert session.scalar(select(func.count(EventLog.id)).where(EventLog.source == "ml_backend")) == 1
        event = session.scalar(select(MlOriginEvent))
        assert event.payload["detection"]["boxes"]
        assert event.detected_at.isoformat().startswith("2026-10-20T10:30:00")
    app.state.engine.dispose()


def test_ingest_rejects_invalid_payload_and_external_image_urls(tmp_path):
    app = make_client(tmp_path)
    with TestClient(app) as client:
        headers = {"X-ML-API-Key": INGEST_TOKEN}
        assert client.post("/api/integrations/ml/events", json=payload(confidence=1.5), headers=headers).status_code == 422
        assert client.post("/api/integrations/ml/events", json=payload(detected_at="yesterday"), headers=headers).status_code == 422
        assert client.post("/api/integrations/ml/events", json=payload(image_url="https://example.invalid/frame.png"), headers=headers).status_code == 422
        assert client.post("/api/integrations/ml/events", json=payload(evidence_image_base64="dGVzdA=="), headers=headers).status_code == 422
        assert client.post("/api/integrations/ml/events", json=payload(device_id="missing"), headers=headers).status_code == 422
    app.state.engine.dispose()


def test_ingest_fails_closed_without_configured_token(tmp_path):
    app = make_client(tmp_path, ml_token="")
    with TestClient(app) as client:
        response = client.post("/api/integrations/ml/events", json=payload(), headers={"X-ML-API-Key": INGEST_TOKEN})
        assert response.status_code == 503
    app.state.engine.dispose()


def test_ingest_rolls_back_all_rows_on_database_failure(tmp_path):
    app = make_client(tmp_path)

    def fail_before_flush(session, _flush_context, _instances):
        if any(isinstance(row, MlOriginEvent) for row in session.new):
            raise RuntimeError("simulated database write failure")

    event.listen(Session, "before_flush", fail_before_flush)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/integrations/ml/events",
                json=payload(),
                headers={"X-ML-API-Key": INGEST_TOKEN},
            )
            assert response.status_code == 500
        with app.state.session_factory() as session:
            assert session.scalar(select(func.count(Alert.id)).where(Alert.source == "ml_backend")) == 0
            assert session.scalar(select(func.count(MlOriginEvent.id))) == 0
            assert session.scalar(select(func.count(AlertHistory.id)).where(AlertHistory.source == "ml_backend")) == 0
            assert session.scalar(select(func.count(EventLog.id)).where(EventLog.source == "ml_backend")) == 0
    finally:
        event.remove(Session, "before_flush", fail_before_flush)
        app.state.engine.dispose()
