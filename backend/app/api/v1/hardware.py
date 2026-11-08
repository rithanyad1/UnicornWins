"""Ingest for the standalone SENTINEL Pico 2 W node.

The node builds one JSON report every 3 seconds in its own format (Fahrenheit,
nullable sensor values, its own status). It reaches the backend either over
Wi-Fi, posted straight to ``POST /api/sensor-data``, or over USB serial through
``scripts/serial_bridge.py``, which posts to ``POST /api/v1/hardware/report``.
Both routes map the report onto the backend's telemetry pipeline unchanged.
"""

import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.security import validate_device_token
from app.schemas.telemetry import TelemetryIn

router = APIRouter()
# Mounted at /api, matching the URL the Pico's send_to_backend() posts to.
wifi_router = APIRouter()


class SentinelReport(BaseModel):
    """The payload built by ``generate_payload`` in the node firmware."""

    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(min_length=1, max_length=100)
    temperature_f: float | None = Field(default=None, allow_inf_nan=False)
    humidity_percent: float | None = Field(default=None, allow_inf_nan=False)
    vibration_g: float | None = Field(default=None, allow_inf_nan=False)
    status: str = Field(default="UNKNOWN", max_length=40)
    fan_active: bool = False
    fan_speed_percent: float = Field(default=0, ge=0, le=100)
    alert_reasons: list[str] = Field(default_factory=list, max_length=20)


def fahrenheit_to_celsius(value: float) -> float:
    return round((value - 32) * 5 / 9, 2)


def _next_sequence(runtime, device_id: str) -> int:
    # The firmware sends no counter, so the backend issues a strictly increasing one.
    now_ms = time.time_ns() // 1_000_000
    return max(now_ms, runtime.last_sequence.get(device_id, 0) + 1)


@router.post("/hardware/report", status_code=status.HTTP_202_ACCEPTED)
async def ingest_sentinel_report(
    report: SentinelReport,
    request: Request,
    x_device_token: str | None = Header(default=None),
) -> dict[str, Any]:
    return await _ingest(report, request, x_device_token)


@wifi_router.post("/sensor-data", status_code=status.HTTP_202_ACCEPTED)
async def receive_sensor_data(
    report: SentinelReport,
    request: Request,
    x_device_token: str | None = Header(default=None),
) -> dict[str, Any]:
    config = request.app.state.runtime.config
    if x_device_token is None and not config.sentinel_device_token and config.app_env.lower() == "development":
        # The Pico's urequests.post() sends no headers. Allowed only in development
        # with no token configured; set SENTINEL_DEVICE_TOKEN to require one.
        x_device_token = "dev-sentinel-token"
    result = await _ingest(report, request, x_device_token)
    return {"success": True, **result}


@wifi_router.get("/sensor-data")
async def latest_sensor_data(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    device = runtime.devices[runtime.config.sentinel_device_id]
    return {
        "device": device,
        "reading": runtime.latest.get(device["facility_id"]),
    }


async def _ingest(report: SentinelReport, request: Request, x_device_token: str | None) -> dict[str, Any]:
    runtime = request.app.state.runtime
    validate_device_token(runtime.config, report.device_id, x_device_token)
    if report.device_id != runtime.config.sentinel_device_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This device cannot submit node reports")

    device = runtime.devices[report.device_id]
    node_state = {
        "fan": report.fan_active,
        "fan_speed_percent": report.fan_speed_percent,
        "node_status": report.status,
        "alert_reasons": report.alert_reasons,
    }
    device["actuator_state"] = node_state
    device["firmware_version"] = "sentinel-pico-standalone"

    missing = [
        name for name, value in (
            ("temperature", report.temperature_f),
            ("humidity", report.humidity_percent),
            ("vibration", report.vibration_g),
        ) if value is None
    ]
    if missing:
        # The node is alive but at least one sensor failed; keep it connected and
        # record the fault instead of inventing a reading.
        await runtime.heartbeat(report.device_id, node_state, device["firmware_version"])
        await runtime.record_sensor_fault(
            report.device_id,
            f"Sensor error reported by node: {', '.join(missing)}",
            {"node_status": report.status, "alert_reasons": report.alert_reasons},
        )
        await runtime.emit("device.report", {"device_id": report.device_id, **node_state})
        return {"accepted": False, "reason": "sensor_error", "missing": missing}

    try:
        telemetry = TelemetryIn(
            device_id=report.device_id,
            temperature_c=fahrenheit_to_celsius(report.temperature_f),
            humidity_percent=report.humidity_percent,
            vibration_score=min(report.vibration_g, 100.0),
            water_detected=False,  # The node has no water sensor.
            timestamp_ms=_next_sequence(runtime, report.device_id),
        )
    except ValidationError as exc:
        await runtime.record_sensor_fault(report.device_id, "Node reading out of range", {
            "temperature_f": report.temperature_f,
            "humidity_percent": report.humidity_percent,
            "vibration_g": report.vibration_g,
        })
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc

    reading = await runtime.telemetry.ingest({
        **telemetry.model_dump(),
        "temperature_f": report.temperature_f,
        "vibration_g": report.vibration_g,
        **node_state,
    })
    await runtime.emit("device.report", {"device_id": report.device_id, **node_state})
    return {
        "accepted": True,
        "reading": reading,
        "anomaly": runtime.latest_anomaly.get(reading["facility_id"]),
    }
