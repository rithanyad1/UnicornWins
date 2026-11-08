from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from typing import Any
from uuid import uuid4

from openai import AsyncOpenAI

from app.core.config import Settings
from app.schemas.commands import CommandType

if TYPE_CHECKING:
    from app.services.runtime import Runtime

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

MAX_TOOL_ROUNDS = 4
MAX_TOOL_CALLS = 8

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sensor_history",
            "description": "Retrieve the most recent environmental readings for a facility.",
            "parameters": {
                "type": "object",
                "properties": {"facility_id": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["facility_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_device_status",
            "description": "Retrieve device connectivity and actuator state for a facility.",
            "parameters": {
                "type": "object",
                "properties": {"facility_id": {"type": "string"}},
                "required": ["facility_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_incidents",
            "description": "Retrieve open incidents and severity for a facility.",
            "parameters": {
                "type": "object",
                "properties": {"facility_id": {"type": "string"}},
                "required": ["facility_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_network_status",
            "description": "Retrieve current operational status for all monitored facilities.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_safe_action",
            "description": "Request a backend-approved, non-critical actuator action. The backend may reject it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_id": {"type": "string"},
                    "command_type": {"type": "string", "enum": ["FAN_ON", "VENT_OPEN", "BUZZER_ON"]},
                    "parameters": {"type": "object"},
                },
                "required": ["facility_id", "command_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_incident_recovery",
            "description": "Review later sensor readings and device state for an incident.",
            "parameters": {
                "type": "object",
                "properties": {"incident_id": {"type": "string"}},
                "required": ["incident_id"],
                "additionalProperties": False,
            },
        },
    },
]


class GeminiAgent:
    def __init__(self, runtime: Runtime, config: Settings) -> None:
        self.runtime = runtime
        self.config = config
        self.client: AsyncOpenAI | None = None
        if config.gemini_api_key and config.gemini_base_url and config.gemini_model:
            try:
                self.client = AsyncOpenAI(
                    api_key=config.gemini_api_key,
                    base_url=config.gemini_base_url,
                    timeout=config.gemini_timeout_seconds,
                    max_retries=0,
                )
            except Exception:
                logger.exception("Could not initialize Gemini OpenAI-compatible client")

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()

    async def analyze_incident(self, incident: dict[str, Any]) -> dict[str, Any]:
        tool_calls: list[dict[str, Any]] = []
        if self.client is None:
            return self._decision(
                incident, "Gemini API is not configured; deterministic safety rules remain in control.",
                None, False, [], "RULES",
            )
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are SENTINEL Infrastructure Response Agent. Analyze the provided incident "
                    "and use backend tools for evidence. Hardware actions are optional requests and "
                    "are subject to backend policy. Never claim an action succeeded without device "
                    "acknowledgment. Give a concise final summary; do not loop."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "incident": incident,
                    "instruction": "Investigate the incident, assess risk, and recommend a safe response.",
                }, default=str),
            },
        ]
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                response = await self.client.chat.completions.create(
                    model=self.config.gemini_model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=2048,
                )
                answer = response.choices[0].message
                calls = answer.tool_calls or []
                messages.append(answer.model_dump(exclude_none=True))
                if not calls:
                    return self._decision(
                        incident, answer.content or "No analysis was returned.",
                        self._approved_action(tool_calls), False, tool_calls, "GEMINI",
                    )
                for call in calls:
                    if len(tool_calls) >= MAX_TOOL_CALLS:
                        break
                    arguments: dict[str, Any] = {}
                    try:
                        arguments = json.loads(call.function.arguments or "{}")
                        result = await self._execute_tool(call.function.name, arguments)
                        error = None
                    except (ValueError, KeyError, TypeError) as exc:
                        result, error = {"error": str(exc)}, str(exc)
                    tool_calls.append({
                        "name": call.function.name,
                        "arguments": arguments,
                        "result": result,
                        "error": error,
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    })
                if len(tool_calls) >= MAX_TOOL_CALLS:
                    return self._decision(
                        incident, "Analysis stopped after reaching the configured tool-call limit.",
                        self._approved_action(tool_calls), False, tool_calls, "GEMINI",
                    )
            return self._decision(
                incident, "Analysis stopped after reaching the configured tool-call limit.",
                None, False, tool_calls, "GEMINI",
            )
        except Exception as exc:
            logger.exception("Gemini incident analysis failed for incident %s", incident["id"])
            return self._decision(
                incident, f"Gemini analysis unavailable ({type(exc).__name__}); safety rules remain active.",
                None, False, tool_calls, "RULES_FALLBACK",
            )

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        runtime = self.runtime
        facility_id = arguments.get("facility_id")
        if name == "get_sensor_history":
            if facility_id not in runtime.facilities:
                raise ValueError("Unknown facility")
            limit = max(1, min(int(arguments.get("limit", 20)), 100))
            return list(runtime.readings.get(facility_id, []))[-limit:]
        if name == "get_device_status":
            if facility_id not in runtime.facilities:
                raise ValueError("Unknown facility")
            return [device for device in runtime.devices.values() if device["facility_id"] == facility_id]
        if name == "get_active_incidents":
            if facility_id not in runtime.facilities:
                raise ValueError("Unknown facility")
            return [
                incident for incident in runtime.incidents.values()
                if incident["facility_id"] == facility_id and incident["status"] in {"OPEN", "RESPONDING"}
            ]
        if name == "get_network_status":
            return [
                {"facility_id": item["id"], "name": item["name"], "status": item["status"]}
                for item in runtime.facilities.values()
            ]
        if name == "request_safe_action":
            try:
                command_type = CommandType(arguments["command_type"])
            except (KeyError, ValueError) as exc:
                raise ValueError("Unsupported requested action") from exc
            return await runtime.request_safe_action(
                facility_id, command_type, arguments.get("parameters", {})
            )
        if name == "verify_incident_recovery":
            incident = runtime.incidents.get(arguments.get("incident_id"))
            if incident is None:
                raise ValueError("Unknown incident")
            return {
                "status": incident["status"],
                "verification_data": incident["verification_data"][-10:],
                "device_status": [
                    device for device in runtime.devices.values()
                    if device["facility_id"] == incident["facility_id"]
                ],
            }
        raise ValueError(f"Unknown agent tool: {name}")

    @staticmethod
    def _approved_action(tool_calls: list[dict[str, Any]]) -> str | None:
        for call in tool_calls:
            if call["name"] == "request_safe_action" and call.get("result", {}).get("approved"):
                return call["arguments"].get("command_type")
        return None

    def _decision(
        self,
        incident: dict[str, Any],
        reasoning: str,
        action: str | None,
        anomaly_detected: bool,
        tool_calls: list[dict[str, Any]],
        source: str,
    ) -> dict[str, Any]:
        model = self.config.gemini_model
        return {
            "id": str(uuid4()),
            "incident_id": incident["id"],
            "model_name": f"Google Gemini ({model})" if source == "GEMINI" else "SENTINEL safety rules",
            "anomaly_score": None,
            "anomaly_detected": anomaly_detected,
            "severity": incident["severity"],
            "reasoning": reasoning,
            "tool_calls": tool_calls,
            "recommended_action": action,
            "decision_source": source,
            "created_at": _utc_now(),
        }
