from datetime import datetime, timedelta
from typing import Any

from app.core.config import Settings


class RecoveryVerifier:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self._healthy_since: dict[str, datetime] = {}
        self._last_reading: dict[str, datetime] = {}

    def record(self, incident: dict[str, Any], reading: dict[str, Any]) -> bool:
        if not self._reading_is_recovered(incident, reading):
            self._healthy_since.pop(incident["id"], None)
            self._last_reading.pop(incident["id"], None)
            return False
        recorded_at = reading["recorded_at"]
        previous = self._last_reading.get(incident["id"])
        if previous and recorded_at - previous > timedelta(seconds=self.config.device_timeout_seconds):
            self._healthy_since[incident["id"]] = recorded_at
        started = self._healthy_since.setdefault(incident["id"], recorded_at)
        self._last_reading[incident["id"]] = recorded_at
        if recorded_at - started < timedelta(seconds=self.config.recovery_stability_seconds):
            return False
        return True

    def _reading_is_recovered(self, incident: dict[str, Any], reading: dict[str, Any]) -> bool:
        incident_type = incident["incident_type"]
        if incident_type in {"HIGH_TEMPERATURE", "CRITICAL_TEMPERATURE"}:
            return reading["temperature_c"] <= self.config.recovery_temp_threshold
        if incident_type == "HIGH_HUMIDITY":
            return reading["humidity_percent"] < self.config.high_humidity_threshold
        if incident_type == "WATER_DETECTED":
            return not reading["water_detected"]
        if incident_type == "ABNORMAL_VIBRATION":
            return reading["vibration_score"] < self.config.vibration_threshold
        return False