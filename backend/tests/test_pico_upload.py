"""Exercise the firmware HTTP helper without importing board-only modules."""

import importlib.util
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def uploader(monkeypatch):
    monkeypatch.setattr(time, "ticks_ms", lambda: 1000, raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda a, b: a - b, raising=False)
    requests = SimpleNamespace(post=Mock())
    monkeypatch.setitem(sys.modules, "requests", requests)
    path = Path(__file__).resolve().parents[2] / "firmware/pico/telemetry_upload.py"
    spec = importlib.util.spec_from_file_location("telemetry_upload", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, requests


def test_upload_uses_native_endpoint_token_timeout_and_closes_response(uploader):
    module, requests = uploader
    response = Mock(status_code=202)
    response.json.return_value = {"persisted": True}
    requests.post.return_value = response
    wifi = Mock()
    wifi.isconnected.return_value = True
    payload = {"device_id": "SENTINEL-01"}
    assert module.send_report(wifi, payload, "http://backend/", "token", "ssid", "pass")
    requests.post.assert_called_once_with(
        "http://backend/api/v1/telemetry/hardware", json=payload,
        headers={"X-Device-Token": "token"}, timeout=2,
    )
    response.close.assert_called_once()


def test_network_failure_does_not_stop_monitoring(uploader):
    module, requests = uploader
    requests.post.side_effect = OSError("timeout")
    wifi = Mock()
    wifi.isconnected.return_value = True
    assert module.send_report(wifi, {}, "http://backend", "token", "ssid", "pass") is False


def test_disconnected_wifi_reconnect_is_rate_limited(uploader):
    module, requests = uploader
    wifi = Mock()
    wifi.isconnected.return_value = False
    for _ in range(2):
        assert module.send_report(wifi, {}, "http://backend", "token", "ssid", "pass") is False
    wifi.connect.assert_called_once_with("ssid", "pass")
    requests.post.assert_not_called()
