from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.runtime import Runtime


class TelemetryService:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    async def ingest(self, payload: dict[str, Any], *, is_simulated: bool = False) -> dict[str, Any]:
        return await self.runtime.ingest(payload, is_simulated=is_simulated)

    def latest(self, facility_id: str | None = None) -> list[dict[str, Any]]:
        if facility_id:
            reading = self.runtime.latest.get(facility_id)
            return [reading] if reading else []
        return list(self.runtime.latest.values())

    def history(self, facility_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        return list(self.runtime.readings.get(facility_id, []))[-limit:]