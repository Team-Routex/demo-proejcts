"""ASGI WebSocket connection wrapper used by Raft handlers."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs


class RaftWebSocket:
    """Friendly wrapper around ASGI websocket scope/receive/send."""

    def __init__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
        manager: Any | None = None,
    ) -> None:
        self._scope = scope
        self._receive = receive
        self._send = send
        self._manager = manager
        self.path_params: dict[str, str] = {}
        self.state: dict[str, Any] = {}
        self._accepted = False
        self._closed = False

    @property
    def is_accepted(self) -> bool:
        return self._accepted

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def path(self) -> str:
        return self._scope.get("path", "/")

    @property
    def query_string(self) -> str:
        return self._scope.get("query_string", b"").decode("latin-1")

    @property
    def query_params(self) -> dict[str, list[str]]:
        return parse_qs(self.query_string)

    @property
    def headers(self) -> dict[str, str]:
        return {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in self._scope.get("headers", [])
        }

    async def accept(self, subprotocol: str | None = None) -> None:
        if self._accepted:
            return
        message: dict[str, Any] = {"type": "websocket.accept"}
        if subprotocol is not None:
            message["subprotocol"] = subprotocol
        await self._send(message)
        self._accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if self._closed:
            return
        await self._send({"type": "websocket.close", "code": code, "reason": reason})
        self._closed = True

    async def receive(self) -> dict[str, Any]:
        return await self._receive()

    async def receive_text(self) -> str:
        while True:
            message = await self.receive()
            msg_type = message.get("type")
            if msg_type == "websocket.disconnect":
                raise ConnectionError("WebSocket disconnected")
            if msg_type == "websocket.connect":
                continue

            text = message.get("text")
            if text is not None:
                return text
            data = message.get("bytes")
            if data is None:
                return ""
            return data.decode("utf-8")

    async def receive_json(self) -> Any:
        return json.loads(await self.receive_text())

    async def send_text(self, data: str) -> None:
        await self.accept()
        await self._send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        await self.accept()
        await self._send({"type": "websocket.send", "bytes": data})

    async def send_json(self, data: Any) -> None:
        await self.send_text(json.dumps(data, default=str))

    async def join_room(self, room: str) -> None:
        if self._manager is not None:
            self._manager.join_room(room, self)

    async def leave_room(self, room: str) -> None:
        if self._manager is not None:
            self._manager.leave_room(room, self)

    async def send_room(self, room: str, message: str) -> None:
        if self._manager is not None:
            await self._manager.send_to_room(room, message)

    async def broadcast(self, message: str) -> None:
        if self._manager is not None:
            await self._manager.broadcast(message)
