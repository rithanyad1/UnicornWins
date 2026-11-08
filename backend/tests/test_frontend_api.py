"""Endpoints the Next.js dashboard depends on."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

ESP32 = {"X-Device-Token": "dev-esp32-token"}
OPERATOR = {"X-Operator-Key": "dev-operator-token"}


def _reading(timestamp_ms: int, temperature: float = 24.0) -> dict:
    return {
        "device_id": "sentinel-esp32", "temperature_c": temperature,
        "humidity_percent": 40, "vibration_score": 0.1,
        "water_detected": False, "timestamp_ms": timestamp_ms,
    }


def _client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, simulation_enabled=False)))


def test_cors_allows_configured_local_frontend_origins_only() -> None:
    with _client() as client:
        for origin in ("http://localhost:3000", "http://localhost:3001"):
            response = client.get("/api/v1/system/status", headers={"Origin": origin})
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin

            preflight = client.options(
                "/api/v1/decisions",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-origin"] == origin

        rejected = client.get(
            "/api/v1/system/status",
            headers={"Origin": "http://localhost:3002"},
        )
        assert "access-control-allow-origin" not in rejected.headers


def test_status_exposes_configured_thresholds() -> None:
    with _client() as client:
        status = client.get("/api/v1/system/status").json()
        config = client.app.state.runtime.config
        assert status["thresholds"] == {
            "high_temperature_c": config.high_temp_threshold,
            "critical_temperature_c": config.critical_temp_threshold,
            "recovery_temperature_c": config.recovery_temp_threshold,
            "high_humidity_percent": config.high_humidity_threshold,
            "vibration_score": config.vibration_threshold,
        }
        assert status["simulation_enabled"] is False


def test_events_feed_contains_operational_events_not_raw_telemetry() -> None:
    with _client() as client:
        client.post("/api/v1/telemetry", headers=ESP32, json=_reading(1))
        client.post("/api/v1/telemetry", headers=ESP32, json=_reading(2, temperature=36))
        events = client.get("/api/v1/events?limit=20").json()["events"]
        types = [event["type"] for event in events]
        assert "incident.created" in types
        assert "command.status" in types
        assert "telemetry.reading" not in types
        timestamps = [event["timestamp"] for event in events]
        assert timestamps == sorted(timestamps, reverse=True)
        assert client.get("/api/v1/events?limit=0").status_code == 422


def test_commands_can_be_listed_by_incident() -> None:
    with _client() as client:
        client.post("/api/v1/telemetry", headers=ESP32, json=_reading(1, temperature=36))
        incident = client.get("/api/v1/incidents").json()["incidents"][0]
        commands = client.get(f"/api/v1/commands?incident_id={incident['id']}").json()["commands"]
        assert [command["command_type"] for command in commands] == ["FAN_ON"]
        assert client.get("/api/v1/commands?incident_id=missing").json()["commands"] == []


def test_acknowledge_requires_operator_is_idempotent_and_keeps_status() -> None:
    with _client() as client:
        client.post("/api/v1/telemetry", headers=ESP32, json=_reading(1, temperature=36))
        incident = client.get("/api/v1/incidents").json()["incidents"][0]
        url = f"/api/v1/incidents/{incident['id']}/acknowledge"
        assert incident["acknowledged_at"] is None
        assert client.post(url).status_code == 401

        first = client.post(url, headers=OPERATOR, json={"note": "on site"})
        assert first.status_code == 200
        body = first.json()
        assert body["duplicate"] is False
        assert body["incident"]["acknowledged_at"] is not None
        assert body["incident"]["status"] == incident["status"]

        again = client.post(url, headers=OPERATOR).json()
        assert again["duplicate"] is True
        assert again["incident"]["acknowledged_at"] == body["incident"]["acknowledged_at"]
        assert client.post("/api/v1/incidents/missing/acknowledge", headers=OPERATOR).status_code == 404
        assert client.get(f"/api/v1/incidents/{incident['id']}").json()["acknowledged_at"] is not None


def test_facility_summary_lists_all_devices() -> None:
    with _client() as client:
        facility = client.get("/api/v1/facilities/facility-main").json()
        assert {device["device_id"] for device in facility["devices"]} == {"sentinel-esp32", "sentinel-pico"}
        assert facility["connected_devices"] == []


@pytest.mark.asyncio
async def test_activity_is_rebuilt_from_restored_records(monkeypatch) -> None:
    from app.services.runtime import Runtime

    detected = datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 11, 8, 10, 5, tzinfo=timezone.utc)
    rows = {
        "incidents": [{
            "id": "inc-1", "facility_id": "facility-main", "incident_type": "HIGH_TEMPERATURE",
            "severity": "WARNING", "status": "RESOLVED", "description": "hot",
            "detected_readings": {}, "verification_data": [], "detected_at": detected,
            "resolved_at": resolved,
        }],
    }

    async def list_recent(table: str, order_column: str, limit: int = 1000):
        return rows.get(table, [])

    runtime = Runtime(Settings(_env_file=None, simulation_enabled=False))
    monkeypatch.setattr(runtime.persistence, "list_recent", list_recent)
    await runtime.load_persisted_state()
    activity = runtime.recent_activity(10)
    assert [event["type"] for event in activity] == ["incident.recovered", "incident.created"]


def test_websocket_streams_events_with_serialized_timestamps() -> None:
    with _client() as client:
        with client.websocket_connect("/ws/live") as socket:
            client.post("/api/v1/telemetry", headers=ESP32, json=_reading(1, temperature=36))
            received = []
            while not {"telemetry.reading", "incident.created"} <= {event["type"] for event in received}:
                received.append(socket.receive_json())
                assert len(received) < 20, [event["type"] for event in received]
        reading = next(event for event in received if event["type"] == "telemetry.reading")["data"]
        assert isinstance(reading["recorded_at"], str) and reading["recorded_at"].startswith("20")
        assert reading["anomaly"]["model_trained"] in (True, False)
        assert client.app.state.runtime.connections.client_count == 0
