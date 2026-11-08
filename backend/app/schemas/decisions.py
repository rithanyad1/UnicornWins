from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Decision(BaseModel):
    id: str
    incident_id: str | None = None
    model_name: str
    anomaly_score: float | None = None
    anomaly_detected: bool = False
    severity: str
    reasoning: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    recommended_action: str | None = None
    decision_source: str = "RULES"
    created_at: datetime