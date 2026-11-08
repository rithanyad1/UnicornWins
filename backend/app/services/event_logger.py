from typing import Any
from uuid import uuid4

from app.services.runtime import Runtime, utc_now


async def log_event(
    runtime: Runtime,
    event_type: str,
    description: str,
    device_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "id": str(uuid4()),
        "event_type": event_type,
        "device_id": device_id,
        "description": description,
        "metadata": metadata or {},
        "created_at": utc_now(),
    }
    runtime.events.append(event)
    await runtime.persistence.persist_critical("system_events", event)
    await runtime.emit("system.event", event)
    return event