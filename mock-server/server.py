from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

# Temporary demo database. Replace this in-memory store with the production API/Firebase backend.
now = datetime.now(timezone.utc).isoformat()
alerts = [
    {"id": "ALT-102", "defect": "Crack", "severity": "S3", "track": "Track A", "chainage": "KM 12/4", "confidence": 0.94, "status": "ACTIVE", "latitude": 12.9719, "longitude": 77.5942, "sensors": ["Camera", "Ultrasonic", "Accelerometer"], "updated_at": now},
    {"id": "ALT-103", "defect": "Joint Gap", "severity": "S2", "track": "Track B", "chainage": "KM 13/2", "confidence": 0.87, "status": "ACKNOWLEDGED", "latitude": 12.9732, "longitude": 77.5961, "sensors": ["Camera", "Ultrasonic"], "updated_at": now},
    {"id": "ALT-104", "defect": "Surface Wear", "severity": "S1", "track": "Track A", "chainage": "KM 13/8", "confidence": 0.81, "status": "RESOLVED", "latitude": 12.9745, "longitude": 77.5980, "sensors": ["Camera"], "updated_at": now},
]
devices = [{"id": "device-01", "name": "RAILSAFE-01", "platform": "Raspberry Pi 5", "status": "ONLINE", "uptime": "3d 04h 18m", "updated_at": now}]
sensor_readings = [
    {"name": "Camera", "status": "ONLINE", "value": "FRAME 18420", "interpreted": "S3 crack candidate", "updated_at": now},
    {"name": "Ultrasonic", "status": "ONLINE", "value": 18.4, "interpreted": "mm gap estimate", "updated_at": now},
    {"name": "Accelerometer", "status": "DEGRADED", "value": 0.42, "x": 0.12, "y": 0.08, "z": 0.42, "vibration": "ABNORMAL", "anomaly_score": 0.72, "updated_at": now},
    {"name": "Temperature", "status": "ONLINE", "value": 34.6, "interpreted": "NORMAL", "updated_at": now},
    {"name": "GPS", "status": "ONLINE", "lat": 12.9724, "lng": 77.5950, "accuracy": 2.8, "satellites": 8, "fix_type": "3D", "updated_at": now},
]
tracks_data = [
    {"id": "track-a", "name": "Track A", "status": "OPEN", "occupancy": "CLEAR", "max_speed": "80 km/h", "severity": "S3", "geometry": {"type": "LineString", "coordinates": [[77.5928, 12.9708], [77.5960, 12.9730], [77.5990, 12.9752]]}},
    {"id": "track-b", "name": "Track B", "status": "OPEN", "occupancy": "OCCUPIED", "max_speed": "60 km/h", "severity": "S2", "geometry": {"type": "LineString", "coordinates": [[77.5928, 12.9698], [77.5960, 12.9720], [77.5990, 12.9742]]}},
]
trains_data = [{"id": "train-demo-01", "latitude": 12.9713, "longitude": 77.5938, "speed": "42 km/h", "destination": "KSR Bengaluru", "next_switch": "switch-01", "distance": "680 m", "gps": {"accuracy": 3.1, "satellites": 8, "fix_type": "3D"}}]
tasks = []
workers = [{"id": "worker-01", "name": "Maintenance Worker", "status": "ONLINE", "role": "worker"}]
users = {
    "admin": {"password": "admin", "role": "admin", "name": "Admin User"},
    "worker": {"password": "worker", "role": "worker", "name": "Maintenance Worker", "worker_id": "worker-01"},
}


def envelope(data):
    return jsonify(data)


@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    return response


@app.post("/api/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    user = users.get(body.get("username"))
    if not user or user["password"] != body.get("password"):
        return envelope({"error": "Invalid credentials"}), 401
    # Production backend must re-check the authenticated role on every endpoint.
    result = {"token": f"mock-{body['username']}-token", "role": user["role"], "name": user["name"]}
    if user.get("worker_id"):
        result["worker_id"] = user["worker_id"]
    return envelope(result)


@app.get("/api/alerts")
def list_alerts():
    result = alerts
    for key in ("severity", "status", "track"):
        if request.args.get(key):
            result = [item for item in result if item.get(key) == request.args[key]]
    return envelope({"items": result})


@app.get("/api/alerts/<alert_id>")
def alert_detail(alert_id):
    return envelope(next((item for item in alerts if item["id"] == alert_id), {}))


@app.post("/api/alerts/<alert_id>/<action>")
def alert_action(alert_id, action):
    item = next((item for item in alerts if item["id"] == alert_id), None)
    if item and action in {"acknowledge", "resolve", "false-positive"}:
        item["status"] = {"acknowledge": "ACKNOWLEDGED", "resolve": "RESOLVED", "false-positive": "FALSE_POSITIVE"}[action]
    if action == "history":
        return envelope({"items": []})
    return envelope(item or {})


@app.get("/api/alerts/<alert_id>/history")
def alert_history(alert_id):
    return envelope({"items": []})


@app.get("/api/devices")
def list_devices():
    return envelope({"items": devices})


@app.get("/api/devices/<device_id>/sensors")
def sensors(device_id):
    return envelope({"items": sensor_readings if device_id == "device-01" else []})


@app.get("/api/devices/<device_id>/diagnostics")
def diagnostics(device_id):
    return envelope({"device_id": device_id, "status": "ONLINE", "pi_status": "ONLINE", "network_status": "ONLINE", "uptime": devices[0].get("uptime") if device_id == "device-01" else None, "updated_at": now, "checks": [{"name": "Camera stream", "status": "PASS"}, {"name": "Sensor bus", "status": "PASS"}, {"name": "GPS fix", "status": "PASS"}]})


@app.get("/api/tasks")
def list_tasks():
    worker_id = request.args.get("worker_id")
    result = [task for task in tasks if not worker_id or task.get("worker_id") == worker_id]
    return envelope({"items": result})


@app.post("/api/tasks")
def create_task():
    body = request.get_json(silent=True) or {}
    task = {"id": f"TASK-{len(tasks) + 1:03d}", **body}
    tasks.append(task)
    return envelope(task), 201


@app.get("/api/workers")
def list_workers():
    return envelope({"items": workers})


@app.route("/api/tasks/<task_id>/<action>", methods=["POST", "PUT"])
def task_action(task_id, action):
    task = next((item for item in tasks if item["id"] == task_id), None)
    if action == "evidence":
        if task is not None:
            task["evidence"] = {"status": "RECEIVED", "notes": request.form.get("notes", "Demo repair evidence")}
        return envelope({"task_id": task_id, "status": "RECEIVED"})
    status = request.json.get("status") if request.is_json else None
    if task is not None and status:
        task["status"] = status
    return envelope({"task_id": task_id, "status": status})


@app.get("/api/tracks")
def tracks():
    return envelope({"items": tracks_data})


@app.get("/api/trains")
def trains():
    return envelope({"items": trains_data})


@app.get("/api/switch/status")
def switch_status():
    return envelope({"status": "READY", "action": "MAINTAIN", "action_level": "WARNING", "train_id": "train-demo-01", "switch_id": "switch-01", "target_track": "Track A", "confidence": 0.78, "reason": "Track A has S2 defect. Track B is occupied.", "latitude": 12.9720, "longitude": 77.5954, "rules_checked": [{"rule": "Target track is not occupied", "passed": True}, {"rule": "No S3 defect on target track", "passed": True}, {"rule": "Switch mechanism is available", "passed": True}, {"rule": "Train is not too close to switch", "passed": True}], "raw_scores": {"A": 0.78, "B": 0.42}})


@app.post("/api/switch/decision")
def switch_decision():
    return envelope({"status": "RECEIVED", "decision": request.get_json(silent=True)})


@app.get("/api/simulation/state")
def simulation_state():
    return envelope({"status": "CONNECTED", "mode": "SIMULATION", "scenario": "S2 on A, B occupied", "updated_at": now})


@app.post("/api/simulation/mode")
def simulation_mode():
    return envelope({"mode": request.json.get("mode") if request.is_json else None})


@app.get("/api/dashboard/summary")
def dashboard_summary():
    return envelope({"active_alerts": len(alerts), "s3_alerts": sum(item["severity"] == "S3" for item in alerts), "s2_alerts": sum(item["severity"] == "S2" for item in alerts), "s1_alerts": 0, "pending_tasks": len(tasks), "online_devices": sum(item["status"] == "ONLINE" for item in devices), "total_devices": len(devices)})


@app.get("/api/dashboard/event-log")
def event_log():
    return envelope({"items": [], "generated_at": datetime.now(timezone.utc).isoformat()})


@app.get("/api/model/status")
def model_status():
    return envelope({"name": "RailSafe TrackDefectNet", "version": "demo-1.0", "class_count": 4, "input_size": "640x640", "inference_ms": 84, "device": "Raspberry Pi 5", "loaded": True, "inference_active": True})


@app.get("/api/ai/detection")
def ai_detection():
    return envelope({"image_url": "/demo/track-inspection.svg", "class": "Crack", "confidence": 0.94, "severity": "S3", "boxes": [{"x": 0.34, "y": 0.28, "width": 0.22, "height": 0.16}], "fusion": {"camera": True, "ultrasonic": True, "vibration": True}, "final_confidence": 0.96})


@app.get("/demo/track-inspection.svg")
def demo_image():
    svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 960 540'><rect width='960' height='540' fill='#131b2c'/><path d='M80 470 L880 130 M80 520 L880 180' stroke='#8c99b3' stroke-width='20'/><path d='M120 450 L820 150' stroke='#26324a' stroke-width='6'/><path d='M430 315 l145 -62' stroke='#d62839' stroke-width='13' stroke-linecap='round'/><text x='36' y='54' fill='#e7ecf5' font-family='sans-serif' font-size='28'>RailSafe demo inspection frame</text></svg>"""
    return app.response_class(svg, mimetype="image/svg+xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
