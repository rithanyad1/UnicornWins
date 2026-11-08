from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.security import require_operator

router = APIRouter()


def _facility_summary(runtime, facility_id: str) -> dict:
    facility = runtime.facilities[facility_id]
    incidents = [
        item for item in runtime.incidents.values()
        if item["facility_id"] == facility_id and item["status"] in {"OPEN", "RESPONDING"}
    ]
    devices = [
        item for item in runtime.devices.values() if item["facility_id"] == facility_id
    ]
    return {
        **facility,
        "latest_reading": runtime.latest.get(facility_id),
        "active_incidents": incidents,
        "connected_devices": [item for item in devices if item["status"] == "CONNECTED"],
        "device_count": len(devices),
    }


@router.get("/facilities")
async def list_facilities(request: Request) -> dict:
    runtime = request.app.state.runtime
    return {
        "facilities": [
            _facility_summary(runtime, facility_id)
            for facility_id in runtime.facilities
        ]
    }


@router.get("/facilities/{facility_id}")
async def get_facility(facility_id: str, request: Request) -> dict:
    runtime = request.app.state.runtime
    if facility_id not in runtime.facilities:
        raise HTTPException(status_code=404, detail="Facility not found")
    return _facility_summary(runtime, facility_id)


@router.get("/facilities/{facility_id}/history")
async def facility_history(facility_id: str, request: Request, limit: int = 100) -> dict:
    runtime = request.app.state.runtime
    if facility_id not in runtime.facilities:
        raise HTTPException(status_code=404, detail="Facility not found")
    if not 1 <= limit <= 1000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 1000")
    return {"readings": list(runtime.readings.get(facility_id, []))[-limit:]}


@router.get("/facilities/{facility_id}/incidents")
async def facility_incidents(facility_id: str, request: Request) -> dict:
    runtime = request.app.state.runtime
    if facility_id not in runtime.facilities:
        raise HTTPException(status_code=404, detail="Facility not found")
    incidents = [
        item for item in runtime.incidents.values() if item["facility_id"] == facility_id
    ]
    incidents.sort(key=lambda item: item["detected_at"], reverse=True)
    return {"incidents": incidents}


@router.get("/network/overview")
async def network_overview(request: Request) -> dict:
    runtime = request.app.state.runtime
    facilities = [_facility_summary(runtime, item) for item in runtime.facilities]
    return {
        "facility_count": len(facilities),
        "simulated_facility_count": sum(item["is_simulated"] for item in facilities),
        "active_incident_count": sum(len(item["active_incidents"]) for item in facilities),
        "facilities": facilities,
        "generated_at": runtime.latest.get("facility-main", {}).get("recorded_at"),
    }


class SimulationTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: str = Field(pattern="^(overheating|water|vibration|disconnect|normal)$")


@router.post("/facilities/{facility_id}/simulation/trigger")
async def trigger_simulation(
    facility_id: str,
    payload: SimulationTrigger,
    request: Request,
    _: None = Depends(require_operator),
) -> dict:
    runtime = request.app.state.runtime
    if facility_id not in runtime.facilities:
        raise HTTPException(status_code=404, detail="Facility not found")
    if not runtime.facilities[facility_id]["is_simulated"]:
        raise HTTPException(status_code=409, detail="Scenario triggers are only available for simulated facilities")
    request.app.state.simulator.trigger(facility_id, payload.scenario)
    return {"facility_id": facility_id, "scenario": payload.scenario, "accepted": True}
