from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _incident_detail(runtime, incident: dict) -> dict:
    decisions = [
        item for item in runtime.decisions.values() if item["incident_id"] == incident["id"]
    ]
    commands = [
        item for item in runtime.commands.commands.values() if item["incident_id"] == incident["id"]
    ]
    return {
        **incident,
        "ai_analysis": decisions[-1] if decisions else None,
        "decisions": decisions,
        "hardware_commands": commands,
        "hardware_acknowledgment": next(
            (item for item in reversed(commands) if item["acknowledged_at"]), None
        ),
    }


@router.get("/incidents")
async def list_incidents(request: Request, status: str | None = None) -> dict:
    runtime = request.app.state.runtime
    incidents = list(runtime.incidents.values())
    if status:
        incidents = [item for item in incidents if item["status"] == status.upper()]
    incidents.sort(key=lambda item: item["detected_at"], reverse=True)
    return {"incidents": [_incident_detail(runtime, item) for item in incidents]}


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, request: Request) -> dict:
    incident = request.app.state.runtime.incidents.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incident_detail(request.app.state.runtime, incident)
