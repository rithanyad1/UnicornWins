from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.runtime import get_runtime

router = APIRouter()


@router.websocket("/ws/live")
async def live_updates(websocket: WebSocket) -> None:
    runtime = get_runtime(websocket.app)
    await runtime.connections.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await runtime.connections.disconnect(websocket)