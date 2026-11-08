from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from app.ai.anomaly_detector import AnomalyDetector
from app.ai.gemini_agent import GeminiAgent
from app.core.config import Settings, settings
from app.realtime.connection_manager import ConnectionManager
from app.schemas.commands import CommandType
from app.schemas.devices import DeviceStatus
from app.schemas.incidents import IncidentStatus
from app.services.command_manager import CommandManager
from app.services.persistence import PersistenceService
from app.services.recovery_verification import RecoveryVerifier
from app.services.safety_rules import SafetyEngine
from app.services.telemetry import TelemetryService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class Runtime:
    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        self.connections = ConnectionManager()
        self.telemetry = TelemetryService(self)
        self.safety = SafetyEngine(self.config)
        self.commands = CommandManager(self.config)
        self.persistence = PersistenceService(self.config)
        self.recovery = RecoveryVerifier(self.config)
        self.anomaly_detector = AnomalyDetector(self.config.anomaly_model_path)
        self.agent = GeminiAgent(self, self.config)
        self.readings: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.config.telemetry_history_limit)
        )
        self.latest: dict[str, dict[str, Any]] = {}
        self.hardware_reports: deque[dict[str, Any]] = deque(maxlen=self.config.telemetry_history_limit)
        self.facilities: dict[str, dict[str, Any]] = {
            "facility-main": {
                "id": "facility-main", "name": "UN1C0RN^2 Lab", "city": "Austin",
                "latitude": 30.2672, "longitude": -97.7431, "facility_type": "DEMO",
                "is_simulated": False, "status": "DISCONNECTED", "created_at": utc_now(),
            }
        }
        self.devices: dict[str, dict[str, Any]] = {
            "sentinel-esp32": self._device("sentinel-esp32", "ESP32_SENSOR"),
            "sentinel-pico": self._device("sentinel-pico", "PICO_CONTROLLER"),
        }
        if self.config.simulation_enabled:
            simulated = (
                ("facility-sim-west", "UN1C0RN^2 Sim West", "San Francisco", 37.7749, -122.4194),
                ("facility-sim-central", "UN1C0RN^2 Sim Central", "Chicago", 41.8781, -87.6298),
                ("facility-sim-east", "UN1C0RN^2 Sim East", "New York", 40.7128, -74.0060),
            )
            for facility_id, name, city, latitude, longitude in simulated:
                self.facilities[facility_id] = {
                    "id": facility_id, "name": name, "city": city,
                    "latitude": latitude, "longitude": longitude,
                    "facility_type": "SIMULATED", "is_simulated": True,
                    "status": "DISCONNECTED", "created_at": utc_now(),
                }
                self.devices[f"{facility_id}-sensor"] = self._device(
                    f"{facility_id}-sensor", "SIMULATED_SENSOR", facility_id
                )
                self.devices[f"{facility_id}-controller"] = self._device(
                    f"{facility_id}-controller", "SIMULATED_CONTROLLER", facility_id
                )
        self.incidents: dict[str, dict[str, Any]] = {}
        self.decisions: dict[str, dict[str, Any]] = {}
        self.latest_anomaly: dict[str, dict[str, Any]] = {}
        self.events: deque[dict[str, Any]] = deque(maxlen=5000)
        self.last_sequence: dict[str, int] = {}
        self.last_boot_id: dict[str, str] = {}
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self.mode = "AUTOMATIC"
        self.gemini_available = self.agent.client is not None

    async def load_persisted_state(self) -> None:
        await self.persistence.ensure_reference_data()
        facility_rows = await self.persistence.list_recent("facilities", "created_at")
        for row in facility_rows:
            facility = {
                **row,
                "created_at": _parse_datetime(row.get("created_at")) or utc_now(),
                "status": row.get("status", "DISCONNECTED"),
            }
            self.facilities[facility["id"]] = facility

        device_rows = await self.persistence.list_recent("devices", "created_at")
        for row in device_rows:
            last_seen = _parse_datetime(row.get("last_seen"))
            status = row.get("status", DeviceStatus.DISCONNECTED.value)
            if not last_seen or utc_now() - last_seen > timedelta(seconds=self.config.device_timeout_seconds):
                status = DeviceStatus.DISCONNECTED.value
            self.devices[row["device_id"]] = {
                **row,
                "last_seen": last_seen,
                "status": status,
                "actuator_state": {},
                "firmware_version": None,
            }

        reading_rows = await self.persistence.list_recent("sensor_readings", "recorded_at")
        reading_rows.sort(
            key=lambda row: _parse_datetime(row.get("recorded_at")) or datetime.min.replace(tzinfo=timezone.utc)
        )
        for row in reading_rows:
            recorded_at = _parse_datetime(row.get("recorded_at")) or utc_now()
            reading = {**row, "recorded_at": recorded_at}
            facility_id = reading.get("facility_id")
            if facility_id not in self.facilities:
                continue
            self.readings[facility_id].append(reading)
            current = self.latest.get(facility_id)
            if current is None or recorded_at > current["recorded_at"]:
                self.latest[facility_id] = reading
            device_id = reading["device_id"]
            self.last_sequence[device_id] = row["timestamp_ms"]
            if row.get("boot_id"):
                self.last_boot_id[device_id] = row["boot_id"]

        for row in await self.persistence.list_recent("incidents", "detected_at"):
            incident = {
                **row,
                "detected_at": _parse_datetime(row.get("detected_at")) or utc_now(),
                "resolved_at": _parse_datetime(row.get("resolved_at")),
                "verification_data": row.get("verification_data") or [],
                "detected_readings": row.get("detected_readings") or {},
            }
            self.incidents[incident["id"]] = incident

        for row in await self.persistence.list_recent("ai_decisions", "created_at"):
            self.decisions[row["id"]] = {
                **row,
                "created_at": _parse_datetime(row.get("created_at")) or utc_now(),
                "tool_calls": row.get("tool_calls") or [],
            }

        for row in await self.persistence.list_recent("hardware_commands", "created_at"):
            self.commands.restore({
                **row,
                "parameters": row.get("parameters") or {},
                "reported_state": row.get("reported_state") or {},
            })
        events = await self.persistence.list_recent("system_events", "created_at")
        for event in reversed(events):
            if event["event_type"] == "HARDWARE_TELEMETRY":
                self.hardware_reports.append(event["metadata"])
        for facility_id in self.facilities:
            await self._refresh_facility_status(facility_id)

    def _device(self, device_id: str, device_type: str, facility_id: str = "facility-main") -> dict[str, Any]:
        return {
            "device_id": device_id,
            "facility_id": facility_id,
            "device_type": device_type,
            "status": DeviceStatus.DISCONNECTED.value,
            "last_seen": None,
            "actuator_state": {},
            "firmware_version": None,
        }

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        message = {"type": event_type, "timestamp": utc_now().isoformat(), "data": data}
        self.events.append(message)
        await self.connections.broadcast(message)

    def _schedule(self, coroutine: Any) -> None:
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def persist_command(self, command: dict[str, Any]) -> bool:
        record = {
            key: command.get(key)
            for key in (
                "id", "device_id", "incident_id", "command_type", "parameters",
                "status", "reported_state", "failure_reason", "created_at",
                "acknowledged_at", "executed_at",
            )
        }
        return await self.persistence.persist_critical("hardware_commands", record)

    async def record_sensor_fault(self, device_id: str, reason: str, details: dict[str, Any]) -> None:
        event = {
            "id": str(uuid4()),
            "event_type": "SENSOR_VALIDATION_FAULT",
            "device_id": device_id if device_id in self.devices else None,
            "description": reason,
            "metadata": details,
            "created_at": utc_now(),
        }
        await self.persistence.persist_critical("system_events", event, upsert=False)
        await self.emit("sensor.fault", event)

    async def heartbeat(
        self, device_id: str, actuator_state: dict[str, Any] | None = None, firmware_version: str | None = None
    ) -> dict[str, Any]:
        device = self.devices.get(device_id)
        if device is None:
            device = self._device(device_id, "UNKNOWN")
            self.devices[device_id] = device
        changed = device["status"] != DeviceStatus.CONNECTED.value
        device["status"] = DeviceStatus.CONNECTED.value
        device["last_seen"] = utc_now()
        device["actuator_state"] = actuator_state or device["actuator_state"]
        device["firmware_version"] = firmware_version or device["firmware_version"]
        self._schedule(self.persistence.persist_device(device))
        if changed:
            await self._handle_device_reconnected(device_id, device["last_seen"])
            await self.emit("device.connection", {"device_id": device_id, "status": device["status"]})
            await self._refresh_facility_status(device["facility_id"])
        return device

    async def _handle_device_reconnected(self, device_id: str, seen_at: datetime) -> None:
        for incident in self.incidents.values():
            if (
                incident["incident_type"] == "DEVICE_DISCONNECTED"
                and incident["detected_readings"].get("device_id") == device_id
                and incident["status"] in {IncidentStatus.OPEN.value, IncidentStatus.RESPONDING.value}
            ):
                incident["status"] = IncidentStatus.RESOLVED.value
                incident["resolved_at"] = seen_at
                incident["verification_data"].append({"heartbeat_at": seen_at})
                self._schedule(self.persistence.persist_critical("incidents", incident))
                await self.emit("incident.recovered", incident)

    async def ingest(self, payload: dict[str, Any], is_simulated: bool = False) -> dict[str, Any]:
        device_id = payload["device_id"]
        device = self.devices.get(device_id)
        if device is None:
            device = self._device(device_id, "SIMULATED_SENSOR" if is_simulated else "ESP32_SENSOR")
            self.devices[device_id] = device
        sequence = int(payload["timestamp_ms"])
        previous = self.last_sequence.get(device_id)
        boot_id = payload.get("boot_id")
        known_boot_id = self.last_boot_id.get(device_id)
        device_last_seen = device.get("last_seen")
        rebooted = bool(boot_id and known_boot_id and boot_id != known_boot_id)
        timed_out_reset = bool(
            sequence < (previous or 0)
            and sequence < 60_000
            and device_last_seen
            and utc_now() - device_last_seen > timedelta(seconds=self.config.device_timeout_seconds)
        )
        if previous is not None and sequence <= previous and not rebooted and not timed_out_reset:
            raise ValueError("Telemetry timestamp_ms must increase for each device")
        self.last_sequence[device_id] = sequence
        if boot_id:
            self.last_boot_id[device_id] = boot_id
        was_connected = device["status"] == DeviceStatus.CONNECTED.value
        device["status"] = DeviceStatus.CONNECTED.value
        device["last_seen"] = utc_now()
        self._schedule(self.persistence.persist_device(device))
        reading = {
            **payload,
            "id": str(uuid4()),
            "facility_id": device["facility_id"],
            "recorded_at": utc_now(),
            "is_simulated": is_simulated or self.facilities[device["facility_id"]]["is_simulated"],
        }
        self.latest[device["facility_id"]] = reading
        self.readings[device["facility_id"]].append(reading)
        self.persistence.buffer_reading(reading)
        await self._process_safety(reading)
        if not was_connected:
            await self._handle_device_reconnected(device_id, device["last_seen"])
            await self.emit("device.connection", {"device_id": device_id, "status": device["status"]})
        await self._verify_recovery(reading)
        await self._refresh_facility_status(device["facility_id"])

        history = list(self.readings[device["facility_id"]])
        anomaly = self.anomaly_detector.detect(history)
        self.latest_anomaly[device["facility_id"]] = anomaly
        if anomaly["model_trained"] and anomaly["anomaly_detected"]:
            self._schedule(self._record_anomaly_decision(device["facility_id"], reading, anomaly))
            await self.emit("ai.anomaly", {
                "facility_id": device["facility_id"],
                "reading_id": reading["id"],
                **anomaly,
            })
        await self.emit("telemetry.reading", reading)
        return reading

    async def _record_anomaly_decision(
        self, facility_id: str, reading: dict[str, Any], anomaly: dict[str, Any]
    ) -> None:
        decision = {
            "id": str(uuid4()),
            "incident_id": None,
            "model_name": "Isolation Forest",
            "anomaly_score": anomaly["anomaly_score"],
            "anomaly_detected": True,
            "severity": anomaly["severity"],
            "reasoning": "; ".join(anomaly["suspected_factors"]),
            "tool_calls": [],
            "recommended_action": anomaly["recommended_action"],
            "decision_source": "ISOLATION_FOREST",
            "created_at": utc_now(),
        }
        self.decisions[decision["id"]] = decision
        await self.persistence.persist_critical("ai_decisions", decision)
        await self.emit("ai.decision", {"facility_id": facility_id, **decision, "reading_id": reading["id"]})

    async def _process_safety(self, reading: dict[str, Any]) -> None:
        for action in self.safety.evaluate(reading):
            if action.incident_type == "TEMPERATURE_RECOVERED":
                if not self._is_simulated(reading["facility_id"]):
                    temperature_incident = next((
                        item for item in reversed(tuple(self.incidents.values()))
                        if item["facility_id"] == reading["facility_id"]
                        and item["incident_type"] in {"HIGH_TEMPERATURE", "CRITICAL_TEMPERATURE"}
                    ), None)
                    incident_id = temperature_incident["id"] if temperature_incident else None
                    device_id = self._controller_for(reading["facility_id"])
                    command_count = len(self.commands.commands)
                    command = self.commands.create(
                        device_id,
                        CommandType.FAN_OFF,
                        {},
                        incident_id,
                        idempotency_key=f"{incident_id or reading['id']}:FAN_OFF",
                    )
                    if len(self.commands.commands) != command_count:
                        self._schedule(self.persist_command(command))
                        await self.emit("command.status", command)
                continue
            incident = self._active_incident(reading["facility_id"], action.incident_type)
            created = incident is None
            if incident is None:
                incident = {
                    "id": str(uuid4()),
                    "facility_id": reading["facility_id"],
                    "incident_type": action.incident_type,
                    "severity": action.severity.value,
                    "status": IncidentStatus.OPEN.value,
                    "description": action.description,
                    "detected_readings": reading,
                    "verification_data": [],
                    "detected_at": utc_now(),
                    "resolved_at": None,
                }
                self.incidents[incident["id"]] = incident
            command = None
            command_created = False
            if action.command_type and not self._is_simulated(reading["facility_id"]):
                device_id = self._controller_for(reading["facility_id"])
                command_count = len(self.commands.commands)
                command = self.commands.create(
                    device_id, action.command_type, action.parameters, incident["id"],
                    idempotency_key=f"{incident['id']}:{action.command_type.value}",
                )
                command_created = len(self.commands.commands) != command_count
                incident["status"] = IncidentStatus.RESPONDING.value
            if created:
                decision = self._record_rule_decision(incident, action.command_type)
                self._schedule(self._persist_incident_bundle(incident, command, decision))
                await self.emit("incident.created", incident)
                await self.emit("ai.decision", decision)
                if self.agent.client is not None:
                    self._schedule(self._analyze_incident(incident))
            elif command_created:
                self._schedule(self._persist_incident_bundle(incident, command, None))
            if command is not None and command_created:
                await self.emit("command.status", command)

    async def _persist_incident_bundle(
        self,
        incident: dict[str, Any],
        command: dict[str, Any] | None,
        decision: dict[str, Any] | None,
    ) -> None:
        await self.persistence.persist_critical("incidents", incident)
        if command is not None:
            await self.persist_command(command)
        if decision is not None:
            await self.persistence.persist_critical("ai_decisions", decision)

    def _active_incident(
        self, facility_id: str, incident_type: str, device_id: str | None = None
    ) -> dict[str, Any] | None:
        return next((
            incident for incident in self.incidents.values()
            if incident["facility_id"] == facility_id
            and incident["incident_type"] == incident_type
            and incident["status"] in {IncidentStatus.OPEN.value, IncidentStatus.RESPONDING.value}
            and (
                device_id is None
                or incident["detected_readings"].get("device_id") == device_id
            )
        ), None)

    def _controller_for(self, facility_id: str) -> str:
        return next((
            device_id for device_id, device in self.devices.items()
            if device["facility_id"] == facility_id
            and device["device_type"] in {"PICO_CONTROLLER", "SIMULATED_CONTROLLER"}
        ), "sentinel-pico")

    def _is_simulated(self, facility_id: str) -> bool:
        return bool(self.facilities.get(facility_id, {}).get("is_simulated"))

    def _record_rule_decision(
        self, incident: dict[str, Any], recommended_action: CommandType | None
    ) -> dict[str, Any]:
        decision = {
            "id": str(uuid4()),
            "incident_id": incident["id"],
            "model_name": "UN1C0RN^2 safety rules",
            "anomaly_score": self.latest_anomaly.get(incident["facility_id"], {}).get("anomaly_score"),
            "anomaly_detected": self.latest_anomaly.get(incident["facility_id"], {}).get("anomaly_detected", False),
            "severity": incident["severity"],
            "reasoning": incident["description"],
            "tool_calls": [],
            "recommended_action": recommended_action.value if recommended_action else None,
            "decision_source": "RULES",
            "created_at": utc_now(),
        }
        self.decisions[decision["id"]] = decision
        return decision

    async def _analyze_incident(self, incident: dict[str, Any]) -> None:
        decision = await self.agent.analyze_incident(incident)
        self.decisions[decision["id"]] = decision
        await self.persistence.persist_critical("ai_decisions", decision)
        await self.emit("ai.decision", decision)

    async def request_safe_action(
        self, facility_id: str, command_type: CommandType, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.config.gemini_actions_enabled or self.mode != "AUTOMATIC":
            return {"approved": False, "reason": "Autonomous AI actions are disabled by operator policy"}
        if facility_id not in self.facilities:
            return {"approved": False, "reason": "Unknown facility"}
        if self._is_simulated(facility_id):
            return {"approved": False, "reason": "Simulated facilities cannot issue physical commands"}
        if command_type not in {CommandType.FAN_ON, CommandType.VENT_OPEN, CommandType.BUZZER_ON}:
            return {"approved": False, "reason": "Requested action is not in the agent allowlist"}
        controller_id = self._controller_for(facility_id)
        controller = self.devices.get(controller_id)
        if controller is None or controller["status"] != "CONNECTED":
            return {"approved": False, "reason": "Control device is disconnected"}
        reason = self.safety.validate_operator_command(
            command_type, parameters, self.latest.get(facility_id)
        )
        if reason:
            return {"approved": False, "reason": reason}
        command = self.commands.create(controller_id, command_type, parameters)
        await self.persist_command(command)
        await self.emit("command.status", command)
        return {"approved": True, "command_id": command["id"], "status": command["status"]}

    async def _refresh_facility_status(self, facility_id: str) -> None:
        old_status = self.facilities[facility_id]["status"]
        active = [
            item for item in self.incidents.values()
            if item["facility_id"] == facility_id
            and item["status"] in {IncidentStatus.OPEN.value, IncidentStatus.RESPONDING.value}
        ]
        sensor_devices = [
            item for item in self.devices.values()
            if item["facility_id"] == facility_id
            and item["device_type"] in {"ESP32_SENSOR", "SIMULATED_SENSOR"}
        ]
        if not any(item["status"] == DeviceStatus.CONNECTED.value for item in sensor_devices):
            status = "DISCONNECTED"
        elif any(item["severity"] == "CRITICAL" for item in active):
            status = "CRITICAL"
        elif active:
            status = "WARNING"
        elif not self.latest.get(facility_id):
            status = "DISCONNECTED"
        else:
            status = "HEALTHY"
        self.facilities[facility_id]["status"] = status
        if old_status != status:
            await self.emit("facility.status", {
                "facility_id": facility_id, "previous_status": old_status, "status": status
            })

    async def _verify_recovery(self, reading: dict[str, Any]) -> None:
        facility_id = reading["facility_id"]
        for incident in self.incidents.values():
            if incident["facility_id"] != facility_id or incident["status"] not in {
                IncidentStatus.OPEN.value, IncidentStatus.RESPONDING.value
            }:
                continue
            incident["verification_data"].append({
                "recorded_at": reading["recorded_at"],
                "temperature_c": reading["temperature_c"],
                "humidity_percent": reading["humidity_percent"],
                "water_detected": reading["water_detected"],
                "vibration_score": reading["vibration_score"],
            })
            incident["verification_data"] = incident["verification_data"][-1000:]
            if self.recovery.record(incident, reading):
                incident["status"] = IncidentStatus.RESOLVED.value
                incident["resolved_at"] = utc_now()
                await self.persistence.persist_critical("incidents", incident)
                await self.emit("incident.recovered", incident)

    async def check_disconnections(self) -> None:
        now = utc_now()
        for device in self.devices.values():
            last_seen = device["last_seen"]
            if last_seen and device["status"] == DeviceStatus.CONNECTED.value:
                if now - last_seen > timedelta(seconds=self.config.device_timeout_seconds):
                    device["status"] = DeviceStatus.DISCONNECTED.value
                    self._schedule(self.persistence.persist_device(device))
                    await self.emit("device.connection", {
                        "device_id": device["device_id"], "status": device["status"]
                    })
                    facility_id = device["facility_id"]
                    incident = self._active_incident(
                        facility_id, "DEVICE_DISCONNECTED", device["device_id"]
                    )
                    if incident is None:
                        incident = {
                            "id": str(uuid4()), "facility_id": facility_id,
                            "incident_type": "DEVICE_DISCONNECTED", "severity": "WARNING",
                            "status": IncidentStatus.OPEN.value,
                            "description": f"Device {device['device_id']} missed its heartbeat",
                            "detected_readings": {"device_id": device["device_id"]}, "verification_data": [],
                            "detected_at": now, "resolved_at": None,
                        }
                        self.incidents[incident["id"]] = incident
                        await self.persistence.persist_critical("incidents", incident)
                        await self.emit("incident.created", incident)
                    await self._refresh_facility_status(facility_id)

    async def close(self) -> None:
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        await self.persistence.flush_readings()
        self.persistence.close()
        await self.agent.close()


_runtime: Runtime | None = None


def get_runtime(app: FastAPI | None = None) -> Runtime:
    global _runtime
    if app is not None:
        runtime = getattr(app.state, "runtime", None)
        if runtime is not None:
            return runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime
