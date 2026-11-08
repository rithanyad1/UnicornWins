from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.services.runtime import Runtime


@pytest.mark.asyncio
async def test_runtime_hydrates_persisted_facility_device_reading_and_command(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    rows_by_table = {
        "facilities": [{
            "id": "facility-main", "name": "SENTINEL Lab", "city": "Austin",
            "latitude": 30, "longitude": -97, "facility_type": "DEMO",
            "is_simulated": False, "created_at": now.isoformat(),
        }],
        "devices": [{
            "device_id": "sentinel-esp32", "facility_id": "facility-main",
            "device_type": "ESP32_SENSOR", "status": "CONNECTED",
            "last_seen": now.isoformat(),
        }],
        "sensor_readings": [{
            "id": "reading-1", "device_id": "sentinel-esp32",
            "facility_id": "facility-main", "temperature_c": 25,
            "humidity_percent": 45, "vibration_score": 0.1,
            "water_detected": False, "timestamp_ms": 1000,
            "boot_id": "boot-a", "is_simulated": False,
            "recorded_at": now.isoformat(),
        }],
        "incidents": [],
        "ai_decisions": [],
        "hardware_commands": [{
            "id": "command-1", "device_id": "sentinel-pico",
            "command_type": "FAN_ON", "status": "PENDING",
            "parameters": {}, "reported_state": {}, "failure_reason": None,
            "created_at": (now - timedelta(seconds=1)).isoformat(),
            "incident_id": None, "acknowledged_at": None, "executed_at": None,
        }],
    }

    async def list_recent(table: str, order_column: str, limit: int = 1000):
        return rows_by_table[table]

    runtime = Runtime(Settings(simulation_enabled=False))
    monkeypatch.setattr(runtime.persistence, "list_recent", list_recent)
    await runtime.load_persisted_state()
    assert runtime.latest["facility-main"]["id"] == "reading-1"
    assert runtime.last_sequence["sentinel-esp32"] == 1000
    assert runtime.last_boot_id["sentinel-esp32"] == "boot-a"
    command = runtime.commands.commands["command-1"]
    assert command["expires_at"] > command["created_at"]
