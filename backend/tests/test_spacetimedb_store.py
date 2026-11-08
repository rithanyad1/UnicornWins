import json
from datetime import datetime, timezone

import httpx
import pytest

from app.core.config import Settings
from app.db.repositories import Repository, decode_row, encode_row, from_micros, to_micros
from app.db.spacetimedb import SpacetimeDBError, SpacetimeStore


def _store(handler) -> SpacetimeStore:
    config = Settings(
        _env_file=None,
        spacetimedb_uri="http://stdb.test/",
        spacetimedb_database="sentinel",
        spacetimedb_token="secret-token",
    )
    return SpacetimeStore(config, transport=httpx.MockTransport(handler))


def test_store_is_unconfigured_without_database_or_token() -> None:
    assert SpacetimeStore(Settings(_env_file=None)).configured is False


def test_timestamp_round_trip_preserves_microseconds() -> None:
    moment = datetime(2026, 11, 7, 18, 30, 1, 123456, tzinfo=timezone.utc)
    assert from_micros(to_micros(moment)) == moment
    assert to_micros(moment.isoformat()) == to_micros(moment)
    assert to_micros(None) == 0 and from_micros(0) is None


def test_incident_row_encoding_round_trip() -> None:
    detected = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    incident = {
        "id": "inc-1", "facility_id": "facility-main", "incident_type": "HIGH_TEMPERATURE",
        "severity": "WARNING", "status": "OPEN", "description": "hot",
        "detected_readings": {"temperature_c": 36.0}, "verification_data": [],
        "detected_at": detected, "resolved_at": None,
    }
    row = encode_row("incidents", incident)
    assert row["resolved_at"] == 0
    assert json.loads(row["detected_readings"]) == {"temperature_c": 36.0}
    assert decode_row("incidents", row) == incident


def test_optional_float_uses_presence_flag() -> None:
    base = {
        "id": "d-1", "incident_id": None, "model_name": "rules", "anomaly_detected": False,
        "severity": "INFO", "reasoning": "r", "tool_calls": [], "recommended_action": None,
        "decision_source": "RULES", "created_at": datetime.now(timezone.utc),
    }
    absent = encode_row("ai_decisions", {**base, "anomaly_score": None})
    present = encode_row("ai_decisions", {**base, "anomaly_score": -0.42})
    assert absent["has_anomaly_score"] is False and present["has_anomaly_score"] is True
    assert decode_row("ai_decisions", absent)["anomaly_score"] is None
    assert decode_row("ai_decisions", present)["anomaly_score"] == -0.42
    assert decode_row("ai_decisions", absent)["incident_id"] is None


def test_reducer_call_sends_bearer_token_and_row_argument() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    Repository(_store(handler)).upsert_one("devices", {
        "device_id": "sentinel-esp32", "facility_id": "facility-main",
        "device_type": "ESP32_SENSOR", "status": "CONNECTED", "last_seen": None,
    })
    request = seen[0]
    assert request.url.path == "/v1/database/sentinel/call/upsert_device"
    assert request.headers["Authorization"] == "Bearer secret-token"
    (row,) = json.loads(request.content)
    assert row["device_id"] == "sentinel-esp32" and row["last_seen"] == 0


def test_reducer_error_is_raised() -> None:
    store = _store(lambda request: httpx.Response(530, text="Only the UN1C0RN^2 backend identity"))
    with pytest.raises(SpacetimeDBError, match="upsert_incident"):
        store.call_reducer("upsert_incident", [{}])


def test_read_rows_procedure_result_is_decoded_and_sorted_newest_first() -> None:
    old, new = to_micros("2026-11-07T10:00:00+00:00"), to_micros("2026-11-07T11:00:00+00:00")
    rows = [
        {"id": "a", "facility_id": "facility-main", "incident_type": "WATER_DETECTED",
         "severity": "CRITICAL", "status": "OPEN", "description": "", "detected_readings": "{}",
         "verification_data": "[]", "detected_at": old, "resolved_at": 0},
        {"id": "b", "facility_id": "facility-main", "incident_type": "WATER_DETECTED",
         "severity": "CRITICAL", "status": "RESOLVED", "description": "", "detected_readings": "{}",
         "verification_data": "[]", "detected_at": new, "resolved_at": new},
    ]
    calls: list[tuple[str, list]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content)))
        # Procedures returning t.string() arrive as a JSON-encoded string.
        return httpx.Response(200, json=json.dumps(rows))

    result = Repository(_store(handler)).list_recent("incidents", "detected_at", 10)
    path, (table, since, limit) = calls[0]
    assert path == "/v1/database/sentinel/call/read_rows"
    assert table == "incidents" and since > 0 and limit == 10
    assert [row["id"] for row in result] == ["b", "a"]
    assert result[1]["resolved_at"] is None and result[0]["resolved_at"] == from_micros(new)


def test_unauthorized_procedure_error_is_raised_without_token() -> None:
    store = _store(lambda request: httpx.Response(500, text="fatal error: Only the UN1C0RN^2 backend identity"))
    with pytest.raises(SpacetimeDBError) as excinfo:
        store.read_rows("facilities", 0, 1)
    assert "secret-token" not in str(excinfo.value)


def test_ensure_seed_data_calls_reducer() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200)

    Repository(_store(handler)).ensure_seed_data()
    assert paths == ["/v1/database/sentinel/call/ensure_seed_data"]


def test_list_recent_rejects_unknown_identifiers() -> None:
    repository = Repository(_store(lambda request: httpx.Response(200, json=[])))
    with pytest.raises(ValueError):
        repository.list_recent("owner", "id", 1)
    with pytest.raises(ValueError):
        repository.list_recent("incidents", "nope", 1)


@pytest.mark.asyncio
async def test_repeated_failures_are_logged_once_then_recovery_is_reported(caplog) -> None:
    import logging

    from app.services.persistence import PersistenceService

    service = PersistenceService(Settings(
        _env_file=None, spacetimedb_database="sentinel", spacetimedb_token="secret-token",
    ))
    healthy = {"ok": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if healthy["ok"]:
            return httpx.Response(200)
        return httpx.Response(530, text="Only the UN1C0RN^2 backend identity may write")

    service.store.client = httpx.Client(
        base_url="http://stdb.test", transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer secret-token"},
    )
    device = {"device_id": "d", "facility_id": "facility-main", "device_type": "X",
              "status": "CONNECTED", "last_seen": None}
    with caplog.at_level(logging.WARNING, logger="app.services.persistence"):
        for _ in range(25):
            assert await service.persist_device(device) is False
        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(errors) == 1
        healthy["ok"] = True
        assert await service.persist_device(device) is True
    assert any("recovered" in r.getMessage() for r in caplog.records)
    assert all("secret-token" not in r.getMessage() for r in caplog.records)
