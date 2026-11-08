from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TelemetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=100)
    temperature_c: float = Field(ge=-20, le=100, allow_inf_nan=False)
    humidity_percent: float = Field(ge=0, le=100, allow_inf_nan=False)
    vibration_score: float = Field(ge=0, le=100, allow_inf_nan=False)
    water_detected: bool
    timestamp_ms: int = Field(ge=0)
    boot_id: str | None = Field(default=None, max_length=100)


class TelemetryReading(TelemetryIn):
    id: str
    facility_id: str
    recorded_at: datetime
    is_simulated: bool = False


class HardwareTelemetryIn(BaseModel):
    """Native Pico report; missing sensors stay null rather than becoming zero."""

    model_config = ConfigDict(extra="forbid")

    device_id: Literal["SENTINEL-01"]
    temperature_f: float | None = Field(ge=-67, le=257, allow_inf_nan=False)
    humidity_percent: float | None = Field(ge=0, le=100, allow_inf_nan=False)
    vibration_g: float | None = Field(ge=0, allow_inf_nan=False)
    status: Literal["STARTING", "NORMAL", "WARNING", "CRITICAL", "SENSOR ERROR"]
    fan_active: bool
    fan_speed_percent: int = Field(ge=0, le=100)
    alert_reasons: list[str] = Field(max_length=20)
