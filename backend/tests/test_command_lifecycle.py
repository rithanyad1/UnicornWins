import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import Settings
from app.services.runtime import Runtime


def test_command_poll_acknowledgment_and_duplicate_ack() -> None:
    with TestClient(create_app()) as client:
        telemetry = {
            "device_id": "sentinel-esp32", "temperature_c": 36,
            "humidity_percent": 40, "vibration_score": 0.1,
            "water_detected": False, "timestamp_ms": 10,
        }
        client.post("/api/v1/telemetry", headers={"X-Device-Token": "dev-esp32-token"}, json=telemetry)
        command = client.get(
            "/api/v1/devices/sentinel-pico/commands/next",
            headers={"X-Device-Token": "dev-pico-token"},
        ).json()["command"]
        assert command["command_type"] == "FAN_ON"
        assert client.get(
            "/api/v1/devices/sentinel-pico/commands/next",
            headers={"X-Device-Token": "dev-pico-token"},
        ).json()["command"]["id"] == command["id"]

        ack = client.post(
            f"/api/v1/commands/{command['id']}/ack",
            headers={"X-Device-Token": "dev-pico-token"},
            json={"status": "EXECUTED", "reported_state": {"fan": True}},
        )
        assert ack.status_code == 200
        assert ack.json()["command"]["status"] == "EXECUTED"
        assert client.post(
            f"/api/v1/commands/{command['id']}/ack",
            headers={"X-Device-Token": "dev-pico-token"},
            json={"status": "EXECUTED", "reported_state": {"fan": True}},
        ).json()["duplicate"] is True


def test_execution_ack_requires_matching_reported_actuator_state() -> None:
    with TestClient(create_app(Settings(simulation_enabled=False))) as client:
        client.post(
            "/api/v1/telemetry",
            headers={"X-Device-Token": "dev-esp32-token"},
            json={
                "device_id": "sentinel-esp32", "temperature_c": 25,
                "humidity_percent": 45, "vibration_score": 0.1,
                "water_detected": False, "timestamp_ms": 1,
            },
        )
        client.post(
            "/api/v1/devices/sentinel-pico/heartbeat",
            headers={"X-Device-Token": "dev-pico-token"},
            json={"device_id": "sentinel-pico", "actuator_state": {}},
        )
        created = client.post(
            "/api/v1/commands",
            headers={"X-Operator-Key": "dev-operator-token"},
            json={"device_id": "sentinel-pico", "command_type": "FAN_ON"},
        ).json()["command"]
        response = client.post(
            f"/api/v1/commands/{created['id']}/ack",
            headers={"X-Device-Token": "dev-pico-token"},
            json={"status": "EXECUTED", "reported_state": {"fan": False}},
        )
        assert response.json()["command"]["status"] == "FAILED"
        assert "did not match" in response.json()["command"]["failure_reason"]


def test_operator_authentication_and_safety_override() -> None:
    with TestClient(create_app()) as client:
        headers = {"X-Device-Token": "dev-esp32-token"}
        client.post(
            "/api/v1/telemetry", headers=headers,
            json={
                "device_id": "sentinel-esp32", "temperature_c": 37,
                "humidity_percent": 40, "vibration_score": 0.1,
                "water_detected": False, "timestamp_ms": 1,
            },
        )
        client.post(
            "/api/v1/devices/sentinel-pico/heartbeat",
            headers={"X-Device-Token": "dev-pico-token"},
            json={"device_id": "sentinel-pico", "actuator_state": {}},
        )
        payload = {"device_id": "sentinel-pico", "command_type": "FAN_OFF"}
        assert client.post("/api/v1/commands", json=payload).status_code == 401
        blocked = client.post(
            "/api/v1/commands", headers={"X-Operator-Key": "dev-operator-token"}, json=payload
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["blocked"] is True


def test_operator_command_idempotency_key_returns_same_command() -> None:
    with TestClient(create_app()) as client:
        client.post(
            "/api/v1/telemetry",
            headers={"X-Device-Token": "dev-esp32-token"},
            json={
                "device_id": "sentinel-esp32", "temperature_c": 25,
                "humidity_percent": 40, "vibration_score": 0.1,
                "water_detected": False, "timestamp_ms": 10,
            },
        )
        client.post(
            "/api/v1/devices/sentinel-pico/heartbeat",
            headers={"X-Device-Token": "dev-pico-token"},
            json={"device_id": "sentinel-pico", "actuator_state": {}},
        )
        headers = {"X-Operator-Key": "dev-operator-token", "Idempotency-Key": "same-action"}
        request = {"device_id": "sentinel-pico", "command_type": "FAN_ON"}
        first = client.post("/api/v1/commands", headers=headers, json=request)
        second = client.post("/api/v1/commands", headers=headers, json=request)
        assert first.json()["command"]["id"] == second.json()["command"]["id"]


@pytest.mark.asyncio
async def test_websocket_broadcasts_runtime_events() -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.messages: list[dict] = []

        async def accept(self) -> None:
            return None

        async def send_json(self, message: dict) -> None:
            self.messages.append(message)

    runtime = Runtime(Settings(simulation_enabled=False))
    websocket = FakeWebSocket()
    await runtime.connections.connect(websocket)
    await runtime.emit("telemetry.reading", {"temperature_c": 25})
    assert websocket.messages[0]["type"] == "telemetry.reading"