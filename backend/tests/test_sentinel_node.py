from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

HEADERS = {"X-Device-Token": "dev-sentinel-token"}


def node_report(**overrides):
    # Exactly the shape the Pico firmware's generate_payload() prints.
    report = {
        "device_id": "SENTINEL-01",
        "temperature_f": 72.5,
        "humidity_percent": 41,
        "vibration_g": 0.012,
        "status": "NORMAL",
        "fan_active": False,
        "fan_speed_percent": 0,
        "alert_reasons": [],
    }
    report.update(overrides)
    return report


def make_client(**settings):
    app = create_app(Settings(_env_file=None, simulation_enabled=False, **settings))
    return TestClient(app)


def test_node_report_becomes_a_reading_in_celsius() -> None:
    with make_client() as client:
        response = client.post("/api/v1/hardware/report", json=node_report(), headers=HEADERS)
        assert response.status_code == 202
        reading = response.json()["reading"]
        assert reading["facility_id"] == "facility-main"
        assert reading["temperature_c"] == 22.5
        assert reading["temperature_f"] == 72.5
        assert reading["vibration_score"] == 0.012
        assert reading["water_detected"] is False
        assert reading["node_status"] == "NORMAL"

        latest = client.get("/api/v1/facilities/facility-main").json()
        assert latest["status"] == "HEALTHY"
        assert latest["latest_reading"]["id"] == reading["id"]


def test_consecutive_reports_are_all_accepted() -> None:
    with make_client() as client:
        for _ in range(3):
            assert client.post("/api/v1/hardware/report", json=node_report(), headers=HEADERS).status_code == 202
        history = client.get("/api/v1/facilities/facility-main/history").json()["readings"]
        assert len(history) == 3


def test_node_report_requires_device_token() -> None:
    with make_client() as client:
        assert client.post("/api/v1/hardware/report", json=node_report()).status_code == 401
        bad = client.post(
            "/api/v1/hardware/report", json=node_report(), headers={"X-Device-Token": "wrong"}
        )
        assert bad.status_code == 401


def test_sensor_error_records_fault_without_a_reading() -> None:
    with make_client() as client:
        response = client.post(
            "/api/v1/hardware/report",
            json=node_report(temperature_f=None, status="SENSOR ERROR", fan_active=True,
                             fan_speed_percent=100, alert_reasons=["Temperature sensor error"]),
            headers=HEADERS,
        )
        assert response.status_code == 202
        assert response.json() == {"accepted": False, "reason": "sensor_error", "missing": ["temperature"]}
        assert client.get("/api/v1/facilities/facility-main/history").json()["readings"] == []
        status = client.get("/api/v1/system/status").json()
        node = next(item for item in status["devices"] if item["device_id"] == "SENTINEL-01")
        assert node["status"] == "CONNECTED"
        assert node["actuator_state"]["node_status"] == "SENSOR ERROR"
        events = client.get("/api/v1/events").json()["events"]
        assert any(item["type"] == "sensor.fault" for item in events)


def test_hot_node_opens_incident_but_queues_no_commands() -> None:
    # 76 F is the firmware's critical threshold (24.4 C).
    with make_client(high_temp_threshold=23.3, critical_temp_threshold=24.4) as client:
        response = client.post(
            "/api/v1/hardware/report",
            json=node_report(temperature_f=77.0, status="CRITICAL", fan_active=True, fan_speed_percent=100),
            headers=HEADERS,
        )
        assert response.status_code == 202
        incidents = client.get("/api/v1/incidents").json()["incidents"]
        assert [item["incident_type"] for item in incidents] == ["CRITICAL_TEMPERATURE"]
        assert incidents[0]["status"] == "RESPONDING"
        assert incidents[0]["hardware_commands"] == []
        assert client.get("/api/v1/facilities/facility-main").json()["status"] == "CRITICAL"


def test_live_websocket_receives_node_readings() -> None:
    with make_client() as client:
        with client.websocket_connect("/ws/live") as live:
            client.post("/api/v1/hardware/report", json=node_report(), headers=HEADERS)
            types = set()
            for _ in range(6):
                message = live.receive_json()
                types.add(message["type"])
                if "telemetry.reading" in types:
                    break
            assert "telemetry.reading" in types
