import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.facility_simulator import FacilitySimulator
from app.services.runtime import Runtime


def test_facility_map_endpoints_include_real_and_simulated_sites() -> None:
    with TestClient(create_app(Settings(simulation_enabled=False))) as client:
        facilities = client.get("/api/v1/facilities").json()["facilities"]
        assert len(facilities) == 1
        assert facilities[0]["id"] == "facility-main"
        assert client.get("/api/v1/network/overview").json()["simulated_facility_count"] == 0

    with TestClient(create_app(Settings(simulation_enabled=True))) as client:
        overview = client.get("/api/v1/network/overview").json()
        assert overview["facility_count"] == 4
        assert overview["simulated_facility_count"] == 3
        assert client.get("/api/v1/facilities/not-real").status_code == 404


def test_facility_status_and_manual_mode_require_operator_auth() -> None:
    with TestClient(create_app(Settings(simulation_enabled=False))) as client:
        assert client.put("/api/v1/system/mode?mode=MANUAL").status_code == 401
        response = client.put(
            "/api/v1/system/mode?mode=MANUAL",
            headers={"X-Operator-Key": "dev-operator-token"},
        )
        assert response.json()["operating_mode"] == "MANUAL"
        telemetry = client.post(
            "/api/v1/telemetry",
            headers={"X-Device-Token": "dev-esp32-token"},
            json={
                "device_id": "sentinel-esp32", "temperature_c": 25,
                "humidity_percent": 45, "vibration_score": 0.1,
                "water_detected": False, "timestamp_ms": 1,
            },
        )
        assert telemetry.status_code == 202
        facility = client.get("/api/v1/facilities/facility-main").json()
        assert facility["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_simulator_uses_telemetry_pipeline_without_hardware_commands() -> None:
    runtime = Runtime(Settings(simulation_enabled=True))
    simulator = FacilitySimulator(runtime)
    simulator.trigger("facility-sim-west", "overheating")
    reading = await simulator.step("facility-sim-west")
    assert reading is not None
    assert reading["is_simulated"] is True
    assert reading["temperature_c"] >= 38
    assert any(
        incident["facility_id"] == "facility-sim-west"
        for incident in runtime.incidents.values()
    )
    assert not runtime.commands.commands

    simulator.trigger("facility-sim-east", "water")
    water_reading = await simulator.step("facility-sim-east")
    assert water_reading["water_detected"] is True
    assert any(
        incident["facility_id"] == "facility-sim-east"
        and incident["incident_type"] == "WATER_DETECTED"
        for incident in runtime.incidents.values()
    )

    simulator.trigger("facility-sim-central", "disconnect")
    await simulator.step("facility-sim-central")
    assert any(
        incident["facility_id"] == "facility-sim-central"
        and incident["incident_type"] == "DEVICE_DISCONNECTED"
        for incident in runtime.incidents.values()
    )


@pytest.mark.asyncio
async def test_simulator_continues_after_sequence_restored_from_database() -> None:
    from app.core.config import Settings
    from app.services.facility_simulator import FacilitySimulator
    from app.services.runtime import Runtime

    runtime = Runtime(Settings(_env_file=None, simulation_enabled=True))
    runtime.last_sequence["facility-sim-west-sensor"] = 103_000
    simulator = FacilitySimulator(runtime)
    reading = await simulator.step("facility-sim-west")
    assert reading is not None and reading["timestamp_ms"] > 103_000
