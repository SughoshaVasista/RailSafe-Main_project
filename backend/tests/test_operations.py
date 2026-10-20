from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import models  # noqa: F401
from app.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models import Alert, AlertHistory, EventLog, MaintenanceTask, TaskEvidence, User

SECRET = "phase-four-operations-test-secret-longer-than-32-bytes"
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"test-image-payload"


@pytest.fixture
def operations_client(tmp_path):
    app = create_app(Settings(
        _env_file=None,
        environment="test",
        jwt_secret_key=SECRET,
        database_url=f"sqlite:///{(tmp_path / 'operations-tests.db').as_posix()}",
        upload_folder=str(tmp_path / "uploads"),
        max_content_length=4096,
    ))
    Base.metadata.create_all(app.state.engine)
    factory = app.state.session_factory
    with factory.begin() as session:
        session.add_all([
            User(id="admin-ops", name="Admin", email="ops-admin@example.com", role="admin", approval_status="approved", is_active=True, source="test"),
            User(id="worker-ops", name="Worker One", email="ops-worker@example.com", role="worker", approval_status="approved", worker_id="WKR-OPS-01", city="bengaluru", is_active=True, source="test"),
            User(id="worker-other", name="Worker Two", email="ops-other@example.com", role="worker", approval_status="approved", worker_id="WKR-OPS-02", city="mysuru", is_active=True, source="test"),
            User(id="worker-pending", name="Pending", email="ops-pending@example.com", role="worker", approval_status="pending", is_active=True, source="test"),
            Alert(id="ALT-DETECTED", defect="rail crack", severity="S3", status="DETECTED", confidence=0.94, track="BLR-A", city="bengaluru", source="test", detected_at=datetime.now(timezone.utc)),
            Alert(id="ALT-ACK", defect="joint wear", severity="S2", status="ACKNOWLEDGED", track="BLR-B", city="bengaluru", source="test", detected_at=datetime.now(timezone.utc)),
            Alert(id="ALT-OTHER", defect="surface damage", severity="S1", status="ACKNOWLEDGED", track="MYS-A", city="mysuru", source="test", detected_at=datetime.now(timezone.utc)),
            Alert(id="ALT-REPAIR", defect="ballast shift", severity="S2", status="UNDER_REPAIR", track="BLR-C", city="bengaluru", source="test", detected_at=datetime.now(timezone.utc)),
        ])
    with TestClient(app) as client:
        yield client, factory, app
    app.state.engine.dispose()


def _auth(client, user_id: str, role: str) -> dict[str, str]:
    token = jwt.encode({
        "sub": user_id,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
    }, SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_alert_filters_detail_history_and_admin_actions(operations_client) -> None:
    client, factory, _app = operations_client
    admin = _auth(client, "admin-ops", "admin")
    worker = _auth(client, "worker-ops", "worker")
    response = client.get("/api/alerts", params={"severity": "S3", "city": "bengaluru", "type": "crack"}, headers=worker)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["ALT-DETECTED"]
    worker_alerts = client.get("/api/alerts", headers=worker)
    assert "ALT-OTHER" not in {item["id"] for item in worker_alerts.json()["items"]}
    assert client.get("/api/alerts/ALT-OTHER", headers=worker).status_code == 404
    assert client.get("/api/alerts", params={"severity": "S9"}, headers=worker).status_code == 422
    assert client.get("/api/alerts/missing", headers=admin).status_code == 404
    assert client.post("/api/alerts/ALT-DETECTED/acknowledge", headers=worker).status_code == 403

    changed = client.post("/api/alerts/ALT-DETECTED/acknowledge", headers=admin).json()
    assert changed["status"] == "ACKNOWLEDGED"
    history = client.get("/api/alerts/ALT-DETECTED/history", headers=admin)
    assert history.status_code == 200
    assert history.json()["items"][0]["new_status"] == "ACKNOWLEDGED"
    assert history.json()["items"][0]["action"] == "alert_acknowledged"

    priority = client.post("/api/alerts/ALT-DETECTED/priority", json={"severity": "S1"}, headers=admin)
    assert priority.status_code == 200 and priority.json()["severity"] == "S1"
    assigned = client.post("/api/alerts/ALT-DETECTED/assign", json={"worker_id": "WKR-OPS-01"}, headers=admin)
    assert assigned.status_code == 200 and assigned.json()["status"] == "ASSIGNED"
    assert assigned.json()["assigned_worker_id"] == "WKR-OPS-01"
    invalid_worker = client.post("/api/alerts/ALT-OTHER/assign", json={"worker_id": "worker-pending"}, headers=admin)
    assert invalid_worker.status_code == 404
    assert client.post("/api/alerts/ALT-OTHER/resolve", headers=admin).status_code == 409

    false_positive = client.post("/api/alerts/ALT-OTHER/false-positive", headers=admin)
    assert false_positive.status_code == 200
    assert false_positive.json()["status"] == "FALSE_POSITIVE"
    resolved = client.post("/api/alerts/ALT-REPAIR/resolve", json={"notes": "Inspected and repaired"}, headers=admin)
    assert resolved.status_code == 200 and resolved.json()["status"] == "RESOLVED"
    reopened = client.post("/api/alerts/ALT-OTHER/reopen", headers=admin)
    assert reopened.status_code == 404  # No unrequested reopen endpoint is exposed in this phase.
    with factory() as session:
        actions = set(session.scalars(select(AlertHistory.action)).all())
        assert {"alert_acknowledged", "alert_priority_changed", "alert_assigned", "alert_marked_false_positive"} <= actions


def test_task_creation_ownership_transitions_and_repair_evidence(operations_client) -> None:
    client, factory, app = operations_client
    admin = _auth(client, "admin-ops", "admin")
    worker = _auth(client, "worker-ops", "worker")
    other_worker = _auth(client, "worker-other", "worker")

    created = client.post("/api/tasks", json={
        "alert_id": "ALT-ACK", "worker_id": "WKR-OPS-01", "status": "ASSIGNED", "notes": "Check the joint",
    }, headers=admin)
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["alert_id"] == "ALT-ACK" and task["worker_id"] == "WKR-OPS-01"
    assert task["defect"] == "joint wear" and task["priority"] == "S2"
    duplicate = client.post("/api/tasks", json={"alert_id": "ALT-ACK", "worker_id": "worker-ops"}, headers=admin)
    assert duplicate.status_code == 409

    own_tasks = client.get("/api/tasks?worker_id=WKR-OPS-02", headers=worker)
    assert [item["id"] for item in own_tasks.json()["items"]] == [task["id"]]
    assert client.get("/api/tasks", headers=other_worker).json()["items"] == []
    assert client.put(f"/api/tasks/{task['id']}/status", json={"status": "ACCEPTED"}, headers=other_worker).status_code == 403
    assert client.put(f"/api/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"}, headers=worker).status_code == 409

    accepted = client.put(f"/api/tasks/{task['id']}/status", json={"status": "ACCEPTED"}, headers=worker)
    assert accepted.status_code == 200 and accepted.json()["status"] == "ACCEPTED"
    in_progress = client.put(f"/api/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"}, headers=worker)
    assert in_progress.status_code == 200 and in_progress.json()["status"] == "IN_PROGRESS"
    assert in_progress.json()["evidence"] == []

    no_evidence = client.put(f"/api/tasks/{task['id']}/status", json={"status": "COMPLETED"}, headers=worker)
    assert no_evidence.status_code == 409
    assert no_evidence.json()["error"]["code"] == "repair_evidence_required"
    bad_mime = client.post(
        f"/api/tasks/{task['id']}/evidence", headers=worker,
        files={"file": ("note.txt", b"not an image", "text/plain")},
    )
    assert bad_mime.status_code == 415
    bad_signature = client.post(
        f"/api/tasks/{task['id']}/evidence", headers=worker,
        files={"file": ("bad.png", b"not really png", "image/png")},
    )
    assert bad_signature.status_code == 415
    too_large = client.post(
        f"/api/tasks/{task['id']}/evidence", headers=worker,
        files={"file": ("large.png", PNG_HEADER + b"x" * 5000, "image/png")},
    )
    assert too_large.status_code == 413

    upload = client.post(
        f"/api/tasks/{task['id']}/evidence", headers=worker,
        files={"file": ("repair.png", PNG_HEADER, "image/png")},
        data={"notes": "Repair complete", "evidence_type": "repair"},
    )
    assert upload.status_code == 201, upload.text
    metadata = upload.json()
    assert metadata["mime_type"] == "image/png"
    assert metadata["original_filename"] == "repair.png"
    assert metadata["url"].startswith(f"/api/tasks/{task['id']}/evidence/")
    assert metadata["filename"] != "repair.png"

    forbidden_file = client.get(metadata["url"], headers=other_worker)
    assert forbidden_file.status_code == 403
    image_file = client.get(metadata["url"], headers=worker)
    assert image_file.status_code == 200 and image_file.content == PNG_HEADER
    assert image_file.headers["content-type"] == "image/png"
    completed = client.put(f"/api/tasks/{task['id']}/status", json={"status": "COMPLETED"}, headers=worker)
    assert completed.status_code == 200 and completed.json()["status"] == "COMPLETED"
    assert completed.json()["evidence"][0]["evidence_type"] == "repair"
    assert completed.json()["evidence"][0]["url"] == metadata["url"]
    assert client.put(f"/api/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"}, headers=worker).status_code == 409

    with factory() as session:
        alert = session.get(Alert, "ALT-ACK")
        assert alert.status == "RESOLVED"
        evidence = session.scalar(select(TaskEvidence).where(TaskEvidence.task_id == task["id"]))
        assert evidence is not None and evidence.byte_size == len(PNG_HEADER)
        audit = list(session.scalars(select(AlertHistory).where(AlertHistory.alert_id == alert.id)).all())
        assert any(item.changes and "task_status" in item.changes for item in audit)
        assert session.scalar(select(EventLog.id).where(EventLog.object_type == "task")) is not None
    assert app.state.settings.upload_folder


def test_evidence_requires_authorized_assigned_worker_and_active_task(operations_client) -> None:
    client, _factory, _app = operations_client
    admin = _auth(client, "admin-ops", "admin")
    worker = _auth(client, "worker-ops", "worker")
    created = client.post("/api/tasks", json={"alert_id": "ALT-ACK", "worker_id": "worker-ops"}, headers=admin).json()
    path = f"/api/tasks/{created['id']}/evidence"
    not_started = client.post(path, headers=worker, files={"file": ("photo.png", PNG_HEADER, "image/png")})
    assert not_started.status_code == 409
    missing = client.get(f"/api/tasks/{created['id']}/evidence/missing", headers=worker)
    assert missing.status_code == 404
