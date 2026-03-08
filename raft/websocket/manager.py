"""Small helper for room-based websocket broadcasts."""

from __future__ import annotations

from collections import defaultdict

from raft.websocket.connection import RaftWebSocket


class WebSocketManager:
    """Track active websocket connections and room memberships."""

    def __init__(self) -> None:
        self._connections: set[RaftWebSocket] = set()
        self._rooms: dict[str, set[RaftWebSocket]] = defaultdict(set)

    def connect(self, websocket: RaftWebSocket) -> None:
        self._connections.add(websocket)

    def disconnect(self, websocket: RaftWebSocket) -> None:
        self._connections.discard(websocket)
        for room in list(self._rooms.keys()):
            members = self._rooms[room]
            members.discard(websocket)
            if not members:
                del self._rooms[room]

    def join_room(self, room: str, websocket: RaftWebSocket) -> None:
        self._rooms[room].add(websocket)

    def leave_room(self, room: str, websocket: RaftWebSocket) -> None:
        members = self._rooms.get(room)
        if not members:
            return
        members.discard(websocket)
        if not members:
            del self._rooms[room]

    async def send_to_room(self, room: str, message: str) -> None:
        members = list(self._rooms.get(room, set()))
        for websocket in members:
            await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        for websocket in list(self._connections):
            await websocket.send_text(message)
