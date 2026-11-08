import asyncio
from datetime import timedelta

import pytest

from app.services.runtime import Runtime, utc_now


@pytest.mark.asyncio
async def test_device_timeout_generates_connectivity_incident() -> None:
    runtime = Runtime()
    await runtime.heartbeat("sentinel-esp32")
    runtime.devices["sentinel-esp32"]["last_seen"] = utc_now() - timedelta(seconds=20)
    await runtime.check_disconnections()
    assert runtime.devices["sentinel-esp32"]["status"] == "DISCONNECTED"
    assert any(item["incident_type"] == "DEVICE_DISCONNECTED" for item in runtime.incidents.values())


@pytest.mark.asyncio
async def test_multiple_device_disconnects_resolve_independently() -> None:
    runtime = Runtime()
    await runtime.heartbeat("sentinel-esp32")
    await runtime.heartbeat("sentinel-pico")
    timeout = timedelta(seconds=20)
    runtime.devices["sentinel-esp32"]["last_seen"] = utc_now() - timeout
    runtime.devices["sentinel-pico"]["last_seen"] = utc_now() - timeout
    await runtime.check_disconnections()
    incidents = [
        item for item in runtime.incidents.values()
        if item["incident_type"] == "DEVICE_DISCONNECTED"
    ]
    assert len(incidents) == 2
    await runtime.heartbeat("sentinel-esp32")
    assert sum(item["status"] == "RESOLVED" for item in incidents) == 1