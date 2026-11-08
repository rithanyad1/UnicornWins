import random
from datetime import timedelta
from typing import Any

from app.services.runtime import Runtime, utc_now


class FacilitySimulator:
    SCENARIOS = {"overheating", "water", "vibration", "disconnect", "normal"}

    def __init__(self, runtime: Runtime, seed: int = 41) -> None:
        self.runtime = runtime
        self.random = random.Random(seed)
        self.scenarios: dict[str, str] = {}
        self._sequences: dict[str, int] = {}

    def trigger(self, facility_id: str, scenario: str) -> None:
        if facility_id not in self.runtime.facilities:
            raise ValueError(f"Unknown facility: {facility_id}")
        if not self.runtime.facilities[facility_id]["is_simulated"]:
            raise ValueError("Physical facilities cannot be controlled by the simulator")
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unsupported simulation scenario: {scenario}")
        self.scenarios[facility_id] = scenario

    async def step(self, facility_id: str) -> dict[str, Any] | None:
        if facility_id not in self.runtime.facilities:
            raise ValueError(f"Unknown facility: {facility_id}")
        if not self.runtime.facilities[facility_id]["is_simulated"]:
            raise ValueError("Simulator cannot generate readings for a physical facility")
        scenario = self.scenarios.get(facility_id, "normal")
        sensor_id = f"{facility_id}-sensor"
        await self.runtime.heartbeat(f"{facility_id}-controller", {"fan": False, "vent": "CLOSED"})
        # Continue after any sequence restored from the database so readings stay monotonic.
        previous = max(self._sequences.get(sensor_id, 0), self.runtime.last_sequence.get(sensor_id, 0))
        self._sequences[sensor_id] = previous + 1000
        if scenario == "disconnect":
            sensor = self.runtime.devices[sensor_id]
            if sensor["status"] == "DISCONNECTED":
                if sensor["last_seen"] is None:
                    await self.runtime.heartbeat(sensor_id)
                    sensor["last_seen"] = utc_now() - timedelta(
                        seconds=self.runtime.config.device_timeout_seconds + 1
                    )
                    await self.runtime.check_disconnections()
                return None
            sensor["last_seen"] = utc_now() - timedelta(seconds=self.runtime.config.device_timeout_seconds + 1)
            await self.runtime.check_disconnections()
            return None

        reading = {
            "device_id": sensor_id,
            "temperature_c": self.random.gauss(25.0, 0.8),
            "humidity_percent": min(100.0, max(0.0, self.random.gauss(48.0, 3.0))),
            "vibration_score": max(0.0, self.random.gauss(0.12, 0.04)),
            "water_detected": False,
            "timestamp_ms": self._sequences[sensor_id],
        }
        if scenario == "overheating":
            reading["temperature_c"] = 38.0 + self.random.random()
        elif scenario == "water":
            reading["water_detected"] = True
        elif scenario == "vibration":
            reading["vibration_score"] = 1.0 + self.random.random()
        return await self.runtime.telemetry.ingest(reading, is_simulated=True)
