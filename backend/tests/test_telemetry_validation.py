from fastapi.testclient import TestClient

from app.main import create_app


def test_valid_telemetry_is_accepted_and_stored() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/telemetry",
            headers={"X-Device-Token": "dev-esp32-token"},
            json={
                "device_id": "sentinel-esp32", "temperature_c": 26.4,
                "humidity_percent": 45, "vibration_score": 0.08,
                "water_detected": False, "timestamp_ms": 15320,
            },
        )
        assert response.status_code == 202
        assert response.json()["reading"]["facility_id"] == "facility-main"
        latest = client.get("/api/v1/sensors/latest").json()["readings"]
        assert next(item for item in latest if item["device_id"] == "sentinel-esp32")["temperature_c"] == 26.4


def test_invalid_or_missing_telemetry_is_rejected() -> None:
    with TestClient(create_app()) as client:
        headers = {"X-Device-Token": "dev-esp32-token"}
        invalid = {
            "device_id": "sentinel-esp32", "temperature_c": 101,
            "humidity_percent": 45, "vibration_score": 0.08,
            "water_detected": False, "timestamp_ms": 1,
        }
        assert client.post("/api/v1/telemetry", headers=headers, json=invalid).status_code == 422
        assert any(
            event["type"] == "sensor.fault"
            for event in client.app.state.runtime.events
        )
        del invalid["temperature_c"]
        assert client.post("/api/v1/telemetry", headers=headers, json=invalid).status_code == 422


def test_unknown_device_identity_cannot_authenticate() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/telemetry",
            headers={"X-Device-Token": "dev-pico-token"},
            json={
                "device_id": "unregistered-device", "temperature_c": 25,
                "humidity_percent": 45, "vibration_score": 0.1,
                "water_detected": False, "timestamp_ms": 1,
            },
        )
        assert response.status_code == 401


def test_duplicate_and_stale_sequence_is_rejected() -> None:
    payload = {
        "device_id": "sentinel-esp32", "temperature_c": 26.4,
        "humidity_percent": 45, "vibration_score": 0.08,
        "water_detected": False, "timestamp_ms": 100,
    }
    with TestClient(create_app()) as client:
        headers = {"X-Device-Token": "dev-esp32-token"}
        assert client.post("/api/v1/telemetry", headers=headers, json=payload).status_code == 202
        assert client.post("/api/v1/telemetry", headers=headers, json=payload).status_code == 409


def test_new_boot_id_allows_sensor_uptime_counter_to_reset() -> None:
    headers = {"X-Device-Token": "dev-esp32-token"}
    with TestClient(create_app()) as client:
        for timestamp, boot_id in ((100_000, "boot-a"), (1, "boot-b")):
            response = client.post(
                "/api/v1/telemetry",
                headers=headers,
                json={
                    "device_id": "sentinel-esp32", "temperature_c": 25,
                    "humidity_percent": 45, "vibration_score": 0.1,
                    "water_detected": False, "timestamp_ms": timestamp,
                    "boot_id": boot_id,
                },
            )
            assert response.status_code == 202