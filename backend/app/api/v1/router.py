from fastapi import APIRouter

from app.api.v1 import commands, decisions, devices, facilities, hardware, incidents, sensors, system, telemetry

router = APIRouter()
router.include_router(telemetry.router)
router.include_router(hardware.router)
router.include_router(devices.router)
router.include_router(commands.router)
router.include_router(incidents.router)
router.include_router(decisions.router)
router.include_router(sensors.router)
router.include_router(system.router)
router.include_router(facilities.router)