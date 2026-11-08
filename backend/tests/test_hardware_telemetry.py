from unittest.mock import AsyncMock
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.repositories import decode_row, encode_row
from app.main import create_app
from app.services.runtime import Runtime, utc_now


def report():
    return {
        "device_id": "SENTINEL-01", "temperature_f": 75.2,
        "humidity_percent": 45, "vibration_g": 0.215, "status": "WARNING",
        "fan_active": True, "fan_speed_percent": 60,
        "alert_reasons": ["Temperature WARNING: 75.2 F", "Vibration WARNING: 0.215g"],
    }


def config():
    return Settings(_env_file=None, simulation_enabled=False)


HEADERS = {"X-Device-Token": "dev-pico-token"}


def test_native_report_preserves_all_fields_and_updates_controller():
    with TestClient(create_app(config())) as client:
        response = client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=report())
        assert response.status_code == 202
        body = response.json()
        assert body["persisted"] is False
        assert {key: body["report"][key] for key in report()} == report()
        assert body["report"]["recorded_at"]
        history = client.get("/api/v1/telemetry/hardware?limit=1").json()["reports"]
        assert history == [body["report"]]
        controller = client.app.state.runtime.devices["sentinel-pico"]
        assert controller["status"] == "CONNECTED"
        assert controller["actuator_state"]["fan_speed_percent"] == 60


def test_sensor_errors_are_recorded_without_fabricating_measurements():
    payload = {**report(), "temperature_f": None, "humidity_percent": None,
               "vibration_g": None, "status": "SENSOR ERROR", "fan_speed_percent": 100,
               "alert_reasons": ["Temperature sensor error", "Vibration sensor error"]}
    with TestClient(create_app(config())) as client:
        response = client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=payload)
        assert response.status_code == 202
        for field in ("temperature_f", "humidity_percent", "vibration_g"):
            assert response.json()["report"][field] is None
        assert not client.app.state.runtime.latest


def test_hardware_connection_requires_a_recent_report():
    with TestClient(create_app(config())) as client:
        assert client.get("/api/v1/telemetry/hardware").json()["connected"] is False
        client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=report())
        assert client.get("/api/v1/telemetry/hardware").json()["connected"] is True
        runtime = client.app.state.runtime
        runtime.hardware_reports[-1]["recorded_at"] = utc_now() - timedelta(seconds=16)
        # Even a separate, fresh controller heartbeat must not make old data live.
        runtime.devices["sentinel-pico"]["last_seen"] = utc_now()
        state = client.get("/api/v1/telemetry/hardware").json()
        assert state["connected"] is False
        assert len(state["reports"]) == 1


def test_disconnected_controller_never_marks_retained_reports_as_live():
    with TestClient(create_app(config())) as client:
        client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=report())
        client.app.state.runtime.devices["sentinel-pico"]["status"] = "DISCONNECTED"
        assert client.get("/api/v1/telemetry/hardware").json()["connected"] is False


@pytest.mark.parametrize("headers", [{}, {"X-Device-Token": "dev-esp32-token"}])
def test_hardware_endpoint_requires_pico_credentials(headers):
    with TestClient(create_app(config())) as client:
        assert client.post("/api/v1/telemetry/hardware", headers=headers, json=report()).status_code == 401
        assert not client.app.state.runtime.hardware_reports


@pytest.mark.parametrize("change", [
    {"device_id": "other"}, {"temperature_f": 300}, {"humidity_percent": 101},
    {"vibration_g": -1}, {"fan_speed_percent": 101}, {"status": "UNKNOWN"},
])
def test_invalid_hardware_reports_are_rejected(change):
    with TestClient(create_app(config())) as client:
        assert client.post("/api/v1/telemetry/hardware", headers=HEADERS,
                           json={**report(), **change}).status_code == 422


def test_report_is_written_to_existing_database_event_table():
    with TestClient(create_app(config())) as client:
        persistence = client.app.state.runtime.persistence
        persistence.persist_critical = AsyncMock(return_value=True)
        response = client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=report())
        assert response.json()["persisted"] is True
        args = persistence.persist_critical.call_args
        assert args.args[0] == "system_events"
        stored = decode_row("system_events", encode_row("system_events", args.args[1]))
        assert stored["event_type"] == "HARDWARE_TELEMETRY"
        assert stored["metadata"]["alert_reasons"] == report()["alert_reasons"]
        assert stored["metadata"]["vibration_g"] == 0.215


def test_database_failure_is_reported_instead_of_accepting_unsaved_report():
    with TestClient(create_app(config())) as client:
        persistence = client.app.state.runtime.persistence
        persistence.store.client = httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(503)
        ))
        persistence.persist_critical = AsyncMock(return_value=False)
        assert client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=report()).status_code == 503
        assert not client.app.state.runtime.hardware_reports


@pytest.mark.asyncio
async def test_saved_hardware_history_is_restored_after_restart():
    runtime = Runtime(config())
    runtime.persistence.ensure_reference_data = AsyncMock(return_value=True)

    async def recent(table, order_column):
        if table == "system_events":
            return [{"event_type": "HARDWARE_TELEMETRY", "metadata": report()}]
        return []

    runtime.persistence.list_recent = recent
    try:
        await runtime.load_persisted_state()
        assert list(runtime.hardware_reports) == [report()]
    finally:
        await runtime.close()


@pytest.mark.parametrize("temperature,command,expected", [
    (70, "FAN_ON", 201), (70, "FAN_OFF", 201),
    (74, "FAN_OFF", 409), (None, "FAN_OFF", 409),
    (None, "FAN_ON", 201), (70, "VENT_OPEN", 409),
])
def test_native_pico_reports_allow_commands_with_local_cooling_protection(temperature, command, expected):
    with TestClient(create_app(config())) as client:
        client.post("/api/v1/telemetry/hardware", headers=HEADERS,
                    json={**report(), "temperature_f": temperature})
        response = client.post("/api/v1/commands",
                               headers={"X-Operator-Key": "dev-operator-token"},
                               json={"device_id": "sentinel-pico", "command_type": command})
        assert response.status_code == expected


def test_native_commands_reject_stale_sensor_state_despite_fresh_heartbeat():
    with TestClient(create_app(config())) as client:
        client.post("/api/v1/telemetry/hardware", headers=HEADERS, json=report())
        client.app.state.runtime.hardware_reports[-1]["recorded_at"] = utc_now() - timedelta(seconds=16)
        response = client.post("/api/v1/commands",
                               headers={"X-Operator-Key": "dev-operator-token"},
                               json={"device_id": "sentinel-pico", "command_type": "FAN_ON"})
        assert response.status_code == 409
