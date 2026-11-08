from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import HTTPException

if TYPE_CHECKING:
    from app.services.runtime import Runtime


class TelemetryService:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    async def ingest(self, payload: dict[str, Any], *, is_simulated: bool = False) -> dict[str, Any]:
        return await self.runtime.ingest(payload, is_simulated=is_simulated)

    async def ingest_hardware(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.services.runtime import utc_now

        runtime = self.runtime
        report = {
            **payload,
            "id": str(uuid4()),
            "facility_id": runtime.devices["sentinel-pico"]["facility_id"],
            "recorded_at": utc_now(),
        }
        # The existing JSON event table preserves the native units and nulls,
        # including fan state and local alerts, without a database migration.
        event = {
            "id": report["id"],
            "event_type": "HARDWARE_TELEMETRY",
            "device_id": "sentinel-pico",
            "description": "SENTINEL-01 hardware report",
            "metadata": report,
            "created_at": report["recorded_at"],
        }
        persisted = await runtime.persistence.persist_critical("system_events", event, upsert=False)
        if runtime.persistence.configured and not persisted:
            raise HTTPException(status_code=503, detail="Hardware report could not be persisted")
        runtime.hardware_reports.append(report)
        await runtime.heartbeat("sentinel-pico", {
            "fan_active": payload["fan_active"],
            "fan_speed_percent": payload["fan_speed_percent"],
        })
        await runtime.emit("hardware.telemetry", report)
        return {"accepted": True, "persisted": persisted, "report": report}

    def latest(self, facility_id: str | None = None) -> list[dict[str, Any]]:
        if facility_id:
            reading = self.runtime.latest.get(facility_id)
            return [reading] if reading else []
        return list(self.runtime.latest.values())

    def history(self, facility_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        return list(self.runtime.readings.get(facility_id, []))[-limit:]
