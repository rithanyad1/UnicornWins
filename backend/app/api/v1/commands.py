from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.security import authenticated_device_id, require_operator
from app.schemas.commands import CommandAck, CommandRequest, CommandStatus

router = APIRouter()


@router.post("/commands", status_code=status.HTTP_201_CREATED)
async def create_command(
    payload: CommandRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: None = Depends(require_operator),
) -> dict:
    runtime = request.app.state.runtime
    device = runtime.devices.get(payload.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Unknown device")
    if device["status"] != "CONNECTED":
        raise HTTPException(status_code=409, detail="Cannot command a disconnected device")
    if device["device_type"] != "PICO_CONTROLLER":
        raise HTTPException(status_code=409, detail="Commands may only be sent to a control device")
    if runtime.facilities[device["facility_id"]]["is_simulated"]:
        raise HTTPException(status_code=403, detail="Manual hardware commands are disabled for simulated facilities")
    reason = runtime.safety.validate_operator_command(
        payload.command_type, payload.parameters, runtime.latest.get(device["facility_id"])
    )
    if reason:
        raise HTTPException(status_code=409, detail={"blocked": True, "reason": reason})
    command_count = len(runtime.commands.commands)
    command = runtime.commands.create(
        payload.device_id, payload.command_type, payload.parameters, payload.incident_id,
        idempotency_key=idempotency_key,
    )
    created = len(runtime.commands.commands) != command_count
    if created:
        await runtime.persist_command(command)
        await runtime.emit("command.status", command)
    return {"command": command, "duplicate": not created}


@router.post("/commands/{command_id}/ack")
async def acknowledge_command(
    command_id: str,
    payload: CommandAck,
    request: Request,
    x_device_token: str | None = Header(default=None),
) -> dict:
    runtime = request.app.state.runtime
    device_id = authenticated_device_id(request, x_device_token)
    command = runtime.commands.commands.get(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Unknown command")
    if command["device_id"] != device_id:
        raise HTTPException(status_code=403, detail="Command belongs to another device")
    try:
        updated, changed = runtime.commands.acknowledge(
            command_id, payload.status, payload.reported_state, payload.failure_reason
        )
    except ValueError as exc:
        code = 409 if command["status"] == "EXPIRED" else 422
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Unknown command")
    if changed:
        await runtime.heartbeat(device_id, payload.reported_state)
        await runtime.persist_command(updated)
        await runtime.emit("command.status", updated)
        incident_id = updated.get("incident_id")
        incident = runtime.incidents.get(incident_id) if incident_id else None
        if incident:
            incident["verification_data"].append({
                "command_id": updated["id"],
                "command_status": updated["status"],
                "reported_state": updated["reported_state"],
                "acknowledged_at": updated["acknowledged_at"],
            })
            await runtime.persistence.persist_critical("incidents", incident)
            await runtime.emit("incident.updated", incident)
    return {"command": updated, "duplicate": not changed}