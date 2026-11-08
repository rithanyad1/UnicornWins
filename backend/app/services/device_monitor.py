import asyncio

from app.services.runtime import Runtime


class DeviceMonitor:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        last_flush = 0.0
        last_connectivity_check = 0.0
        while True:
            await self.runtime.check_disconnections()
            now = loop.time()
            if now - last_flush >= self.runtime.config.telemetry_persist_interval_seconds:
                await self.runtime.persistence.flush_readings()
                last_flush = now
            if self.runtime.persistence.configured and now - last_connectivity_check >= 30:
                await self.runtime.persistence.check_connection()
                last_connectivity_check = now
            await asyncio.sleep(1)