import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any

from app.core.config import Settings
from app.db.repositories import Repository
from app.db.spacetimedb import SpacetimeStore

logger = logging.getLogger(__name__)

READING_BATCH_SIZE = 500
FAILURE_LOG_INTERVAL_SECONDS = 60.0


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


class _FailureLog:
    """Logs the first database failure in full, then at most one summary per interval.

    Keeps an outage from producing a traceback for every reading or heartbeat,
    while still surfacing it and announcing recovery.
    """

    def __init__(self, interval: float = FAILURE_LOG_INTERVAL_SECONDS) -> None:
        self.interval = interval
        self.failing = False
        self.suppressed = 0
        self._last_logged = 0.0

    def failure(self, action: str, exc: BaseException) -> None:
        now = time.monotonic()
        if not self.failing:
            self.failing = True
            self.suppressed = 0
            self._last_logged = now
            logger.error("SpacetimeDB write/read failed (%s): %s", action, exc, exc_info=exc)
            return
        self.suppressed += 1
        if now - self._last_logged >= self.interval:
            logger.error(
                "SpacetimeDB still failing (%s): %s [%s similar failures suppressed]",
                action, exc, self.suppressed,
            )
            self.suppressed = 0
            self._last_logged = now

    def success(self) -> None:
        if self.failing:
            logger.warning(
                "SpacetimeDB persistence recovered (%s failures suppressed since last report)",
                self.suppressed,
            )
        self.failing = False
        self.suppressed = 0


class PersistenceService:
    def __init__(self, config: Settings) -> None:
        self.store = SpacetimeStore(config)
        self.repository = Repository(self.store)
        self.pending_readings: deque[dict[str, Any]] = deque(maxlen=10_000)
        self._flush_lock = asyncio.Lock()
        self.dropped_readings = 0
        self._failures = _FailureLog()
        self._warned_unconfigured = False

    @property
    def configured(self) -> bool:
        return self.store.configured

    @property
    def available(self) -> bool:
        return self.store.available

    def _succeeded(self) -> None:
        self.store.available = True
        self._failures.success()

    def _failed(self, action: str, exc: BaseException) -> None:
        self.store.available = False
        self._failures.failure(action, exc)

    def _warn_unconfigured(self, table: str) -> None:
        if not self._warned_unconfigured:
            self._warned_unconfigured = True
            logger.warning(
                "SpacetimeDB is not configured; %s and later records are kept in memory only",
                table,
            )

    def buffer_reading(self, reading: dict[str, Any]) -> None:
        if len(self.pending_readings) == self.pending_readings.maxlen:
            self.dropped_readings += 1
            if self.dropped_readings == 1 or self.dropped_readings % 1000 == 0:
                logger.error(
                    "Telemetry persistence buffer full; %s readings have been dropped",
                    self.dropped_readings,
                )
        self.pending_readings.append({
            "id": reading["id"],
            "device_id": reading["device_id"],
            "facility_id": reading["facility_id"],
            "temperature_c": reading["temperature_c"],
            "humidity_percent": reading["humidity_percent"],
            "vibration_score": reading["vibration_score"],
            "water_detected": reading["water_detected"],
            "timestamp_ms": reading["timestamp_ms"],
            "boot_id": reading.get("boot_id"),
            "recorded_at": reading["recorded_at"].isoformat(),
            "is_simulated": reading["is_simulated"],
        })

    async def flush_readings(self) -> bool:
        if not self.configured or not self.pending_readings:
            return False
        async with self._flush_lock:
            while self.pending_readings:
                batch = list(self.pending_readings)[:READING_BATCH_SIZE]
                try:
                    await asyncio.to_thread(self.repository.insert_readings, batch)
                except Exception as exc:
                    self._failed(f"flush {len(self.pending_readings)} buffered readings", exc)
                    return False
                for _ in range(len(batch)):
                    self.pending_readings.popleft()
                self._succeeded()
            return True

    async def persist_critical(
        self, table: str, row: dict[str, Any], *, upsert: bool = True
    ) -> bool:
        if not self.configured:
            self._warn_unconfigured(table)
            return False
        try:
            operation = self.repository.upsert_one if upsert else self.repository.insert_one
            await asyncio.to_thread(operation, table, _json_value(row))
            self._succeeded()
            return True
        except Exception as exc:
            self._failed(f"persist {table}", exc)
            return False

    async def persist_device(self, device: dict[str, Any]) -> bool:
        if not self.configured:
            return False
        record = {
            key: device[key]
            for key in ("device_id", "facility_id", "device_type", "status", "last_seen")
        }
        try:
            await asyncio.to_thread(
                self.repository.upsert_one,
                "devices",
                _json_value(record),
            )
            self._succeeded()
            return True
        except Exception as exc:
            self._failed("persist devices", exc)
            return False

    async def ensure_reference_data(self) -> bool:
        """Insert missing seed facilities/devices (repairs databases where init never ran)."""
        if not self.configured:
            return False
        try:
            await asyncio.to_thread(self.repository.ensure_seed_data)
            self._succeeded()
            return True
        except Exception as exc:
            self._failed("ensure seed data", exc)
            return False

    async def check_connection(self) -> bool:
        if not self.configured:
            return False
        try:
            await asyncio.to_thread(self.store.ping)
            self._succeeded()
            return True
        except Exception as exc:
            self._failed("connectivity check", exc)
            return False

    def close(self) -> None:
        self.store.close()

    async def list_recent(
        self, table: str, order_column: str, limit: int = 1000
    ) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        try:
            rows = await asyncio.to_thread(
                self.repository.list_recent, table, order_column, limit
            )
            self._succeeded()
            return rows
        except Exception as exc:
            self._failed(f"load {table}", exc)
            return []
