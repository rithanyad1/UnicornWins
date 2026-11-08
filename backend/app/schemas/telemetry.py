from datetime import datetime

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