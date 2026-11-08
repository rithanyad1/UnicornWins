from typing import Any
from uuid import uuid4

from app.schemas.incidents import IncidentStatus
from app.services.runtime import utc_now


class IncidentManager:
    def __init__(self) -> None:
        self.incidents: dict[str, dict[str, Any]] = {}

    def active_for(self, facility_id: str, incident_type: str) -> dict[str, Any] | None:
        return next((
            incident for incident in self.incidents.values()
            if incident["facility_id"] == facility_id
            and incident["incident_type"] == incident_type
            and incident["status"] in {IncidentStatus.OPEN.value, IncidentStatus.RESPONDING.value}
        ), None)

    def create(
        self,
        facility_id: str,
        incident_type: str,
        severity: str,
        description: str,
        detected_readings: dict[str, Any],
    ) -> dict[str, Any]:
        existing = self.active_for(facility_id, incident_type)
        if existing:
            return existing
        incident = {
            "id": str(uuid4()), "facility_id": facility_id,
            "incident_type": incident_type, "severity": severity,
            "status": IncidentStatus.OPEN.value, "description": description,
            "detected_readings": detected_readings, "verification_data": [],
            "detected_at": utc_now(), "resolved_at": None,
        }
        self.incidents[incident["id"]] = incident
        return incident