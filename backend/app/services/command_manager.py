from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.schemas.commands import CommandStatus, CommandType


class CommandManager:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.commands: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[tuple[str, str], str] = {}
        self.expired_commands: list[dict[str, Any]] = []

    def restore(self, command: dict[str, Any]) -> None:
        created_at = _datetime(command["created_at"])
        command = {
            **command,
            "created_at": created_at,
            "expires_at": _datetime(command["expires_at"])
            if command.get("expires_at")
            else created_at + timedelta(seconds=self.config.command_ttl_seconds),
            "acknowledged_at": _datetime(command["acknowledged_at"])
            if command.get("acknowledged_at")
            else None,
            "executed_at": _datetime(command["executed_at"])
            if command.get("executed_at")
            else None,
        }
        self.commands[command["id"]] = command

    def create(
        self,
        device_id: str,
        command_type: CommandType,
        parameters: dict[str, Any] | None = None,
        incident_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key:
            key = (device_id, idempotency_key)
            existing_id = self._idempotency.get(key)
            if existing_id:
                return self.commands[existing_id]
        for existing in reversed(tuple(self.commands.values())):
            if (
                existing["device_id"] == device_id
                and existing["command_type"] == command_type.value
                and existing["parameters"] == (parameters or {})
                and existing["incident_id"] == incident_id
                and existing["status"] in {
                    CommandStatus.PENDING.value, CommandStatus.DELIVERED.value,
                }
            ):
                if idempotency_key:
                    self._idempotency[(device_id, idempotency_key)] = existing["id"]
                return existing
        now = datetime.now(timezone.utc)
        command = {
            "id": str(uuid4()),
            "device_id": device_id,
            "command_type": command_type.value,
            "parameters": parameters or {},
            "status": CommandStatus.PENDING.value,
            "created_at": now,
            "expires_at": now + timedelta(seconds=self.config.command_ttl_seconds),
            "acknowledged_at": None,
            "executed_at": None,
            "incident_id": incident_id,
            "reported_state": {},
            "failure_reason": None,
        }
        self.commands[command["id"]] = command
        if idempotency_key:
            self._idempotency[(device_id, idempotency_key)] = command["id"]
        return command

    def next_for_device(self, device_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        for command in sorted(self.commands.values(), key=lambda item: item["created_at"]):
            if command["device_id"] != device_id:
                continue
            if command["status"] in {CommandStatus.PENDING.value, CommandStatus.DELIVERED.value}:
                if command["expires_at"] <= now:
                    command["status"] = CommandStatus.EXPIRED.value
                    self.expired_commands.append(command)
                    continue
                if command["status"] == CommandStatus.PENDING.value:
                    command["status"] = CommandStatus.DELIVERED.value
                return command
        return None

    def acknowledge(
        self,
        command_id: str,
        status: CommandStatus,
        reported_state: dict[str, Any] | None = None,
        failure_reason: str | None = None,
    ) -> tuple[dict[str, Any] | None, bool]:
        command = self.commands.get(command_id)
        if command is None:
            return None, False
        if command["status"] == CommandStatus.EXPIRED.value:
            raise ValueError("Expired commands cannot be acknowledged")
        if command["status"] in {CommandStatus.EXECUTED.value, CommandStatus.FAILED.value}:
            return command, False
        if status not in {CommandStatus.EXECUTED, CommandStatus.FAILED}:
            raise ValueError("Acknowledgment status must be EXECUTED or FAILED")
        reported_state = reported_state or {}
        if status == CommandStatus.EXECUTED:
            mismatch = self._actuator_state_mismatch(command, reported_state)
            if mismatch:
                status = CommandStatus.FAILED
                failure_reason = mismatch
        now = datetime.now(timezone.utc)
        command["status"] = status.value
        command["acknowledged_at"] = now
        command["executed_at"] = now if status == CommandStatus.EXECUTED else None
        command["reported_state"] = reported_state
        command["failure_reason"] = failure_reason
        return command, True

    @staticmethod
    def _actuator_state_mismatch(command: dict[str, Any], reported_state: dict[str, Any]) -> str | None:
        command_type = command["command_type"]
        expected: tuple[str, Any] | None = {
            CommandType.FAN_ON.value: ("fan", True),
            CommandType.FAN_OFF.value: ("fan", False),
            CommandType.BUZZER_ON.value: ("buzzer", True),
            CommandType.BUZZER_OFF.value: ("buzzer", False),
        }.get(command_type)
        if command_type in {CommandType.VENT_OPEN.value, CommandType.VENT_CLOSE.value}:
            expected = ("vent", command_type == CommandType.VENT_OPEN.value)
        if command_type == CommandType.SET_LED_STATUS.value:
            expected = ("led_status", command["parameters"].get("status"))
        if expected is None:
            return None
        key, expected_value = expected
        actual = reported_state.get(key)
        if key == "vent":
            matches = actual is expected_value or (
                isinstance(actual, str)
                and actual.upper() == ("OPEN" if expected_value else "CLOSED")
            )
        else:
            matches = actual == expected_value
        if not matches:
            return f"Reported {key} state did not match the requested command"
        return None


def _datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)