"""Maps backend records (plain dicts) to SpacetimeDB rows and back.

Column conventions must match ``spacetimedb/src/index.ts``:

* ``ts`` / ``opt_ts``: i64 microseconds since the Unix epoch; 0 means "not set".
* ``opt_str``: "" means "not set".
* ``json``: JSON documents stored as text.
* ``opt_f64``: stored as an f64 column plus a ``has_<field>`` bool column.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.spacetimedb import SpacetimeStore

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "facilities": [
        ("id", "str"), ("name", "str"), ("city", "str"), ("latitude", "f64"),
        ("longitude", "f64"), ("facility_type", "str"), ("is_simulated", "bool"),
        ("created_at", "ts"),
    ],
    "devices": [
        ("device_id", "str"), ("facility_id", "str"), ("device_type", "str"),
        ("status", "str"), ("last_seen", "opt_ts"), ("created_at", "ts"),
    ],
    "sensor_readings": [
        ("id", "str"), ("device_id", "str"), ("facility_id", "str"),
        ("temperature_c", "f64"), ("humidity_percent", "f64"), ("vibration_score", "f64"),
        ("water_detected", "bool"), ("timestamp_ms", "i64"), ("boot_id", "opt_str"),
        ("is_simulated", "bool"), ("recorded_at", "ts"),
    ],
    "incidents": [
        ("id", "str"), ("facility_id", "str"), ("incident_type", "str"), ("severity", "str"),
        ("status", "str"), ("description", "str"), ("detected_readings", "json"),
        ("verification_data", "json"), ("detected_at", "ts"), ("resolved_at", "opt_ts"),
    ],
    "ai_decisions": [
        ("id", "str"), ("incident_id", "opt_str"), ("model_name", "str"),
        ("anomaly_score", "opt_f64"), ("anomaly_detected", "bool"), ("severity", "str"),
        ("reasoning", "str"), ("tool_calls", "json"), ("recommended_action", "opt_str"),
        ("decision_source", "str"), ("created_at", "ts"),
    ],
    "hardware_commands": [
        ("id", "str"), ("device_id", "str"), ("incident_id", "opt_str"),
        ("command_type", "str"), ("parameters", "json"), ("status", "str"),
        ("reported_state", "json"), ("failure_reason", "opt_str"), ("created_at", "ts"),
        ("acknowledged_at", "opt_ts"), ("executed_at", "opt_ts"),
    ],
    "system_events": [
        ("id", "str"), ("event_type", "str"), ("device_id", "opt_str"),
        ("description", "str"), ("metadata", "json"), ("created_at", "ts"),
    ],
}

JSON_DEFAULTS = {
    "detected_readings": {}, "verification_data": [], "tool_calls": [],
    "parameters": {}, "reported_state": {}, "metadata": {},
}

WRITE_REDUCERS = {
    "devices": "upsert_device",
    "incidents": "upsert_incident",
    "ai_decisions": "upsert_ai_decision",
    "hardware_commands": "upsert_hardware_command",
    "system_events": "insert_system_event",
}

# How far back to load history on startup. Facilities and devices load fully.
HISTORY_WINDOWS = {
    "sensor_readings": timedelta(hours=1),
    "incidents": timedelta(days=7),
    "ai_decisions": timedelta(days=7),
    "hardware_commands": timedelta(days=7),
    "system_events": timedelta(days=7),
}


def to_micros(value: datetime | str | None) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = value - _EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def from_micros(value: int | float | None) -> datetime | None:
    if not value:
        return None
    return _EPOCH + timedelta(microseconds=int(value))


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def encode_row(table: str, record: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for column, kind in TABLE_COLUMNS[table]:
        value = record.get(column)
        if kind == "str":
            row[column] = "" if value is None else str(value)
        elif kind == "opt_str":
            row[column] = "" if value is None else str(value)
        elif kind == "f64":
            row[column] = float(value)
        elif kind == "opt_f64":
            row[f"has_{column}"] = value is not None
            row[column] = 0.0 if value is None else float(value)
        elif kind == "bool":
            row[column] = bool(value)
        elif kind == "i64":
            row[column] = int(value)
        elif kind == "ts":
            row[column] = to_micros(value) or to_micros(datetime.now(timezone.utc))
        elif kind == "opt_ts":
            row[column] = to_micros(value)
        elif kind == "json":
            row[column] = json.dumps(
                JSON_DEFAULTS.get(column, {}) if value is None else value,
                default=_json_default,
            )
    return row


def decode_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    for column, kind in TABLE_COLUMNS[table]:
        value = row.get(column)
        if kind == "opt_str":
            record[column] = value or None
        elif kind == "opt_f64":
            record[column] = float(value) if row.get(f"has_{column}") else None
        elif kind in {"ts", "opt_ts"}:
            record[column] = from_micros(value)
        elif kind == "json":
            record[column] = json.loads(value) if value else JSON_DEFAULTS.get(column, {})
        else:
            record[column] = value
    return record


class Repository:
    def __init__(self, store: SpacetimeStore) -> None:
        self.store = store

    def insert_readings(self, records: list[dict[str, Any]]) -> None:
        if records:
            rows = [encode_row("sensor_readings", record) for record in records]
            self.store.call_reducer("insert_sensor_readings", [rows])

    def insert_one(self, table: str, record: dict[str, Any]) -> None:
        self.upsert_one(table, record)

    def upsert_one(self, table: str, record: dict[str, Any]) -> None:
        reducer = WRITE_REDUCERS.get(table)
        if reducer is None:
            raise ValueError(f"Table {table} is not writable from the backend")
        self.store.call_reducer(reducer, [encode_row(table, record)])

    def ensure_seed_data(self) -> None:
        self.store.call_reducer("ensure_seed_data", [])

    def list_recent(self, table: str, order_column: str, limit: int) -> list[dict[str, Any]]:
        """Newest-first rows from the module's ``read_rows`` procedure.

        The procedure orders by each table's own time column; ``order_column``
        is validated and used to re-sort locally.
        """
        if table not in TABLE_COLUMNS:
            raise ValueError(f"Unknown table {table}")
        if order_column not in dict(TABLE_COLUMNS[table]):
            raise ValueError(f"Unknown column {order_column} for {table}")
        window = HISTORY_WINDOWS.get(table)
        since = to_micros(datetime.now(timezone.utc) - window) if window is not None else 0
        rows = [decode_row(table, row) for row in self.store.read_rows(table, since, limit)]
        rows.sort(
            key=lambda row: row.get(order_column) or _EPOCH,
            reverse=True,
        )
        return rows[:limit]
