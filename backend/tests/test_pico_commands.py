"""Firmware command transport tests run without MicroPython or physical GPIO."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def client(monkeypatch):
    requests = SimpleNamespace(get=Mock(), post=Mock())
    monkeypatch.setitem(__import__("sys").modules, "requests", requests)
    path = Path(__file__).resolve().parents[2] / "firmware/pico/commands.py"
    spec = importlib.util.spec_from_file_location("pico_commands", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    response = Mock(status_code=200)
    response.json.return_value = {"command": {"id": "fan-1", "command_type": "FAN_ON"}}
    requests.get.return_value = response
    requests.post.return_value = Mock(status_code=200)
    return module.CommandClient("https://backend/", "token"), requests


def test_failed_ack_is_retried_without_reexecuting(client):
    command_client, requests = client
    execute = Mock(return_value={"fan": True})
    requests.post.side_effect = [OSError("timeout"), Mock(status_code=200)]
    for _ in range(2):
        command_client.poll(Mock(isconnected=lambda: True), execute)
    execute.assert_called_once()
    requests.get.assert_called_once_with(
        "https://backend/api/v1/devices/sentinel-pico/commands/next",
        headers={"X-Device-Token": "token"}, timeout=2,
    )
    assert requests.post.call_args_list[0] == requests.post.call_args_list[1]
    assert command_client.pending_ack is None
    requests.get.return_value.close.assert_called_once()


def test_local_protection_reports_failure(client):
    command_client, requests = client
    command_client.poll(Mock(isconnected=lambda: True), Mock(side_effect=ValueError("Cooling required")))
    ack = requests.post.call_args.kwargs["json"]
    assert ack["status"] == "FAILED"
    assert ack["failure_reason"] == "Cooling required"


def test_wifi_outage_skips_commands(client):
    command_client, requests = client
    command_client.poll(Mock(isconnected=lambda: False), Mock())
    requests.get.assert_not_called()


def test_no_command_closes_response_without_ack(client):
    command_client, requests = client
    requests.get.return_value.json.return_value = {"command": None}
    command_client.poll(Mock(isconnected=lambda: True), Mock())
    requests.get.return_value.close.assert_called_once()
    requests.post.assert_not_called()
