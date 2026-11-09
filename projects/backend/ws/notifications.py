"""WebSocket routing for real-time notifications."""

import json
import logging
from typing import Any
from raft.websocket.connection import RaftWebSocket
from raft.auth.jwt import decode_access_token

logger = logging.getLogger("raft.ws.notifications")


def register_websocket_routes(app: Any) -> None:
    """Attach real-time notification WebSocket endpoints to the Raft application."""

    @app.websocket("/ws/notifications")
    async def notification_ws(ws: RaftWebSocket) -> None:
        token = ws.query_params.get("token", [None])[0]
        user_id = None
        username = None

        if token:
            try:
                payload = decode_access_token(token)
                user_id = payload.get("user_id")
                username = payload.get("username")
            except Exception as exc:
                logger.warning("WebSocket token verification failed: %s", exc)

        if not user_id:
            await ws.accept()
            try:
                first_msg = await ws.receive_json()
                if isinstance(first_msg, dict) and first_msg.get("type") == "auth":
                    payload = decode_access_token(first_msg.get("token", ""))
                    user_id = payload.get("user_id")
                    username = payload.get("username")
            except Exception as exc:
                logger.warning("Failed to authenticate WebSocket via initial payload: %s", exc)

        if not user_id:
            await ws.send_json({"event": "error", "message": "Authentication required."})
            await ws.close(code=4401, reason="Unauthorized")
            return

        room = f"user_{user_id}"
        await ws.join_room(room)
        logger.info("WebSocket joined room '%s' for user @%s", room, username)

        await ws.send_json({
            "event": "connected",
            "room": room,
            "user_id": user_id,
            "username": username,
            "message": "Connected to real-time notification stream.",
        })

        try:
            while True:
                raw = await ws.receive_text()
                try:
                    parsed = json.loads(raw)
                    if parsed.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                except Exception:
                    pass
        except ConnectionError:
            logger.info("WebSocket disconnected for user @%s (room %s)", username, room)
        finally:
            await ws.leave_room(room)

