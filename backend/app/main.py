import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_router
from app.core.config import Settings, settings
from app.core.security import validate_device_token
from app.realtime.live import router as websocket_router
from app.services.device_monitor import DeviceMonitor
from app.services.facility_simulator import FacilitySimulator
from app.services.runtime import Runtime

logger = logging.getLogger(__name__)


async def _run_simulator(simulator: FacilitySimulator, runtime: Runtime) -> None:
    failing: set[str] = set()
    while True:
        for facility_id, facility in tuple(runtime.facilities.items()):
            if not facility["is_simulated"]:
                continue
            try:
                await simulator.step(facility_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                # One bad step must not stop the simulator; log once per failing facility.
                if facility_id not in failing:
                    failing.add(facility_id)
                    logger.exception("Simulator step failed for %s", facility_id)
            else:
                if facility_id in failing:
                    failing.discard(facility_id)
                    logger.warning("Simulator recovered for %s", facility_id)
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = Runtime(app.state.config)
    app.state.runtime = runtime
    await runtime.load_persisted_state()
    monitor = asyncio.create_task(DeviceMonitor(runtime).run())
    simulator = FacilitySimulator(runtime)
    app.state.simulator = simulator
    simulation_task = (
        asyncio.create_task(_run_simulator(simulator, runtime))
        if runtime.config.simulation_enabled
        else None
    )
    try:
        yield
    finally:
        monitor.cancel()
        if simulation_task:
            simulation_task.cancel()
        try:
            await asyncio.gather(
                monitor,
                *([simulation_task] if simulation_task else []),
                return_exceptions=True,
            )
        except asyncio.CancelledError:
            pass
        await runtime.close()


def create_app(config: Settings | None = None) -> FastAPI:
    config = config or settings
    app = FastAPI(
        title="SENTINEL Infrastructure Monitoring API",
        version="0.1.0",
        description="Safety-first environmental monitoring and response service.",
        lifespan=lifespan,
    )
    app.state.config = config

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = [
            {key: value for key, value in item.items() if key != "input"}
            for item in exc.errors()
        ]
        if request.url.path == "/api/v1/telemetry":
            token = request.headers.get("X-Device-Token")
            authenticated = False
            authenticated_device = ""
            for device_id in ("sentinel-esp32", "sentinel-pico"):
                try:
                    validate_device_token(config, device_id, token)
                    authenticated = True
                    authenticated_device = device_id
                    break
                except HTTPException:
                    pass
            runtime = getattr(request.app.state, "runtime", None)
            if authenticated and runtime:
                details = {"errors": errors}
                logger.warning(
                    "Rejected invalid telemetry payload for %s: %s", authenticated_device, details
                )
                await runtime.record_sensor_fault(
                    authenticated_device, "Invalid telemetry payload", details
                )
        return JSONResponse(
            status_code=422,
            content={"detail": jsonable_encoder(errors)},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-Device-Token", "X-Operator-Key", "Idempotency-Key"],
    )
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()