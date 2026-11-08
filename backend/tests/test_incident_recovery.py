import pytest

from app.core.config import Settings
from app.schemas.commands import CommandStatus
from app.services.recovery_verification import RecoveryVerifier
from app.services.runtime import Runtime


@pytest.mark.asyncio
async def test_incident_is_not_resolved_by_command_ack_and_resolves_after_stable_recovery() -> None:
    runtime = Runtime(Settings(recovery_stability_seconds=0))
    await runtime.ingest({
        "device_id": "sentinel-esp32", "temperature_c": 36,
        "humidity_percent": 40, "vibration_score": 0.1,
        "water_detected": False, "timestamp_ms": 1,
    })
    incident = next(iter(runtime.incidents.values()))
    assert incident["status"] == "RESPONDING"
    command = next(iter(runtime.commands.commands.values()))
    runtime.commands.acknowledge(
        command["id"], status=CommandStatus.EXECUTED, reported_state={"fan": True}
    )
    assert incident["status"] == "RESPONDING"
    await runtime.ingest({
        "device_id": "sentinel-esp32", "temperature_c": 30,
        "humidity_percent": 40, "vibration_score": 0.1,
        "water_detected": False, "timestamp_ms": 2,
    })
    assert incident["status"] == "RESOLVED"


def test_recovery_verifier_requires_stable_subsequent_readings() -> None:
    from datetime import datetime, timedelta, timezone

    verifier = RecoveryVerifier(Settings(recovery_stability_seconds=10))
    incident = {"id": "i-1", "incident_type": "HIGH_TEMPERATURE"}
    start = datetime.now(timezone.utc)
    reading = {
        "recorded_at": start, "temperature_c": 30, "humidity_percent": 40,
        "water_detected": False, "vibration_score": 0.1,
    }
    assert verifier.record(incident, reading) is False
    assert verifier.record(incident, {**reading, "recorded_at": start + timedelta(seconds=5)}) is False
    assert verifier.record(incident, {**reading, "recorded_at": start + timedelta(seconds=11)}) is True
    assert verifier.record(
        incident,
        {**reading, "recorded_at": start + timedelta(seconds=12), "temperature_c": 36},
    ) is False