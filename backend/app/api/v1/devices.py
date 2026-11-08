from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.security import require_device
from app.schemas.devices import DeviceHeartbeat

router = APIRouter()


@router.post("/devices/{device_id}/heartbeat")
async def heartbeat(
    device_id: str,
    payload: DeviceHeartbeat,
    request: Request,
    _: None = Depends(require_device),
) -> dict:
    if payload.device_id != device_id:
        raise HTTPException(status_code=422, detail="Path device_id must match request device_id")
    runtime = request.app.state.runtime
    device = await runtime.heartbeat(device_id, payload.actuator_state, payload.firmware_version)
    return {"accepted": True, "device": device}


@router.get("/devices/{device_id}/commands/next")
async def next_command(
    device_id: str,
    request: Request,
    _: None = Depends(require_device),
) -> dict:
    runtime = request.app.state.runtime
    if device_id not in runtime.devices:
        raise HTTPException(status_code=404, detail="Unknown device")
    expired_count = len(runtime.commands.expired_commands)
    previous_status = {
        command_id: command["status"]
        for command_id, command in runtime.commands.commands.items()
        if command["device_id"] == device_id
    }
    command = runtime.commands.next_for_device(device_id)
    expired_commands = runtime.commands.expired_commands[expired_count:]
    for expired in expired_commands:
        await runtime.persist_command(expired)
        await runtime.emit("command.status", expired)
    if expired_count:
        del runtime.commands.expired_commands[:expired_count]
    if command is not None and previous_status.get(command["id"]) == "PENDING":
        await runtime.persist_command(command)
        await runtime.emit("command.status", command)
    return {"command": command}