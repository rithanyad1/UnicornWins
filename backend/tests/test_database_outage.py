from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import Settings
from app.services.persistence import PersistenceService


def test_telemetry_ingestion_does_not_depend_on_database() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/telemetry",
            headers={"X-Device-Token": "dev-esp32-token"},
            json={
                "device_id": "sentinel-esp32", "temperature_c": 24,
                "humidity_percent": 40, "vibration_score": 0.1,
                "water_detected": False, "timestamp_ms": 1,
            },
        )
        assert response.status_code == 202
        assert client.get("/api/v1/system/status").json()["backend_status"] == "healthy"


@pytest.mark.asyncio
async def test_failed_flush_retains_buffered_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    service = PersistenceService(Settings(spacetimedb_database="sentinel-test", spacetimedb_token="test"))
    service.buffer_reading({
        "id": "reading-1", "device_id": "sensor", "facility_id": "facility-main",
        "temperature_c": 25, "humidity_percent": 45, "vibration_score": 0.1,
        "water_detected": False, "timestamp_ms": 1,
        "recorded_at": datetime.now(timezone.utc),
        "is_simulated": False,
    })

    def fail_insert(_: list[dict]) -> None:
        raise OSError("database unavailable")

    monkeypatch.setattr(service.repository, "insert_readings", fail_insert)
    assert await service.flush_readings() is False
    assert len(service.pending_readings) == 1


def test_gemini_unavailable_falls_back_to_rule_decision() -> None:
    from app.core.config import Settings
    from app.services.runtime import Runtime

    runtime = Runtime(Settings(_env_file=None, gemini_api_key="", simulation_enabled=False))
    assert runtime.gemini_available is False


@pytest.mark.asyncio
async def test_gemini_request_failure_returns_rule_fallback() -> None:
    from app.core.config import Settings
    from app.services.runtime import Runtime

    class FailedCompletions:
        async def create(self, **kwargs):
            raise OSError("Gemini endpoint unavailable")

    class FakeClient:
        chat = type("Chat", (), {"completions": FailedCompletions()})()

    runtime = Runtime(Settings(
        gemini_api_key="test-key",
        gemini_base_url="https://example.invalid/v1",
        gemini_model="configured-model",
        simulation_enabled=False,
    ))
    runtime.agent.client = FakeClient()
    decision = await runtime.agent.analyze_incident({
        "id": "incident-1",
        "facility_id": "facility-main",
        "severity": "WARNING",
        "description": "test incident",
    })
    assert decision["decision_source"] == "RULES_FALLBACK"
    assert "safety rules remain active" in decision["reasoning"]
