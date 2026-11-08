import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            clients = tuple(self._clients)
        disconnected: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                logger.debug("Removing disconnected WebSocket client", exc_info=True)
                disconnected.append(client)
        for client in disconnected:
            await self.disconnect(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)