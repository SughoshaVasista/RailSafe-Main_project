from datetime import timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Alert,
    AlertHistory,
    DecisionState,
    Device,
    EventLog,
    MlOriginEvent,
    MaintenanceTask,
    SensorReading,
    TaskEvidence,
    Track,
    Train,
    User,
)
from app.schemas.serializers import serialize_user
from app.models.entities import utc_now


def test_models_persist_relationships_and_serialize_user_safely(db) -> None:
    _engine, factory = db
    with factory.begin() as session:
        worker = User(
            id="worker-test",
            worker_id="worker-test",
            name="Test Worker",
            email="worker@example.test",
            password_hash="never-serialize-this",
            role="worker",
            approval_status="approved",
            city="bengaluru",
        )
        device = Device(id="device-test", name="Test device", status="ONLINE", source="test")
        track = Track(
            id="track-test",
            name="Track Test",
            status="OPEN",
            occupancy="CLEAR",
            geometry={"type": "LineString", "coordinates": [[77.5, 12.9], [77.6, 13.0]]},
            source="test",
        )
        train = Train(id="train-test", latitude=12.9, longitude=77.5, source="test")
        alert = Alert(
            id="ALT-TEST",
            defect="Rail crack",
            severity="S3",
            status="DETECTED",
            confidence=0.9,
            latitude=12.9,
            longitude=77.5,
            source="test",
            assigned_worker=worker,
        )
        history = AlertHistory(alert=alert, actor=worker, action="created", new_status="DETECTED")
        task = MaintenanceTask(id="TASK-TEST", alert=alert, assigned_worker=worker, status="ASSIGNED", priority="S3")
        evidence = TaskEvidence(
            task=task,
            stored_filename="random-safe-name.png",
            original_filename="repair.png",
            mime_type="image/png",
            byte_size=128,
            uploaded_by=worker,
        )
        reading = SensorReading(device=device, name="Ultrasonic", status="ONLINE", numeric_value=18.4, unit="mm gap")
        decision = DecisionState(id="latest", train=train, action="MAINTAIN", source="test")
        event = EventLog(action="test", actor=worker, source="test")
        ml_event = MlOriginEvent(
            id="ML-TEST",
            source_namespace="test-device",
            source_event_id="event-1",
            device=device,
            alert=alert,
            payload={"schema_version": "1.0"},
            detected_at=utc_now(),
        )
        session.add_all([worker, device, track, train, alert, history, task, evidence, reading, decision, event, ml_event])
        session.flush()

        assert alert.assigned_worker.worker_id == "worker-test"
        assert task.alert.id == "ALT-TEST"
        assert task.evidence[0].mime_type == "image/png"
        assert device.readings[0].numeric_value == 18.4
        assert alert.history[0].actor.name == "Test Worker"
        assert track.geometry["coordinates"][0] == [77.5, 12.9]
        assert ml_event.alert_id == alert.id
        assert worker.created_at.tzinfo is not None or worker.created_at.tzinfo == timezone.utc
        serialized = serialize_user(worker)
        assert serialized["email"] == "worker@example.test"
        assert "password_hash" not in serialized
        assert "never-serialize-this" not in repr(serialized)


@pytest.mark.parametrize(
    "values",
    [
        {"severity": "S4", "status": "DETECTED", "confidence": 0.5},
        {"severity": "S2", "status": "NOT_A_STATE", "confidence": 0.5},
        {"severity": "S2", "status": "DETECTED", "confidence": 1.5},
    ],
)
def test_alert_constraints_reject_invalid_values(db, values) -> None:
    _engine, factory = db
    with factory() as session:
        session.add(Alert(id="ALT-BAD", defect="Bad input", source="test", **values))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
