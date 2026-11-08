from fastapi.testclient import TestClient

from app.main import create_app


def post_reading(client: TestClient, temperature: float, water: bool = False) -> dict:
    response = client.post(
        "/api/v1/telemetry",
        headers={"X-Device-Token": "dev-esp32-token"},
        json={
            "device_id": "sentinel-esp32", "temperature_c": temperature,
            "humidity_percent": 45, "vibration_score": 0.08,
            "water_detected": water, "timestamp_ms": int(temperature * 1000) + (1000 if water else 0),
        },
    )
    assert response.status_code == 202
    return response.json()


def test_high_and_critical_temperature_create_safety_responses() -> None:
    with TestClient(create_app()) as client:
        post_reading(client, 36)
        first = client.get("/api/v1/incidents").json()["incidents"]
        assert any(item["incident_type"] == "HIGH_TEMPERATURE" for item in first)
        commands = client.app.state.runtime.commands.commands.values()
        assert any(command["command_type"] == "FAN_ON" for command in commands)

    with TestClient(create_app()) as client:
        post_reading(client, 41)
        incidents = client.get("/api/v1/incidents").json()["incidents"]
        assert any(item["incident_type"] == "CRITICAL_TEMPERATURE" for item in incidents)


def test_water_detection_creates_critical_incident_and_buzzer_command() -> None:
    with TestClient(create_app()) as client:
        post_reading(client, 25, water=True)
        incidents = client.get("/api/v1/incidents").json()["incidents"]
        assert incidents[0]["incident_type"] == "WATER_DETECTED"
        assert any(item["command_type"] == "BUZZER_ON" for item in client.app.state.runtime.commands.commands.values())


def test_humidity_and_vibration_rules_create_warning_incidents() -> None:
    with TestClient(create_app()) as client:
        headers = {"X-Device-Token": "dev-esp32-token"}
        response = client.post(
            "/api/v1/telemetry",
            headers=headers,
            json={
                "device_id": "sentinel-esp32", "temperature_c": 25,
                "humidity_percent": 75, "vibration_score": 0.9,
                "water_detected": False, "timestamp_ms": 1,
            },
        )
        assert response.status_code == 202
        incident_types = {item["incident_type"] for item in client.get("/api/v1/incidents").json()["incidents"]}
        assert {"HIGH_HUMIDITY", "ABNORMAL_VIBRATION"} <= incident_types
        assert any(
            command["command_type"] == "BUZZER_ON"
            for command in client.app.state.runtime.commands.commands.values()
        )


def test_fan_is_released_only_after_hysteresis_recovery_threshold() -> None:
    with TestClient(create_app()) as client:
        headers = {"X-Device-Token": "dev-esp32-token"}
        for temperature, sequence in ((37, 1), (33, 2), (31, 3)):
            response = client.post(
                "/api/v1/telemetry",
                headers=headers,
                json={
                    "device_id": "sentinel-esp32", "temperature_c": temperature,
                    "humidity_percent": 45, "vibration_score": 0.1,
                    "water_detected": False, "timestamp_ms": sequence,
                },
            )
            assert response.status_code == 202
        command_types = [
            item["command_type"]
            for item in client.app.state.runtime.commands.commands.values()
        ]
        assert command_types == ["FAN_ON", "FAN_OFF"]