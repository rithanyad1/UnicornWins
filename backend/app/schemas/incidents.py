from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    RESPONDING = "RESPONDING"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class Incident(BaseModel):
    id: str
    facility_id: str
    incident_type: str
    severity: Severity
    status: IncidentStatus = IncidentStatus.OPEN
    description: str
    detected_readings: dict[str, Any] = Field(default_factory=dict)
    verification_data: list[dict[str, Any]] = Field(default_factory=list)
    detected_at: datetime
    resolved_at: datetime | None = None