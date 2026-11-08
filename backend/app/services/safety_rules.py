from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.schemas.commands import CommandType
from app.schemas.incidents import Severity


@dataclass(frozen=True)
class SafetyAction:
    incident_type: str
    severity: Severity
    description: str
    command_type: CommandType | None
    parameters: dict[str, Any]


class SafetyEngine:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self._fan_latched: dict[str, bool] = {}

    def evaluate(self, reading: dict[str, Any]) -> list[SafetyAction]:
        actions: list[SafetyAction] = []
        facility_id = str(reading["facility_id"])
        temperature = float(reading["temperature_c"])
        humidity = float(reading["humidity_percent"])
        vibration = float(reading["vibration_score"])

        if temperature >= self.config.critical_temp_threshold:
            self._fan_latched[facility_id] = True
            actions.append(SafetyAction(
                "CRITICAL_TEMPERATURE", Severity.CRITICAL,
                f"Critical temperature detected: {temperature:.1f} C",
                CommandType.FAN_ON, {},
            ))
        elif temperature >= self.config.high_temp_threshold:
            if not self._fan_latched.get(facility_id, False):
                self._fan_latched[facility_id] = True
                actions.append(SafetyAction(
                    "HIGH_TEMPERATURE", Severity.WARNING,
                    f"High temperature detected: {temperature:.1f} C",
                    CommandType.FAN_ON, {},
                ))
        elif temperature <= self.config.recovery_temp_threshold:
            if self._fan_latched.pop(facility_id, False):
                actions.append(SafetyAction(
                    "TEMPERATURE_RECOVERED", Severity.INFO,
                    "Temperature is below the recovery threshold; cooling can be released",
                    CommandType.FAN_OFF, {},
                ))

        if humidity >= self.config.high_humidity_threshold:
            actions.append(SafetyAction(
                "HIGH_HUMIDITY", Severity.WARNING,
                f"High humidity detected: {humidity:.1f}%",
                None, {},
            ))
        if reading["water_detected"]:
            actions.append(SafetyAction(
                "WATER_DETECTED", Severity.CRITICAL,
                "Water sensor detected liquid near the monitored equipment",
                CommandType.BUZZER_ON, {},
            ))
        if vibration >= self.config.vibration_threshold:
            actions.append(SafetyAction(
                "ABNORMAL_VIBRATION", Severity.WARNING,
                f"Abnormal vibration detected: {vibration:.2f}",
                CommandType.BUZZER_ON, {},
            ))
        return actions

    def validate_operator_command(
        self, command_type: CommandType, parameters: dict[str, Any], latest: dict[str, Any] | None
    ) -> str | None:
        if latest is None:
            return "No recent sensor state is available"
        temperature = float(latest["temperature_c"])
        if command_type == CommandType.FAN_OFF and (
            temperature >= self.config.high_temp_threshold
            or self._fan_latched.get(str(latest.get("facility_id", "facility-main")), False)
        ):
            return "Cooling cannot be disabled until the facility is below its recovery threshold"
        if command_type == CommandType.VENT_CLOSE and temperature >= self.config.high_temp_threshold:
            return "Ventilation cannot be closed while temperature is above the high-temperature threshold"
        if command_type == CommandType.BUZZER_OFF and latest["water_detected"]:
            return "The alarm cannot be silenced while water is detected"
        if command_type == CommandType.SET_LED_STATUS:
            status = parameters.get("status")
            if status not in {"HEALTHY", "WARNING", "CRITICAL", "DISCONNECTED"}:
                return "SET_LED_STATUS requires a supported status parameter"
        if parameters.keys() - {"status", "color", "brightness", "duration_ms"}:
            return "Unsupported command parameters"
        return None