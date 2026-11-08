from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DeviceStatus(StrEnum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


class DeviceHeartbeat(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    actuator_state: dict[str, Any] = Field(default_factory=dict)
    firmware_version: str | None = None


class DeviceInfo(BaseModel):
    device_id: str
    facility_id: str
    device_type: str
    status: DeviceStatus
    last_seen: datetime | None = None
    actuator_state: dict[str, Any] = Field(default_factory=dict)