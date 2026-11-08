from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.security import validate_device_token
from app.schemas.telemetry import TelemetryIn

router = APIRouter()


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    payload: TelemetryIn,
    request: Request,
    x_device_token: str | None = Header(default=None),
) -> dict:
    runtime = request.app.state.runtime
    validate_device_token(runtime.config, payload.device_id, x_device_token)
    if payload.device_id != "sentinel-esp32":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This device cannot submit sensor telemetry")
    try:
        reading = await runtime.telemetry.ingest(payload.model_dump())
    except ValueError as exc:
        await runtime.record_sensor_fault(payload.device_id, str(exc), {
            "timestamp_ms": payload.timestamp_ms,
        })
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "accepted": True,
        "reading": reading,
        "anomaly": runtime.latest_anomaly.get(reading["facility_id"]),
    }