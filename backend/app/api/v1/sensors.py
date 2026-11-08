from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/sensors/latest")
async def latest_sensors(request: Request) -> dict:
    return {"readings": request.app.state.runtime.telemetry.latest()}


@router.get("/sensors/history")
async def sensor_history(request: Request, facility_id: str | None = None, limit: int = 100) -> dict:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 1000")
    runtime = request.app.state.runtime
    if facility_id:
        return {"readings": runtime.telemetry.history(facility_id, limit)}
    readings = [
        reading
        for facility_readings in runtime.readings.values()
        for reading in facility_readings
    ]
    readings.sort(key=lambda reading: reading["recorded_at"])
    return {"readings": readings[-limit:]}


@router.get("/sensors/anomaly/latest")
async def latest_anomalies(request: Request) -> dict:
    return {"anomalies": request.app.state.runtime.latest_anomaly}