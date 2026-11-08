import asyncio

from fastapi import APIRouter, Request
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.ai.train import load_baseline
from app.core.security import require_operator
from app.services.runtime import utc_now

router = APIRouter()


class AnomalyTrainingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(pattern="^(recent|simulated|baseline)$")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/system/status")
async def system_status(request: Request) -> dict:
    runtime = request.app.state.runtime
    return {
        "backend_status": "healthy",
        "spacetimedb_status": (
            "connected" if runtime.persistence.available
            else "unavailable" if runtime.persistence.configured
            else "not_configured"
        ),
        "gemini_status": "configured" if runtime.gemini_available else "not_configured",
        "anomaly_model_status": "trained" if runtime.anomaly_detector.is_trained else "untrained",
        "connected_hardware": sum(device["status"] == "CONNECTED" for device in runtime.devices.values()),
        "active_incidents": sum(item["status"] in {"OPEN", "RESPONDING"} for item in runtime.incidents.values()),
        "operating_mode": runtime.mode,
        "latest_telemetry_at": max(
            (item["recorded_at"] for item in runtime.latest.values()), default=None
        ),
        "checked_at": utc_now(),
    }


@router.put("/system/mode")
async def set_operating_mode(
    request: Request,
    mode: str,
    _: None = Depends(require_operator),
) -> dict:
    if mode.upper() not in {"AUTOMATIC", "MANUAL"}:
        raise HTTPException(status_code=422, detail="mode must be AUTOMATIC or MANUAL")
    request.app.state.runtime.mode = mode.upper()
    return {"operating_mode": request.app.state.runtime.mode}


@router.post("/system/anomaly/train")
async def train_anomaly_model(
    payload: AnomalyTrainingRequest,
    request: Request,
    _: None = Depends(require_operator),
) -> dict:
    runtime = request.app.state.runtime
    if payload.source == "simulated":
        await asyncio.to_thread(runtime.anomaly_detector.train_simulated)
    elif payload.source == "recent":
        readings = [reading for group in runtime.readings.values() for reading in group]
        try:
            await asyncio.to_thread(runtime.anomaly_detector.train, readings)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        try:
            readings = await asyncio.to_thread(load_baseline, runtime.config.anomaly_baseline_path)
            await asyncio.to_thread(runtime.anomaly_detector.train, readings)
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    path = await asyncio.to_thread(runtime.anomaly_detector.save)
    return {"trained": True, "samples": payload.source, "model_path": str(path)}
