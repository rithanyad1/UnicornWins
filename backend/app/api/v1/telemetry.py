from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from app.core.security import validate_device_token
from app.schemas.telemetry import HardwareTelemetryIn, TelemetryIn

router = APIRouter()


@router.post("/telemetry/hardware", status_code=status.HTTP_202_ACCEPTED)
async def ingest_hardware_telemetry(
    payload: HardwareTelemetryIn,
    request: Request,
    x_device_token: str | None = Header(default=None),
) -> dict:
    runtime = request.app.state.runtime
    # SENTINEL-01 is the physical label of the registered Pico controller.
    validate_device_token(runtime.config, "sentinel-pico", x_device_token)
    return await runtime.telemetry.ingest_hardware(payload.model_dump())


@router.get("/telemetry/hardware")
async def hardware_history(request: Request, limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    from app.services.runtime import _parse_datetime, utc_now

    runtime = request.app.state.runtime
    reports = list(runtime.hardware_reports)[-limit:]
    recorded_at = _parse_datetime(reports[-1].get("recorded_at")) if reports else None
    now = utc_now()
    connected = bool(
        recorded_at
        and 0 <= (now - recorded_at).total_seconds() < runtime.config.device_timeout_seconds
        and runtime.devices["sentinel-pico"]["status"] == "CONNECTED"
    )
    return {
        "reports": reports,
        "connected": connected,
        "device_timeout_seconds": runtime.config.device_timeout_seconds,
        "checked_at": now,
    }


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
