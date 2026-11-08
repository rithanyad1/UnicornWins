from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommandType(StrEnum):
    FAN_ON = "FAN_ON"
    FAN_OFF = "FAN_OFF"
    VENT_OPEN = "VENT_OPEN"
    VENT_CLOSE = "VENT_CLOSE"
    BUZZER_ON = "BUZZER_ON"
    BUZZER_OFF = "BUZZER_OFF"
    SET_LED_STATUS = "SET_LED_STATUS"


class CommandStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=100)
    command_type: CommandType
    parameters: dict[str, Any] = Field(default_factory=dict)
    incident_id: str | None = None

    @model_validator(mode="after")
    def validate_parameters(self) -> "CommandRequest":
        allowed = {"status", "color", "brightness", "duration_ms"}
        if self.parameters.keys() - allowed:
            raise ValueError("Unsupported command parameters")
        if self.command_type == CommandType.SET_LED_STATUS:
            if self.parameters.get("status") not in {"HEALTHY", "WARNING", "CRITICAL", "DISCONNECTED"}:
                raise ValueError("SET_LED_STATUS requires a supported status parameter")
        elif self.parameters.keys() - {"duration_ms"}:
            raise ValueError("This command does not accept status, color, or brightness parameters")
        if "brightness" in self.parameters:
            brightness = self.parameters["brightness"]
            if not isinstance(brightness, int) or isinstance(brightness, bool) or not 0 <= brightness <= 100:
                raise ValueError("brightness must be an integer from 0 to 100")
        if "duration_ms" in self.parameters:
            duration = self.parameters["duration_ms"]
            if not isinstance(duration, int) or isinstance(duration, bool) or not 0 < duration <= 60_000:
                raise ValueError("duration_ms must be an integer from 1 to 60000")
        if "color" in self.parameters and not isinstance(self.parameters["color"], str):
            raise ValueError("color must be a string")
        return self


class CommandAck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CommandStatus
    reported_state: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = Field(default=None, max_length=500)


class HardwareCommand(BaseModel):
    id: str
    device_id: str
    command_type: CommandType
    parameters: dict[str, Any]
    status: CommandStatus
    created_at: datetime
    acknowledged_at: datetime | None = None
    executed_at: datetime | None = None
    incident_id: str | None = None
    reported_state: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = None