from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SystemEvent(BaseModel):
    event_type: str
    description: str
    device_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))